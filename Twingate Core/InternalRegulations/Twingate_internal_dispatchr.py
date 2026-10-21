#InternalRegulations_Subsystem
# FILENAME: Twingate_internal_dispatchr.py
"""
Dispatch.r - The Mechanical Mailroom
================================================================================
Part of the Internal Regulations subsystem. NOT in the orchestrator - this is a
dedicated module the daemon (Buselzebub / HIGHDaemon) calls, keeping the
orchestrator lean.

No LLM calls. Pure regex + dict lookup + file I/O. It takes a gate's parsed
output, hunts for routing tags, and writes them to their destinations from the
central LOG_PATHS map.

Daemon contract (the handshake):
    start_processing(gate_name, parsed_data, raw_text) -> job_id
        Kicks off the work in a background thread, returns immediately with a job_id.
    is_task_complete(job_id) -> bool
        True once the job finished (success OR failure).
    get_job_status(job_id) -> dict
        Full status incl. error + elapsed, so the daemon's watchdog can tell the
        difference between "still working" and "died," and cancel/restart rather
        than block forever.

The work runs in a thread so a hung or slow write can be NOTICED via timeout
rather than silently stalling the WCR pulse. Steady-but-supervised, not blind-fast.
================================================================================
"""

import os
import re
import json
import time
import uuid
import threading
from typing import Dict, Any

from .Twingate_internal_config import LOG_PATHS

# Recommended watchdog timeout for the daemon to use when polling. Exposed here so
# the daemon and Dispatch.r agree on the same number.
RECOMMENDED_WATCHDOG_SECONDS = 30


class Dispatchr:
    """The mailroom. One instance, reused. Thread-safe job registry."""

    def __init__(self):
        self._jobs: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ #
    # Daemon-facing interface                                            #
    # ------------------------------------------------------------------ #
    def start_processing(self, gate_name: str, parsed_data: dict, raw_text: str) -> str:
        """
        Begin routing this gate's output. Returns a job_id immediately; the actual
        file writing runs in a background thread so the daemon can watchdog it.
        """
        job_id = uuid.uuid4().hex
        with self._lock:
            self._jobs[job_id] = {
                "status": "RUNNING",      # RUNNING | DONE | FAILED
                "gate": gate_name,
                "started_at": time.time(),
                "finished_at": None,
                "error": None,
                "routed": [],             # list of (tag_kind, destination) actually written
            }

        worker = threading.Thread(
            target=self._process_worker,
            args=(job_id, gate_name, parsed_data or {}, raw_text or ""),
            daemon=True,
        )
        worker.start()
        return job_id

    def is_task_complete(self, job_id: str) -> bool:
        """True once the job is DONE or FAILED. Unknown job_id counts as complete
        (so a lost job never hangs the daemon forever)."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return True
            return job["status"] in ("DONE", "FAILED")

    def get_job_status(self, job_id: str) -> Dict[str, Any]:
        """Full status so the daemon's watchdog can distinguish slow from dead."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                return {"status": "UNKNOWN", "error": "no such job", "elapsed": 0.0}
            elapsed = (job["finished_at"] or time.time()) - job["started_at"]
            return {
                "status": job["status"],
                "gate": job["gate"],
                "error": job["error"],
                "routed": list(job["routed"]),
                "elapsed": round(elapsed, 3),
            }

    def cancel_job(self, job_id: str) -> None:
        """Mark a job cancelled. The worker thread is a daemon thread doing only
        file writes; we can't force-kill it safely, but we flag it so the daemon
        stops waiting and the record shows it was cancelled."""
        with self._lock:
            job = self._jobs.get(job_id)
            if job and job["status"] == "RUNNING":
                job["status"] = "FAILED"
                job["error"] = "cancelled by daemon watchdog"
                job["finished_at"] = time.time()

    # ------------------------------------------------------------------ #
    # The worker (runs in a thread)                                      #
    # ------------------------------------------------------------------ #
    def _process_worker(self, job_id: str, gate_name: str, parsed_data: dict, raw_text: str):
        routed = []
        try:
            # 1. Suit-notes  [NOTE: target=SUIT | body]
            for hit in self._route_notes(gate_name, raw_text):
                routed.append(hit)

            # 2. Governance  [SUMMON_ARBIT_R] / [VOTR_OVERRIDE] -> votr log
            for hit in self._route_simple_tag(raw_text, gate_name,
                                              patterns=[r"\[SUMMON_ARBIT_R\]", r"\[VOTR_OVERRIDE\]"],
                                              dest_key="votr", label="GOVERNANCE"):
                routed.append(hit)

            # 3. +3 logic  [PLUS3_SHIFT] -> plus3 log
            for hit in self._route_simple_tag(raw_text, gate_name,
                                              patterns=[r"\[PLUS3_SHIFT\]"],
                                              dest_key="plus3", label="PLUS3"):
                routed.append(hit)

            # 4. Ephemera  [EPHEMERAL_LOG] body -> ephemeral log
            for hit in self._route_ephemeral(raw_text, gate_name):
                routed.append(hit)

            # NOTE: build-copy capture and generic write_entries (autocraft_ledger)
            # are owned by the Logger now (auto-captured via tags elsewhere in Internal
            # Regulations). Dispatch.r deliberately does NOT touch those, to avoid
            # double-writes. This module stays focused on dynamic, state-changing routing.

            with self._lock:
                self._jobs[job_id]["routed"] = routed
                self._jobs[job_id]["status"] = "DONE"
                self._jobs[job_id]["finished_at"] = time.time()

        except Exception as e:
            with self._lock:
                # Only overwrite if not already cancelled.
                if self._jobs[job_id]["status"] == "RUNNING":
                    self._jobs[job_id]["status"] = "FAILED"
                    self._jobs[job_id]["error"] = f"{type(e).__name__}: {e}"
                    self._jobs[job_id]["finished_at"] = time.time()
                    self._jobs[job_id]["routed"] = routed

    # ------------------------------------------------------------------ #
    # Routing helpers                                                    #
    # ------------------------------------------------------------------ #
    def _append(self, dest_key: str, text: str) -> str:
        """Append text to the LOG_PATHS[dest_key] file. Returns the path used."""
        path = LOG_PATHS[dest_key]  # KeyError here is intentional & loud if a key is missing
        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(text)
        return path

    def _route_notes(self, gate_name: str, raw_text: str):
        """
        Type 2 suit-notes: [NOTE: target=SUIT | body]
        Goes to the Dream.r board (2-per-suit cap, overwrite oldest) AND is logged
        to remind_r so overwritten notes are never lost.
        """
        results = []
        pattern = r"\[NOTE:\s*target\s*=\s*([A-Za-z0-9_]+)\s*\|\s*(.*?)\]"
        matches = list(re.finditer(pattern, raw_text, re.IGNORECASE | re.DOTALL))

        # Hard cap: a gate may leave at most 2 notes per run. Take first 2, log drops.
        accepted = matches[:2]
        dropped = matches[2:]

        for m in accepted:
            target_suit = m.group(1).strip().upper()
            body = m.group(2).strip()
            self._post_note_to_dreamr(gate_name, target_suit, body)
            # Always log to remind_r so the note survives even if later overwritten.
            self._log_note_to_remindr(gate_name, target_suit, body)
            results.append(("NOTE->" + target_suit, "dreamr_board+remind_r"))

        for m in dropped:
            target_suit = m.group(1).strip().upper()
            self._append_remindr_raw(
                f"[NOTE DROPPED — over 2-per-run cap] from {gate_name} -> {target_suit}: "
                f"{m.group(2).strip()[:200]}\n"
            )
            results.append(("NOTE_DROPPED->" + target_suit, "remind_r"))

        return results

    def _post_note_to_dreamr(self, author_gate: str, target_suit: str, body: str):
        """
        Append a suit-note to dreamr_board.json's 'ephemeral_notes' dict, enforcing
        the 2-note-max-per-suit rule (overwrite oldest). Defensive: works whether or
        not 'ephemeral_notes' already exists in the board file.
        """
        try:
            # DreamrBoard lives in the Vault subsystem, not InternalRegulations, so this
            # is an absolute cross-subsystem import (the project root is on sys.path via
            # the server's sys.path.insert for "Twingate Core"). NOT a relative '.' import.
            from Vault.Twingate_vault_krowniqulous import DreamrBoard
            board = DreamrBoard()

            # Ensure the ephemeral_notes dict exists on the loaded board.
            if "ephemeral_notes" not in board.goals:
                board.goals["ephemeral_notes"] = {}

            notes_for_suit = board.goals["ephemeral_notes"].get(target_suit, [])
            note_obj = {
                "author": author_gate,
                "body": body,
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
            }
            notes_for_suit.append(note_obj)
            # Enforce 2-max: keep the newest 2, overwrite (drop) the oldest.
            if len(notes_for_suit) > 2:
                notes_for_suit = notes_for_suit[-2:]
            board.goals["ephemeral_notes"][target_suit] = notes_for_suit
            board.save_board()
        except Exception as e:
            # Non-fatal: if the board write fails, the remind_r log still captures it.
            print(f"[DISPATCH.R] Dream.r note write failed ({target_suit}): {e}")

    def _log_note_to_remindr(self, author_gate: str, target_suit: str, body: str):
        self._append_remindr_raw(
            f"[NOTE POSTED] {time.strftime('%Y-%m-%d %H:%M:%S')} "
            f"from={author_gate} target={target_suit} :: {body}\n"
        )

    def _append_remindr_raw(self, text: str):
        """remind_r log is JSON-pathed in LOG_PATHS but we append as text lines for
        a human-readable trail. If you prefer strict JSON, swap this for a JSON
        read-append-write. Kept as line-append for simplicity and resilience."""
        try:
            self._append("remind_r", text)
        except KeyError:
            # If remind_r key somehow absent, don't crash the whole job.
            print(f"[DISPATCH.R] remind_r path missing; note trail line dropped: {text.strip()}")

    def _route_simple_tag(self, raw_text: str, gate_name: str, patterns, dest_key: str, label: str):
        """Generic: if any pattern matches, append a record line to dest_key's log."""
        results = []
        for pat in patterns:
            if re.search(pat, raw_text, re.IGNORECASE):
                line = (f"[{label}] {time.strftime('%Y-%m-%d %H:%M:%S')} "
                        f"from={gate_name} :: matched {pat}\n")
                try:
                    self._append(dest_key, line)
                    results.append((label, dest_key))
                except KeyError:
                    print(f"[DISPATCH.R] {dest_key} path missing; {label} record dropped.")
        return results

    def _route_ephemeral(self, raw_text: str, gate_name: str):
        """[EPHEMERAL_LOG] body -> ephemeral log. Body runs to end-of-tag or newline."""
        results = []
        for m in re.finditer(r"\[EPHEMERAL_LOG:\s*(.*?)\]", raw_text, re.IGNORECASE | re.DOTALL):
            body = m.group(1).strip()
            line = f"[EPHEMERAL] {time.strftime('%Y-%m-%d %H:%M:%S')} from={gate_name} :: {body}\n"
            try:
                self._append("ephemeral", line)
                results.append(("EPHEMERAL", "ephemeral"))
            except KeyError:
                print("[DISPATCH.R] ephemeral path missing; ephemeral record dropped.")
        return results


# ── Self-test (uses a temp LOG_PATHS-like setup; no real council needed) ──
if __name__ == "__main__":
    print("Dispatch.r self-test — interface + routing dry run\n")
    d = Dispatchr()

    sample_text = (
        "Some council output.\n"
        "[NOTE: target=PLANN_R | Remember we ruled out the recursive approach.]\n"
        "[NOTE: target=ANCH_OR | Watch the SNR threshold at 0.5%.]\n"
        "[NOTE: target=PLANN_R | A third note that should be DROPPED past the cap.]\n"
        "[EPHEMERAL_LOG: fleeting thought about membrane geometry]\n"
        "[PLUS3_SHIFT]\n"
        "[SUMMON_ARBIT_R]\n"
    )
    parsed = {"write_entries": [], "control_commands": []}

    jid = d.start_processing("gamma", parsed, sample_text)
    print(f"job_id = {jid}")

    # Simulate the daemon's watchdog poll loop.
    start = time.time()
    while not d.is_task_complete(jid):
        if time.time() - start > RECOMMENDED_WATCHDOG_SECONDS:
            print("watchdog timeout — cancelling")
            d.cancel_job(jid)
            break
        time.sleep(0.05)

    print("final status:", json.dumps(d.get_job_status(jid), indent=2))
