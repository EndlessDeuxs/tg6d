"""
Twingate Hybrid UI – FastAPI Backend
Serves the local dashboard and bridges to the Twingate core subsystems.
"""
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
import shutil
from fastapi import UploadFile, File, Form
from typing import Optional
from pydantic import BaseModel, Field

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
TWINGATE_CORE = os.path.join(BASE_DIR, "Twingate Core")

sys.path.insert(0, TWINGATE_CORE)

from Security.Twingate_security_keys import get_key_manager
from Communications.Twingate_pathways_orchestrator import Orchestrator
from InternalRegulations.Twingate_internal_config import LOG_PATHS, MASTER_LOG_BASE
from InternalRegulations.Twingate_internal_logger import AutocraftLogger
from InternalRegulations.Twingate_internal_daemon import HIGHDaemon
from Behavior.Twingate_behavior_chronos import ChronosEngine
from Behavior.Twingate_behavior_agentman import AgentManager
from Vault.Twingate_vault_kroniqulr import KroniqulrArchive
# ... alongside the other instantiations:
kroniqulr = KroniqulrArchive()

SESSION_ID = uuid.uuid4().hex[:8]

app = FastAPI(title="Twingate Local UI", version="0.2.0")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

key_manager = get_key_manager()
craft_logger = AutocraftLogger()          # move this ABOVE the orchestrator line
orchestrator = Orchestrator(key_manager, logger=craft_logger)
chronos_engine = ChronosEngine()
agent_manager = AgentManager()
high_daemon = HIGHDaemon()
# ── Import feature configuration ──
IMPORT_DIR = os.path.join(LOG_PATHS["council"], "Imports")
os.makedirs(IMPORT_DIR, exist_ok=True)

ALLOWED_IMPORT_EXTENSIONS = {".txt", ".md", ".py"}
MAX_IMPORT_BYTES = 50 * 1024 * 1024  # 50 MB per file

class ChatRequest(BaseModel):
    message: str
    wcr_depth: int = Field(default=1, ge=1, le=10)
    compress_collecticks: int = Field(default=1, ge=1, le=20)


class ChatResponse(BaseModel):
    response: str
    synthesizor: str
    timestamp: str
    session_id: str


class UpdateKeysRequest(BaseModel):
    keys: Dict[str, str]


class UpdateKeysResponse(BaseModel):
    updated: List[str]
    status: str


def _apply_key_updates(keys: Dict[str, str]) -> List[str]:
    updated = []
    for service, key in keys.items():
        if key and key.strip():
            key_manager.set_key(service, key.strip())
            updated.append(service.lower())
    return updated


def _build_transcript(full_transcript: str, relay_log: List[str]) -> str:
    """
    Accepts the unbroken WCR archive directly from the Orchestrator
    and simply appends the timing relays to the bottom.
    """
    if not full_transcript:
        # DP-09: keep the failure reason (circuit-breaker / relay lines) in the record.
        if relay_log:
            return "[NO GATE OUTPUT CAPTURED]\n\n--- RELAY LOG ---\n" + "\n".join(relay_log)
        return "[NO GATE OUTPUT CAPTURED]"
        
    relay_section = "\n".join(relay_log) if relay_log else ""
    
    if relay_section:
        return f"{full_transcript}\n\n--- RELAY LOG ---\n{relay_section}"
    
    return full_transcript


def _append_dive_failed_note(dive_stamp: str, relay_log: List[str]) -> bool:
    """
    DP-09 (ALT): append ONE line to council memory for a failed/aborted dive.
    No gate output, no fault stub, no synth text: only the stamp and a short reason
    (the circuit-breaker / abort relay line, single-lined, max 200 chars).
    Path comes from LOG_PATHS["council_memory"] only; if unmapped, nothing is written.
    """
    path = LOG_PATHS.get("council_memory")
    if not path:
        return False
    reason = "no reason captured"
    for line in reversed(relay_log or []):
        if "abort" in line.lower():
            reason = " ".join(line.split())[:200]
            break
    try:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"\n=== DIVE FAILED @ {dive_stamp} === {reason}\n")
        return True
    except Exception as e:
        print(f"⚠️ [LOGGER FAULT] Failed to write DIVE FAILED note to {path}: {e}")
        return False

def _safe_import_filename(raw_name: str) -> str:
    """Strip any path components so an upload can't escape the import folder."""
    # Take only the final path segment, drop anything that looks like traversal.
    base = os.path.basename(raw_name.replace("\\", "/"))
    # Defensive: reject empties after stripping
    return base.strip()


def _resolve_collision(target_path: str, mode: str) -> Optional[str]:
    """
    Decide the final write path when a file of the same name already exists.
    mode = "overwrite" -> return target_path (caller overwrites)
    mode = "copy"      -> return a suffixed path that doesn't exist yet
    Returns None only if mode is invalid.
    """
    if not os.path.exists(target_path):
        return target_path
    if mode == "overwrite":
        return target_path
    if mode == "copy":
        root, ext = os.path.splitext(target_path)
        n = 2
        while os.path.exists(f"{root}_{n}{ext}"):
            n += 1
        return f"{root}_{n}{ext}"
    return None


@app.post("/import_file")
async def import_file(
    file: UploadFile = File(...),
    collision_mode: str = Form("overwrite"),  # "overwrite" or "copy"
):
    """
    Receives one file, validates it, writes it to the Imports archive, and
    (Stage 3) registers it for retrieval. Each stage reports independently.
    """
    result = {
        "filename": None,
        "stage_1_validation": "pending",
        "stage_2_disk_write": "pending",
        "stage_3_ingestion": "pending",
        "final_path": None,
        "message": "",
    }

    # ───────────── STAGE 1: VALIDATION ─────────────
    filename = _safe_import_filename(file.filename or "")
    result["filename"] = filename

    if not filename:
        result["stage_1_validation"] = "FAILED: empty filename"
        result["message"] = "[ALARM 1] No valid filename received."
        return result

    ext = os.path.splitext(filename)[1].lower()
    if ext not in ALLOWED_IMPORT_EXTENSIONS:
        result["stage_1_validation"] = f"FAILED: extension '{ext}' not allowed"
        result["message"] = (
            f"[ALARM 1] '{ext}' not permitted. "
            f"Allowed: {', '.join(sorted(ALLOWED_IMPORT_EXTENSIONS))}"
        )
        return result

    # Read the file into memory once (so we can size-check before writing).
    # 50MB max keeps this safe for memory.
    contents = await file.read()
    if len(contents) > MAX_IMPORT_BYTES:
        size_mb = len(contents) / (1024 * 1024)
        result["stage_1_validation"] = f"FAILED: {size_mb:.1f}MB exceeds 50MB cap"
        result["message"] = f"[ALARM 1] File too large ({size_mb:.1f}MB). Max is 50MB."
        return result

    if collision_mode not in ("overwrite", "copy"):
        collision_mode = "overwrite"

    result["stage_1_validation"] = "OK"

    # ───────────── STAGE 2: DISK WRITE ─────────────
    target_path = os.path.join(IMPORT_DIR, filename)
    write_path = _resolve_collision(target_path, collision_mode)

    try:
        with open(write_path, "wb") as f:
            f.write(contents)
        result["stage_2_disk_write"] = "OK"
        result["final_path"] = write_path
    except OSError as e:
        result["stage_2_disk_write"] = f"FAILED: {e}"
        result["message"] = f"[ALARM 2] Disk write failed: {e}"
        return result  # Stage 1 passed; we stop here, and we know exactly why.

    # Log the successful landing to the daemon pulse so it shows in the monitor.
    try:
        high_daemon.logger.log_daemon_pulse(
            "[SEV-1: ADVISORY]",
            f"Import grounded: {os.path.basename(write_path)} ({len(contents)} bytes)",
        )
    except Exception:
        pass  # Logging the log must never break the upload.

    # ───────────── STAGE 3: INGESTION (optional, non-fatal) ─────────────
    # This is the "fancy" part. If it fails, the file is STILL safely on disk
    # from Stage 2 — we report the failure but do not treat it as fatal.
    try:
        ingest_ok = _register_import_for_retrieval(write_path)
        result["stage_3_ingestion"] = "OK" if ingest_ok else "SKIPPED: retrieval not wired yet"
    except Exception as e:
        result["stage_3_ingestion"] = f"FAILED (non-fatal): {e}"
        result["message"] = (
            f"[ALARM 3] File saved OK, but retrieval registration failed: {e}. "
            f"The file is safe on disk at {write_path}."
        )
        return result

    result["message"] = f"File imported successfully to {write_path}"
    return result


def _register_import_for_retrieval(file_path: str) -> bool:
    """
    Stage 3: record an imported file in the Kroniqul.r archive so the council
    can retrieve it by name via fetch_wcr_transcript().

    Since Kroniqul.r uses filename-addressed retrieval (not a vector index),
    "registration" means writing a shard entry that records the import event
    and the retrievable filename. The file itself is already on disk from
    Stage 2; this makes the archive aware of it.

    Returns True on successful registration, False if it could not register.
    """
    try:
        filename = os.path.basename(file_path)

        # Pull current chronos position so the shard lands in the right time-chunk.
        metrics = chronos_engine.get_chronometrics()
        mectick = metrics.get("mectick", 0)
        collectick = metrics.get("collectick", 0)

        # Record the import event as a shard entry. This is the archive's
        # bookkeeping that an import occurred and is retrievable by this name.
        registration_note = (
            f"[IMPORT REGISTERED] file='{filename}' "
            f"path='{file_path}' "
            f"retrievable_via=fetch_wcr_transcript('{filename}')"
        )
        kroniqulr.write_shard(mectick, collectick, registration_note, shard_type="imports")

        return True
    except Exception as e:
        # Non-fatal by design. Stage 2 already saved the file; this only affects
        # whether the archive knows about it. The caller logs this as a Stage 3
        # failure without losing the file.
        print(f"[STAGE 3 FAULT] Could not register import in Kroniqul.r: {e}")
        return False

@app.get("/")
async def root():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.post("/update_keys", response_model=UpdateKeysResponse)
async def update_keys(request: UpdateKeysRequest):
    if not request.keys:
        raise HTTPException(status_code=400, detail="No API keys provided.")
    updated = _apply_key_updates(request.keys)
    return UpdateKeysResponse(updated=updated, status="authorized")


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    target_depth = request.wcr_depth

    # Read the council's persistent memory so it walks into the dive knowing prior
    # conclusions. This is the one growing file; the council sees ALL of it.
    council_history = craft_logger.read_persistent()
    history_block = (
        f"=== COUNCIL PERSISTENT MEMORY (prior dives) ===\n{council_history}\n"
        f"=== END MEMORY ===\n\n"
    ) if council_history else ""

    current_prompt = (
        f"{history_block}"
        f"{request.message}\n\n"
        f"[SYSTEM DIRECTIVE]: We are initiating a continuous marathon run. "
        f"Your immediate goal is to complete the ACTIVE quests on the Dream.r Board. "
        f"Remember: INSPEC_TOR requires parseable code (Python/JSON), not narrative prose. "
        f"Take your time, work step-by-step, and draft a valid Sandbox proposal.\n\n"
        f"[UI CONFIG] WCR Depth: {target_depth} | "
        f"Compress Collecticks: {request.compress_collecticks} | "
        f"Session: {SESSION_ID}"
    )

    last_result = None
    synthesizor_output = ""

    for current_depth in range(1, target_depth + 1):
        is_last = (current_depth == target_depth)

        # Explicit WCR interval tracking (this is what the orchestrator was missing)
        current_wcr_interval = current_depth
        total_wcr_intervals = target_depth

        # Only skip preflight on continuation intervals (not the first one)
        skip_preflight = (current_depth > 1)

        result = orchestrator.process(
            user_prompt=current_prompt,
            chronos_engine=chronos_engine,
            high_daemon=high_daemon,
            agentman=agent_manager,
            recursion_depth=1,
            compress_collecticks=request.compress_collecticks,
            is_last_wcr=is_last,
            skip_preflight=skip_preflight,
            current_wcr_interval=current_wcr_interval,
            total_wcr_intervals=total_wcr_intervals,
        )

        last_result = result

        # Handle handoff vs normal output
        if result.get("handoff_mode"):
            carry_forward = result.get("content", "")
            synthesizor_output = carry_forward
        else:
            carry_forward = result.get("response", "")
            synthesizor_output = carry_forward

        # Build prompt for next interval (if any)
        if current_depth < target_depth:
            is_penultimate = (current_depth == target_depth - 1)
            warning = (
                "**WARNING:** The next set is the FINAL set of this WCR. "
                "It is your last chance to submit a build while holding decent continuity. "
                "If you want to submit a Sandbox change, make sure it is formatted as parseable code "
                "(Python/JSON) so it clears INSPEC_TOR for Architect approval."
            ) if is_penultimate else "Maintain operational continuity and work on your Dream.r Board quests."

            current_prompt = (
                f"[AUTO-CONTINUATION: WCR INTERVAL {current_depth} OF {target_depth} CONCLUDED]\n"
                f"HANDOFF FROM PREVIOUS CONDENS_OR:\n{carry_forward}\n\n"
                f"=== DIRECTIVE ===\n"
                f"Proceed to WCR Interval {current_depth + 1}. {warning}"
            )

        if not result.get("success"):
            break

    # ── One prompt = one Tick. Advance ONCE, after the full dive. ──
    dive_ok = bool(last_result and last_result.get("success"))
    if dive_ok:
        chronos_engine.register_depth_exchange_complete()

    if not synthesizor_output:
        synthesizor_output = "[SYNTHESIZ.R FAULT] WCR cascade did not produce a final output."

    dive_stamp = chronos_engine.get_stamp()

    transcript = _build_transcript(
        last_result.get("full_transcript", "") if last_result else "",
        last_result.get("log", []) if last_result else [],
    )

    # Per-tick snapshot files (council/ + synthesiz_r/), keyed on the dive's stamp.
    craft_logger.log_wcr_output(transcript, synthesizor_output, dive_stamp)

    # Persistent growing memory — one file, appended, read at the start of every dive.
    # DP-09 (ALT): only COMPLETED dives enter memory in full. A failed/aborted dive adds
    # ONE line to memory (stamp + short reason); its full record stays in the per-tick
    # snapshot + Synthesizer file (with relay reason) and is flagged in Monit.or.
    if dive_ok:
        craft_logger.log_persistent(transcript, synthesizor_output, dive_stamp)
    else:
        noted = _append_dive_failed_note(dive_stamp, last_result.get("log", []) if last_result else [])
        craft_logger.log_daemon_pulse(
            "[SEV-4: WARNING]",
            f"DIVE FAILED @ {dive_stamp}: "
            + ("one-line failure note written to council memory (DP-09 ALT). " if noted
               else "failure note NOT written to council memory (DP-09 ALT). ")
            + "See Council_Transcripts/ and Synthesizer_Outputs/ for this stamp.",
        )

    return ChatResponse(
        response=synthesizor_output,
        synthesizor="SYNTHESIZ.R",
        timestamp=timestamp,
        session_id=SESSION_ID,
    )

@app.get("/get_chat_history", response_class=PlainTextResponse)
async def get_chat_history():
    """
    Serve the persistent council memory (current_ct_council_logs.md) so the UI can
    load it as chat history on page refresh — instead of showing a blank slate.
    Reads the EXACT file the orchestrator appends to, so it always reflects what's
    actually been written.
    """
    path = os.path.join(MASTER_LOG_BASE, "current_ct_council_logs.md")
    if not os.path.exists(path):
        return "[No council history yet. Run a prompt to begin building memory.]"
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[Could not read council history: {e}]"


@app.get("/get_daemon_logs", response_class=PlainTextResponse)
async def get_daemon_logs():
    # Route the UI to read the active Autocraft Ledger
    target_log = LOG_PATHS.get("autocraft_ledger")
    
    if not target_log or not os.path.exists(target_log):
        return "Awaiting initial WCR output... The Cathedral is currently quiet."
    try:
        with open(target_log, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        return f"[SEV-4: CRITICAL] UI Integration Error: Could not read WCR logs from disk. Details: {str(e)}"


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("twingate_server:app", host="127.0.0.1", port=8000, reload=True)