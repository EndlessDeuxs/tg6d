#Communications_Pathways
# FILENAME: Twingate_pathways_orchestrator.py
import time
import re
import os
import json
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any
from .Twingate_pathways_interfaces import GateOutput, RelayContext, RouterRequest, RouterResponse
from .Twingate_pathways_router import Router, ROUND_COUNT
from .Twingate_pathways_bridge import Bridge, CIRCUIT_BREAKER_SEV_TAG, format_circuit_breaker_ui_message, get_model_display_name
from .UIT_function_translate import UITranslator
from .UIT_interfaces import IntentPacket
from InternalRegulations.Twingate_internal_config import LOG_PATHS
from InternalRegulations.Twingate_internal_config import MASTER_LOG_BASE
from Behavior.Twingate_behavior_chronos import ChronosEngine


@dataclass
class RelayContext:
    user_prompt: str
    tone: str = ""
    mood: str = ""
    recursion_depth: int = 1
    current_cycle: int = 1
    chain_context: str = ""
    previous_outputs: List = field(default_factory=list)
    chrono_tick: str = "MT00CT00T01"
    confidence: float = 1.0
    gate_flips_remaining: Dict = field(default_factory=dict)
    arbit_r_calls_remaining: int = 3

    # === WCR Interval Tracking (New & Clean) ===
    current_wcr_interval: int = 1
    total_wcr_intervals: int = 1
    is_last_wcr: bool = False          # Will be calculated below
    skip_preflight: bool = False
    last_handoff: Optional[str] = None


class _WCRCascadeAborted(Exception):
    def __init__(self, result: Dict[str, Any]):
        self.result = result
        super().__init__(result.get("response", "WCR cascade aborted"))


class Orchestrator:
    def __init__(self, key_manager, logger=None):
        self.key_manager = key_manager
        self.router = Router()
        self.bridge = Bridge(key_manager)
        self.logger = logger          # AutocraftLogger passed in from the server
        self.final_outputs: Dict[str, str] = {}
        self.relay_log: List[str] = []

    def _log(self, message: str, level: int = 2):
        """
        Appends progress and timing messages to the in-memory log list (self.relay_log)
        and, if an AutocraftLogger is available, forwards the pulse to the 
        background monitor logs with the corresponding severity tag.
        """
        # 1. Accumulate message in-memory for final build_transcript compilation
        self.relay_log.append(message)
        
        # 2. Safely route to background daemon pulse log if the logger is active
        if self.logger:
            # Dynamically map severity level using the system config rules
            from InternalRegulations.Twingate_internal_config import get_severity_tag
            sev_tag = get_severity_tag(level)
            self.logger.log_daemon_pulse(sev_tag, message)

    def _log_circuit_breaker(self, model_key: str, error: str, high_daemon=None):
        display = get_model_display_name(model_key)
        daemon_entry = (
            f"{CIRCUIT_BREAKER_SEV_TAG} WCR cascade aborted. "
            f"{display} encountered critical API failure: {error}"
        )
        self._log(daemon_entry)
        if high_daemon:
            from InternalRegulations.Twingate_internal_config import LOG_PATHS
            high_daemon.logger._write(LOG_PATHS["autocraft_emergency"], "CIRCUIT BREAKER", daemon_entry)

    def _abort_cascade(self, model_key: str, error: str, high_daemon=None) -> Dict[str, Any]:
        self._log_circuit_breaker(model_key, error, high_daemon)
        ui_message = format_circuit_breaker_ui_message(model_key)
        self.final_outputs["synthesizor"] = ui_message
        return {
            "success": False,
            "response": ui_message,
            "circuit_breaker": True,
            "final_outputs": self.final_outputs.copy(),
            "log": self.relay_log.copy(),
        }

    def _check_circuit_breaker(
        self, response: Optional[RouterResponse], model_key: str, high_daemon=None
    ) -> Optional[Dict[str, Any]]:
        if response and response.circuit_breaker:
            return self._abort_cascade(model_key, response.error or "Unknown API failure", high_daemon)
        return None

    def _append_wcr_to_archive(self, content: str, chronos_stamp: str = None):
        """
        Reliable append for every WCR interval.
        Always writes to everlog_expanse.md regardless of other logging systems.
        """
        target_path = r"C:\Users\<you>\Desktop\TG6D\Master Log File\Council_Transcripts\everlog_expanse.md"

        if not content or not content.strip():
            return

        try:
            parent = os.path.dirname(target_path)
            if parent:
                os.makedirs(parent, exist_ok=True)

            block = (
                f"\n\n{'='*70}\n"
                f"=== WCR CAPTURE @ {chronos_stamp or 'no stamp'} ===\n"
                f"{'='*70}\n\n"
                f"{content}\n"
            )

            with open(target_path, "a", encoding="utf-8") as f:
                f.write(block)

            print(f"[EVERLOG] WCR content appended to everlog_expanse.md")

        except Exception as e:
            print(f"⚠️ [EVERLOG] Failed to append to everlog_expanse.md: {e}")

    def _check_for_veto(self, text: str) -> bool:
        return "VETO DECISION: SUSTAINED" in text or "Status: QUERY REJECTED" in text

    def _call_special_role(
        self, role: str, context_str: str, global_hud: str, high_daemon=None, agentman=None
    ) -> str:
        full_context = f"{global_hud}\n\n{context_str}"
        request = RouterRequest(gate_name="placeholder", role=role, context=full_context, max_tokens=4096)
        
        # Reset new_wcr_content for this specific WCR interval
        new_wcr_content = ""

        # --- AGENTMAN REGISTRY CHECK ---
        cascade_list = []
        if agentman:
            try:
                suit = agentman.get_active_suit(role.upper())
                if suit and hasattr(suit, 'cascade'):
                    cascade_list = suit.cascade
            except KeyError:
                self._log(f"   [DEBUG] Agentman bypassed: Suit '{role.upper()}' not actively loaded in memory.")
        
        if not cascade_list:
            # Safely retrieve the suit dictionary or object if agentman loaded it
            suit_obj = None
            if agentman:
                try:
                    suit_obj = agentman.get_active_suit(role.upper())
                except KeyError:
                    pass
            cascade_list = self.router.get_cascade_for_role(role, agent_suit=suit_obj)
            
        if not cascade_list:
            cascade_list = ["deepseek"] # Absolute fallback

        for model in cascade_list:
            self._log(f"   ↳ Attempting {role.upper()} via: {model.upper()}")
            request.gate_name = model
            response = self.bridge.call(request)
            abort = self._check_circuit_breaker(response, model, high_daemon)
            if abort:
                raise _WCRCascadeAborted(abort)
            if response.success:
                return response.content
        return f"[ERR-WCR-02] / [SEV-4: WARNING]: CASCADE_EXHAUSTED - API calls failed for {role}"

    def _evaluate_build_flip(self, omega_controls: dict, veto_cleared: bool,
                             inspector_cleared: bool, build_instruction: str,
                             high_daemon) -> dict:
        """
        Decide whether to flip to CONTRAC_TOR and run a build session.
        """
        decision = {"proceed": False, "reason": "", "emergency": False}

        if not omega_controls.get("build_flip"):
            decision["reason"] = "No build approval from Omega."
            return decision

        if not veto_cleared:
            decision["reason"] = "Omega veto did not clear; build blocked."
            return decision

        emergency = omega_controls.get("build_emergency", False)

        if not inspector_cleared and not emergency:
            decision["reason"] = (
                "Build approved by Omega but Inspec.tor did not clear the connection "
                "manifest. Build held pending a clean Inspec.tor pass. "
                "(Or use [BUILD_EMERGENCY] to route straight to the Architect.)"
            )
            self._log("🛑 BUILD GATE: Inspec.tor clearance required. Build held.")
            return decision

        if emergency and not inspector_cleared:
            decision["proceed"] = True
            decision["emergency"] = True
            decision["reason"] = "Emergency bypass: routing to Architect without Inspec.tor staged check."
            try:
                from InternalRegulations.Twingate_autocraft_sandbox import log_emergency_invocation
                log_emergency_invocation("CONTRAC_TOR", build_instruction[:200])
            except Exception as e:
                self._log(f"[EMERGENCY LOG FAULT] {e}")
            self._log("⚠️ BUILD GATE: EMERGENCY BYPASS — straight to Architect, Inspec.tor skipped.")
            return decision

        decision["proceed"] = True
        decision["reason"] = "Build approved: Omega + veto clear + Inspec.tor cleared."
        self._log("✅ BUILD GATE: all clearances present. Flipping to CONTRAC_TOR.")
        return decision

    def _run_inspector(self, proposed_path: str, proposed_source: str,
                       high_daemon, agentman,
                       explicit_connected_files: dict = None) -> dict:
        """
        Run the full Inspec.tor process on a proposed change.
        """
        try:
            from Behavior.Twingate_behavior_inspector import (
                build_connection_manifest, render_manifest_for_llm,
            )
        except ImportError as e:
            self._log(f"⚠️ INSPEC_TOR modules not found ({e}). Failing closed.")
            return {"cleared": False, "manifest": {"ok": False},
                    "llm_review": "Inspec.tor mechanical module missing.",
                    "summary": "INSPEC_TOR HELD: mechanical module unavailable."}

        import os
        import glob

        # ── Connection discovery ──
        if explicit_connected_files:
            connected = explicit_connected_files
            discovery = "explicit (council-provided)"
        else:
            connected = {}
            folder = os.path.dirname(proposed_path) or "."
            try:
                for sibling in glob.glob(os.path.join(folder, "*.py")):
                    if os.path.basename(sibling) == os.path.basename(proposed_path):
                        continue
                    try:
                        with open(sibling, "r", encoding="utf-8") as f:
                            connected[sibling] = f.read()
                    except Exception:
                        pass
            except Exception:
                pass
            discovery = f"same-subsystem ({len(connected)} sibling files)"

        # ── Stage 1: mechanical manifest ──
        manifest = build_connection_manifest(proposed_path, proposed_source, connected)
        self._log(f"🔍 INSPEC_TOR mechanical [{discovery}]: {manifest.get('summary', 'scanned')}")

        # ── Stage 2: INSPEC_TOR suit, fed the manifest ──
        briefing = render_manifest_for_llm(manifest, proposed_path)
        llm_review = ""
        suit_flagged_blocker = False

        inspector_context = (
            f"{briefing}\n\n"
            f"Proposed file source under review:\n"
            f"```\n{proposed_source[:8000]}\n```\n\n"
            f"Remember: output [INSPECTOR_OK] if sound, or [INSPECTOR_BLOCK] if broken."
        )

        try:
            # Route through the suit cascade (NOT hardcoded to any one provider).
            suit_result = self._call_special_role(
                "INSPEC_TOR", inspector_context, high_daemon, agentman
            )
            llm_review = suit_result if isinstance(suit_result, str) else str(suit_result)

            # Verdict tokens. Fail-closed: a block token, OR the absence of an OK
            # token, both hold the build. Only an explicit OK with no block clears.
            has_ok = "[INSPECTOR_OK]" in llm_review
            has_block = "[INSPECTOR_BLOCK]" in llm_review
            if has_block or not has_ok:
                suit_flagged_blocker = True
        except Exception as e:
            llm_review = f"[INSPEC_TOR SUIT ERROR] {e}"
            suit_flagged_blocker = True  # fail-closed

        # Verdict: mechanical manifest is now ADVISORY (fed to the suit as a briefing
        # but no longer a hard gate). Clearance rides on the suit's verdict alone.
        # The Architect's manual review is the real build gate.
        cleared = not suit_flagged_blocker

        if cleared:
            summary = "INSPEC_TOR CLEARED: mechanical clean + suit returned [INSPECTOR_OK]."
            self._log("✅ INSPEC_TOR: cleared.")
        else:
            reasons = []
            if not manifest.get("ok"):
                n = len(manifest.get("broken_connections", []))
                reasons.append(f"{n} mechanical break(s)")
            if suit_flagged_blocker:
                reasons.append("suit flagged a blocker or gave no clean OK")
            summary = f"INSPEC_TOR HELD: {', '.join(reasons) or 'unspecified'}."
            self._log(f"🛑 INSPEC_TOR: held — {', '.join(reasons) or 'unspecified'}.")

        return {
            "cleared": cleared,
            "manifest": manifest,
            "llm_review": llm_review,
            "summary": summary,
        }

    def _run_contractor(self, execution_payload: str, high_daemon) -> dict:
        """
        File the already-compiled code as a proposal DIRECTLY. The code exists in
        execution_payload — we do not need the model to re-submit it through a tool
        loop. We file it and log it ourselves, so a proposal ALWAYS lands on disk.
        """
        from InternalRegulations.Twingate_autocraft_sandbox import propose_file_change

        # Pick a target filename. If the payload doesn't name one, use a stamped default.
        rel_path = self._extract_build_filename(execution_payload) if hasattr(self, "_extract_build_filename") else "council_build.py"

        result = propose_file_change(
            rel_path=rel_path,
            new_content=execution_payload,
            rationale="Auto-filed by CONTRAC_TOR from approved council build.",
        )

        # Durable logger copy, too — the logger owns the permanent record.
        logger = getattr(self, "logger", None)
        if logger and hasattr(logger, "log_proposed_build"):
            logger.log_proposed_build(
                gate_name="CONTRAC_TOR",
                code_content=execution_payload,
                chronos_stamp=None,
            )

        return result

    def process(
        self,
        user_prompt: str,
        chronos_engine=None,
        ek_engine=None,
        high_daemon=None,
        agentman=None,
        recursion_depth: int = 1,
        compress_collecticks: int = 5,
        preferred_synthesizor: Optional[str] = None,
        is_last_wcr: bool = False,           # ← We will calculate this inside
        skip_preflight: bool = False,
        current_wcr_interval: int = 1,
        total_wcr_intervals: int = 1,
    ) -> Dict[str, Any]:
            """
            ONE WCR (tWingate Chambered Resonances) SET (predictable 3-round structure)
            Preflight → 3× Council Line (with round-notes for CONDENS_OR) → Synthesiz.r
            """
            self.final_outputs = {}
            self.relay_log = []
            self.router.reset()
            if preferred_synthesizor:
                self.router.set_preferred_synthesizor(preferred_synthesizor)
            
            # === BUILD GUIDING CONTEXT (HUD + Mood + Chronos) ===
            # Note: One MecTick = 5 CollecTicks / 100 Ticks, 1 CollecTick = 20Ticks
            time_data = {"mectick": 0, "collectick": 0, "tick": 0}
            if chronos_engine:
                time_data = chronos_engine.get_chronometrics()

            hud_lines = ["=== TWINGATE GLOBAL HUD ==="]
            if chronos_engine:
                hud_lines.append(f"[WALL CLOCK] {chronos_engine.get_stamp()}")
            if ek_engine:
                hud_lines.append(ek_engine.get_mood_reader())

            global_hud = "\n".join(hud_lines) + "\n===========================\n"

            # ============================================================
            # WCR INTERVAL + is_last_wcr CALCULATION (This is the clean definition)
            # ============================================================
            current_wcr_interval = current_wcr_interval   # from parameter
            total_wcr_intervals  = total_wcr_intervals    # from parameter

            # Derive is_last_wcr properly
            calculated_is_last_wcr = (current_wcr_interval == total_wcr_intervals)

            # === PROPER RELAY CONTEXT INITIALIZATION ===
            context = RelayContext(
                user_prompt=user_prompt,
                tone="",
                mood="",
                recursion_depth=recursion_depth,
                current_cycle=1,
                chain_context="",
                previous_outputs=[],
                chrono_tick=chronos_engine.get_current_tick_string() if chronos_engine and hasattr(chronos_engine, "get_current_tick_string") else "MT00CT00T01",
                confidence=1.0,
                gate_flips_remaining={g["name"]: 3 for g in self.router.relay_gates},
                arbit_r_calls_remaining=3,

                # === Clean interval tracking ===
                current_wcr_interval=current_wcr_interval,
                total_wcr_intervals=total_wcr_intervals,
                is_last_wcr=calculated_is_last_wcr,     # ← Derived cleanly
                skip_preflight=skip_preflight,
                last_handoff=None,
            )

            # ============================================================
            # ARCHIVE HANDLING — Clean linear growth (one master file)
            # ============================================================
            import os
            from datetime import datetime

            archive_path = LOG_PATHS.get("current_archive_transcript")

            # Header for this specific WCR set
            chronos_stamp = (
                chronos_engine.get_stamp() 
                if chronos_engine and hasattr(chronos_engine, "get_stamp") 
                else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            archive_path = LOG_PATHS.get("current_archive_transcript")

            chronos_stamp = (
                chronos_engine.get_stamp() 
                if chronos_engine and hasattr(chronos_engine, "get_stamp") 
                else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            )

            # === Initialize the transcript accumulator (required for all later +=) ===
            new_wcr_content = ""

            new_wcr_content += (
                f"\n\n{'='*70}\n"
                f"=== WCR SET INITIATED @ {chronos_stamp} ===\n"
                f"{'='*70}\n\n"
            )

            # Only skip preflight on continuation intervals (not the first one)
            if current_wcr_interval > 1:
                self._log(f"=== WCR INTERVAL {current_wcr_interval}/{total_wcr_intervals} — Skipping Analytics + Probabilities ===")
            else:
                # ── PREFLIGHT (only on the very first WCR interval of the dive) ──
                self._log("=== WCR SET PREFLIGHT: Analytics → Probabilities ===")
                try:
                    analytics_out = self._call_special_role("ANALYTICS", user_prompt, global_hud, high_daemon, agentman)
                    self.final_outputs["analytics"] = analytics_out
                    context.chain_context += f"\n\n--- ANALYTICS ---\n{analytics_out}"
                    new_wcr_content += f"\n--- ANALYTICS ---\n{analytics_out}\n"

                    probabilities_out = self._call_special_role("PROBABILITIES", context.chain_context, global_hud, high_daemon, agentman)
                    self.final_outputs["probabilities"] = probabilities_out
                    context.chain_context += f"\n\n--- PROBABILITIES ---\n{probabilities_out}"
                    new_wcr_content += f"\n--- PROBABILITIES ---\n{probabilities_out}\n"

                except _WCRCascadeAborted as abort:
                    return abort.result

            # ============================================================
            # COUNCIL ALWAYS RUNS (This is the important part)
            # ============================================================
            ROUND_COUNT = 3
            COUNCIL_LINE = ["PLANN_R", "C_R_ITIC", "DRIFT_R", "ANCH_OR", "EXPL_OR_R", "CONDENS_OR"]

            # ── THREE COUNCIL ROUNDS ──
            for round_num in range(1, ROUND_COUNT + 1):
                is_final_round = (round_num == ROUND_COUNT)
                self._log(f"=== WCR SET — COUNCIL ROUND {round_num}/{ROUND_COUNT} ===")

                for role in COUNCIL_LINE:
                    # ... (keep your existing gate loop, core flips, and everything inside exactly as it is) ...
                    gate = self._gate_for_role(role)

                    # --- THE SUITORIAL INJECTION (STICKY NOTES) ---
                    # Local to THIS gate's input only — not glued to the shared
                    # chain_context, so a gate's nudge doesn't leak into every later gate.
                    suitorial_note = ""
                    try:
                        suitorials_path = LOG_PATHS.get("suitorials")
                        if suitorials_path and os.path.exists(suitorials_path):
                            with open(suitorials_path, "r", encoding="utf-8") as f:
                                handrails = json.load(f)

                            # Look up the nudge by Round (string key for JSON) and Role
                            round_key = str(round_num)
                            if round_key in handrails and role in handrails[round_key]:
                                sticky_note = handrails[round_key][role]
                                if sticky_note.strip():
                                    suitorial_note = f"\n\n{sticky_note}\n"
                    except Exception as e:
                        print(f"⚠️ [ORCHESTRATOR] Failed to load Suitorials for {role}: {e}")

                    # 2. Build the input and RUN THE GATE.
                    extra_note = ""
                    gate_input = context.chain_context + extra_note + suitorial_note
                    try:
                        content = self._run_single_gate(
                            gate=gate,
                            gate_input=gate_input,
                            context=context,
                            global_hud=global_hud,
                            high_daemon=high_daemon,
                            agentman=agentman,
                        )
                    except _WCRCascadeAborted as abort:
                        return abort.result

                    new_wcr_content += f"\n--- {role} (Round {round_num}) ---\n{content}\n"
                    
                    # --- FLIP DEUXL CORE FLIPS (Rounds 2 & 3) ---
                    if round_num in [2, 3]:
                        suit_flip_r = None

                        if role == "PLANN_R":
                            suit_flip_r = "P_ROT_OGRAPH_R"
                        elif role == "C_R_TIC":
                            suit_flip_r = "INSPEC_TOR"
                    #    elif role == "DRIFT_R":
                    #        suit_flip_r = "BUILD_R"
                        elif role == "ANCH_OR":
                            suit_flip_r = "REMIND_R"


                        if suit_flip_r:
                            print(f"⚙️ [DEUXL CORE] Flipping suit {suit_flip_r} flip for {role}...")

                            # Resolve the suit to a real model (bridge is keyed by model, not suit name)
                            _cascade = self.router.get_cascade_for_role(suit_flip_r)
                            _flip_model = _cascade[0] if _cascade else "deepseek"

                            flip_req = RouterRequest(
                                gate_name=_flip_model,
                                role=suit_flip_r,
                                context=context.chain_context
                                        + "\n\n[SYSTEM DIRECTIVE]: Perform your designated function based on the current context.",
                                max_tokens=4096,
                                temperature=0.7,
                            )
                            flip_resp = self.bridge.call(flip_req)

                            if flip_resp.success:
                                flip_text = f"\n\n=== [SYSTEM DEUXL CORE FLIP: {suit_flip_r}] ===\n{flip_resp.content}\n"
                                context.chain_context += flip_text
                                new_wcr_content += flip_text
                            else:
                    
                                print(f"⚠️ [DEUXL CORE] FLIP_R flip to {suit_flip_r} failed: {flip_resp.error}")

                    # --- RELIABLE PER-ROLE EVERLOG CAPTURE (keep this one) ---
                    try:
                        if content is not None:
                            safe_content = str(content) if not isinstance(content, str) else content
                            role_block = f"\n--- {role} (Round {round_num}) ---\n{safe_content}\n"
                            self._append_wcr_to_archive(role_block, chronos_stamp)
                        else:
                            pass  #Note: content was None — skipped append
                    except Exception as _per_role_err:
                        print(f"⚠️ [PER-ROLE CAPTURE] Non-fatal error for {role}: {_per_role_err}")
                        
                    # 3. CONDENS_OR post-processing: veto + build flip (final round only).
                    if role == "CONDENS_OR":
                        veto_cleared = not self._check_for_veto(content)

                        # Persist this round's consolidated output. ONE file, append-only.
                        # "a" mode cannot truncate — it only ever adds to the end.
                        chrono_tick = getattr(context, "chrono_tick", "?")
                        try:
                            _mem_path = os.path.join(MASTER_LOG_BASE, "condens_or_current_ct_logs.md")
                            with open(_mem_path, "a", encoding="utf-8") as _mf:
                                _mf.write(f"\n\n=== [{chrono_tick}] CONDENS_OR (Round {round_num}) ===\n{content}\n")
                        except Exception as _e:
                            print(f"[PERSISTENT MEMORY] append failed: {_e}")

                        if is_final_round:
                            is_condensor = (gate.get("role") == "CONDENS_OR")
                            omega_controls = high_daemon.parser.evaluate_active_controls(content) if high_daemon else {}
                            
                            if omega_controls.get("build_flip") and not is_condensor:
                                omega_controls["build_flip"] = False
                                self._log("🛑 BUILD GATE: [BUILD_APPROVED] ignored — not from CONDENS_OR.")

                            # --- THE AUTOMATED COMPILER INTERCEPT ---
                            if omega_controls.get("build_flip"):
                                print("⚙️ [ORCHESTRATOR] [BUILD_APPROVED] validated. Activating automated BUILD_R compiler...")
                                
                                compiler_prompt = (
                                    context.chain_context + 
                                    f"\n\n--- CONDENS_OR FINAL DIRECTIVE ---\n{content}" +
                                    "\n\n[SYSTEM DIRECTIVE]: The Council has approved a build. Strip away all poetry and philosophy. "
                                    "Return ONLY the raw, executable Python or JSON code required to make this real. Do not explain. Just build."
                                )
                                
                                # Resolve P_ROT_OGRAPH_R to its model (bridge keyed by model, not suit name).
                                _bcascade = self.router.get_cascade_for_role("P_ROT_OGRAPH_R")
                                _build_model = _bcascade[0] if _bcascade else "deepseek"

                                # Execute Build_r to act as the forge via the Bridge.
                                compiler_req = RouterRequest(
                                    gate_name=_build_model,
                                    role="P_ROT_OGRAPH_R",
                                    context=compiler_prompt,
                                    max_tokens=4096,
                                    temperature=0.5,
                                )
                                compiler_resp = self.bridge.call(compiler_req)

                                if compiler_resp.success:
                                    compiled_code = compiler_resp.content
                                else:
                                    compiled_code = f"# P_ROT_OGRAPH_R COMPILER ERROR: {compiler_resp.error}"
                                    print(f"⚠️ [ORCHESTRATOR] P_ROT_OGRAPH_R Compiler failed.")
                                
                                # Optional: Drop a historical copy of the draft into the Master Logs.
                                # Guarded with getattr so a missing logger never crashes the build.
                                _logger = getattr(self, "logger", None)
                                if _logger and hasattr(_logger, "log_proposed_build"):
                                    _logger.log_proposed_build(
                                        gate_name="BUILD_R_COMPILER",
                                        code_content=compiled_code,
                                        chronos_stamp=context.get_stamp() if hasattr(context, "get_stamp") else None
                                    )

                                # Update the execution payload so Inspector reads the actual code, not the essay
                                execution_payload = compiled_code
                            else:
                                execution_payload = content

                            inspector_cleared = False
                            if omega_controls.get("build_flip"):
                                insp = self._run_inspector(
                                    proposed_path=self._get_proposed_path(context) if hasattr(self, "_get_proposed_path") else "",
                                    proposed_source=execution_payload, # Inspector scans the compiled code payload!
                                    high_daemon=high_daemon,
                                    agentman=agentman,
                                    explicit_connected_files=None,
                                )
                                inspector_cleared = insp["cleared"]
                                self.final_outputs["inspector"] = insp["summary"] + "\n\n" + insp["llm_review"]

                            flip = self._evaluate_build_flip(
                                omega_controls=omega_controls,
                                veto_cleared=veto_cleared,
                                inspector_cleared=inspector_cleared,
                                build_instruction=execution_payload, # Contractor deploys the compiled payload!
                                high_daemon=high_daemon,
                                  )
                            if flip["proceed"]:
                                build_result = self._run_contractor(execution_payload, high_daemon)
                                self.final_outputs["contractor"] = (
                                    f"[CONTRAC_TOR] {flip['reason']}\n"
                                    + ("Proposals queued. Review Autocraft_Bay/Pending_Approval/."
                                       if build_result.get("ok") else f"Build failed: {build_result.get('error')}")
                                )
                            elif omega_controls.get("build_flip"):
                                self.final_outputs["contractor"] = f"[CONTRAC_TOR HELD] {flip['reason']}"
                        
            # ============================================================
            # POST-COUNCIL HANDOFF DECISION + RELIABLE LOGGING
            # ============================================================
            if not is_last_wcr:
                # === Intermediate WCR ===
                self._log("=== CONDENS_OR → PLANN_R HANDOFF (End of WCR) ===")

                handoff_prompt = (
                    f"[MANDATORY HANDOFF: CONDENS_OR → PLANN_R]\n"
                    f"This is NOT the final WCR of the dive.\n\n"
                    f"=== CONDENS_OR CONSOLIDATED OUTPUT ===\n{context.chain_context}\n\n"
                    f"Task: Create a tight summary of what was achieved this WCR.\n"
                    f"Focus on decisions, open threads, and what the next WCR should focus on.\n"
                )

                planner_handoff = self._call_special_role(
                    "PLANN_R", handoff_prompt, global_hud, high_daemon, agentman
                )

                context.skip_preflight = True
                context.last_handoff = planner_handoff

                # Return early — do not call Synthesiz.r
                return {
                    "success": True,
                    "handoff_mode": True,
                    "content": planner_handoff,
                    "full_transcript": new_wcr_content,
                }

            else:
                # === FINAL WCR of the dive ===
                self._log("=== FINAL WCR — Preparing for Synthesiz.r ===")

            # ── SYNTHESIZ.R (only reached on the final WCR) ──
            self._log("=== WCR SET COMPLETE — SYNTHESIZ.R ===")
            try:
                synth_out = self._call_special_role("SYNTHESIZ_R", context.chain_context, global_hud, high_daemon, agentman)
            except _WCRCascadeAborted as abort:
                return abort.result
            self.final_outputs["synthesizor"] = synth_out

            # Safe synth_addition — now AFTER synth_out has a value
            synth_addition = f"\n\n--- SYNTHESIZ.R ---\n{synth_out}\n"
            self._append_wcr_to_archive(new_wcr_content + synth_addition, chronos_stamp)
            
            return {
                "success": True,
                "response": synth_out,
                "final_outputs": self.final_outputs.copy(),
                "log": self.relay_log.copy(),
                "full_transcript": new_wcr_content,
            }

    def _run_single_gate(self, gate, gate_input, context, global_hud, high_daemon, agentman):
        """
        Per-gate execution. Resolves the gate's position name (alpha/beta/...) to
        its model (gemini/claude/...) via the RELAY_GATES 'model' field before
        calling the bridge, because the bridge's MODEL_REGISTRY is keyed by model,
        not by gate position name.
        """
        try:
            # The bridge looks up config by model name. RELAY_GATES carries the
            # model for each gate; use it. Fall back to name only if model absent.
            model_key = gate.get("model") or gate["name"]

            request = RouterRequest(
                gate_name=model_key,        # <-- model name, NOT gate position name
                role=gate["role"],
                context=gate_input,
                system_hud=global_hud
            )
            response = self.bridge.call(request)
            if response.success:
                return response.content
            else:
                return f"[ERR] Gate {gate['name']} ({model_key}) failed: {response.error}"
        except Exception as e:
            return f"[ERR] Gate {gate['name']} exception: {str(e)}"
            
    def _gate_for_role(self, role: str) -> dict:
        """
        Look up the gate dict ({"name","role","model"}) for a given council role.
        The council loop iterates over roles (PLANN_R, C_R_ITIC, ...); this resolves
        each role to its gate so _run_single_gate gets the model/name it needs.
        """
        for g in self.router.relay_gates:
            if g.get("role") == role:
                return g
        # Fallback: synthesize a minimal gate dict so a missing role degrades to a
        # clear error from the bridge rather than crashing the loop.
        return {"name": role.lower(), "role": role, "model": "deepseek"}