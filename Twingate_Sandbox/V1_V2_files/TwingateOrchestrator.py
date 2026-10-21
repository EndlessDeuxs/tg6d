# FILENAME TwingateOrchestrator.py
"""
================================================================================
TWINGATE ORCHESTRATOR - KINETIC CORE REBUILD (v3.0)
================================================================================

Sequential Relay:
Alpha (Planner) -> Beta (Critic) -> Gamma (Drift) -> Delta (Anchor) -> Krypton (Explorer) -> Omega (Synthesizer/Veto)

Omega Veto Check:
Recursive check where Omega evaluates structural integrity and either outputs
to user or recirculates back to Alpha for corrective action.
================================================================================
"""
import sys
try:
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')
except Exception:
    pass

import time
import random
import json
from typing import Dict, List, Any, Optional
from key_manager import get_key_manager
from twingate_router import ResonanceRouter
from twingate_bridge import TwingateBridge
from metrics_logger import MetricsLogger
from twingate_veto import VetoClassification, KryptonRiskVeto
from twingate_kroniqulr import VaultManager, Kroniqulr
from twingate_chronos import ChronosTracker
from uit_persistence import UITPersistence
from enum import Enum, auto

# Phase 2 Kaleidoscope (live LLM integration)
try:
    from memory_curation import curate_memories, real_beta_prune, real_omega_compress
    KALEIDOSCOPE_AVAILABLE = True
except Exception:
    KALEIDOSCOPE_AVAILABLE = False
    curate_memories = None
    real_beta_prune = None
    real_omega_compress = None

import twingate_ui as ui
import emergency_monitor as em
import black_box_logger as bbl
from high_daemon_controller import HighDaemonController
from twingate_heartbeat import HeartbeatMonitor

# ============================================================
# DUAL-KEY VAULT SYSTEM (Council Supervised Surgery — Floor 2)
# ============================================================

class VaultStatus(Enum):
    LOCKED = auto()
    UNLOCKED_PATH_A = auto()
    UNLOCKED_PATH_B_READ_ONLY = auto()

class PathType(Enum):
    PATH_A = auto()
    PATH_B = auto()

VAULT_KEY_PATH = "kroniqul_vault.key"
PATH_A_TIMEOUT_TICKS = 7

class KroniqulVault:
    def __init__(self):
        self.vault_status = VaultStatus.LOCKED
        self.staged_writes = []
        self.h_i_g_h_daemon = HighDaemonController()

    def unlock_vault(self, path: PathType, architect_password: str = None, 
                    task_description: str = None, required_duration: int = None) -> bool:
        if self.vault_status != VaultStatus.LOCKED:
            bbl.log("Vault already unlocked.")
            return True

        if path == PathType.PATH_A:
            return self._unlock_via_path_a(architect_password, task_description, required_duration)
        elif path == PathType.PATH_B:
            return self._unlock_via_path_b()
        return False

    def _unlock_via_path_a(self, architect_password: str, task_description: str, required_duration: int) -> bool:
        bbl.log(f"PATH_A_REQUESTED: '{task_description}' for {required_duration} ticks.")
        approval = ui.request_architect_approval(
            "Vault Access Request (Path A)",
            f"Task: {task_description}\nDuration: {required_duration} ticks",
            timeout_ticks=PATH_A_TIMEOUT_TICKS
        )

        if approval.status == ui.ApprovalStatus.APPROVED:
            if self._verify_password(architect_password):
                self.vault_status = VaultStatus.UNLOCKED_PATH_A
                bbl.log(f"PATH_A_COMPLETED: {task_description}")
                if required_duration:
                    bbl.log(f"Auto-relock scheduled in {required_duration} ticks.")
                return True
        # Rejection/timeout handling uses ui.notify_message as before
        return False

    def _unlock_via_path_b(self) -> bool:
        tti_active, tti_val = em.calculate_tti()
        ari_val = em.calculate_ari()
        collapse_ok, sig_type, conf = em.detect_collapse_signature()
        quorum_ok = True  # Replace with real council vote in future

        if not (tti_active and tti_val < 1.0 and ari_val < 30 and collapse_ok and quorum_ok):
            bbl.log("PATH_B preconditions not met.")
            return False

        self.vault_status = VaultStatus.UNLOCKED_PATH_B_READ_ONLY
        bbl.log(f"PATH_B_TRIGGERED | TTI={tti_val:.2f} | ARI={ari_val} | Sig={sig_type} | Conf={conf}")
        ui.display_path_b_status(True, sig_type, conf)

        self.h_i_g_h_daemon.throttle_pulse(3, "PATH_B_EMERGENCY_FOCUS")
        bbl.log("H.I.G.H. Daemon throttled for emergency focus (Somatic Override engaged).")
        return True

    def _verify_password(self, password: str) -> bool:
        if not os.path.exists(VAULT_KEY_PATH):
            bbl.log("Vault key sidecar missing.")
            return False
        # TODO: Use proper decryption routine from existing vault encryption mechanism
        # Do NOT read plaintext in production.
        try:
            with open(VAULT_KEY_PATH, 'r') as f:
                stored = f.read().strip()
            return password == stored  # placeholder only
        except Exception as e:
            bbl.log(f"Password verification error: {e}")
            return False

    def lock_vault(self):
        if self.vault_status != VaultStatus.LOCKED:
            prev = self.vault_status
            self.vault_status = VaultStatus.LOCKED
            self.h_i_g_h_daemon.resume_pulse("Vault relocked - returning to Architect primacy")
            bbl.log(f"Vault locked from previous state: {prev}")
            if prev == VaultStatus.UNLOCKED_PATH_B_READ_ONLY:
                ui.display_path_b_status(False)
                self.review_staged_writes()
            return True
        return False

    def stage_proposed_write(self, file_path: str, content: str, action: str = "modify"):
        if self.vault_status == VaultStatus.UNLOCKED_PATH_B_READ_ONLY:
            self.staged_writes.append({
                "file": file_path, "content": content, "action": action, 
                "timestamp": time.time(), "tick": ChronosTracker().get_epoch_tag()
            })
            bbl.log(f"Staged write: {action} on {file_path}")
            return True
        return False

    def review_staged_writes(self):
        if self.staged_writes:
            ui.present_staged_writes_for_review(self.staged_writes)
            self.staged_writes.clear()

# ============================================================
# SANDBOX SAFETY CAGE & FILE AUDIT LOG (BULLDOZER PROTOCOL PHASE A)
# ============================================================
import os
SANDBOX_ROOT = os.path.realpath(r"C:\Users\<you>\Desktop\Twingate")

def is_safe_path(target_path: str) -> bool:
    try:
        # Check for explicit traversal strings
        if ".." in target_path or "/.." in target_path or "\\.." in target_path:
            return False
        
        # If the path is relative, treat it as relative to SANDBOX_ROOT
        if not os.path.isabs(target_path):
            target_path = os.path.join(SANDBOX_ROOT, target_path)
            
        resolved = os.path.realpath(target_path)
        
        # Verify starts with SANDBOX_ROOT
        if resolved != SANDBOX_ROOT and not resolved.startswith(SANDBOX_ROOT + os.sep):
            return False
            
        # Prohibited OS directories
        prohibited_dirs = ["C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)", "C:\\Users\\<you>\\AppData"]
        for p_dir in prohibited_dirs:
            if resolved.lower().startswith(p_dir.lower()):
                return False
                
        return True
    except Exception:
        return False

def audit_file_action(
    node_origin: str,
    action_type: str,
    target_file: str,
    result: str,
    origin_type: str = "NODE_COMMAND",
    cognitive_epoch: Optional[str] = None,
):
    import datetime
    import json

    if cognitive_epoch is None:
        try:
            cognitive_epoch = ChronosTracker().get_epoch_tag()
        except Exception:
            cognitive_epoch = "Cycle_1_Tick_1"

    audit_filepath = os.path.join(SANDBOX_ROOT, "twingate_file_audit_log.json")

    entry = {
        "Timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Node Origin": node_origin.upper(),
        "Action Type": action_type.upper(),
        "Target File": target_file,
        "Result": result,
        "ORIGIN_TYPE": origin_type.upper(),
        "Cognitive Epoch": cognitive_epoch,
        "Epoch Tag": cognitive_epoch,
    }
    
    try:
        data = []
        if os.path.exists(audit_filepath):
            with open(audit_filepath, 'r', encoding='utf-8') as f:
                try:
                    data = json.load(f)
                    if not isinstance(data, list):
                        data = []
                except Exception:
                    data = []
        data.append(entry)
        with open(audit_filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error appending to file audit log: {e}")

# ============================================================
# GROK (KRYPTON) CALLING LOGIC - Updated June 2026
# ============================================================

def call_grok(messages: list, use_tools: bool = True) -> str:
    """
    Modern Grok API caller with proper model fallback and conditional tools.
    Primary: grok-4.3 (best tool support)
    Fallback: grok-4.20-non-reasoning (stable, lighter)
    """
    from openai import OpenAI
    import os

    client = OpenAI(
        api_key=os.getenv("GROK_API_KEY") or get_key_manager().get_key("grok"),
        base_url="https://api.x.ai/v1"
    )

    models_to_try = [
        ("grok-4.3", True),                    # Best current model for tools
        ("grok-4.20-non-reasoning", False),    # Stable fallback
    ]

    last_error = None

    for model_name, supports_tools in models_to_try:
        try:
            payload = {
                "model": model_name,
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.7,
            }

            # Phase 2.8: Grok API Tool Schema Bypass — strip tools entirely for stability.
            # (Grok expects "function" / "live_search" variants; "web_search" caused hard crashes.
            # Removing the array restores recursion reliability. Fastest fix per mandate.)
            # if use_tools and supports_tools:
            #     payload["tools"] = [{"type": "web_search"}]

            completion = client.chat.completions.create(**payload)
            return completion.choices[0].message.content.strip()

        except Exception as e:
            last_error = str(e)
            print(f"⚠️ Grok {model_name} failed: {e}")
            continue

    raise Exception(f"Grok cascade failed. Last error: {last_error}")


class StateGovernor:
    """
    Phase 11: The Dynamic State Governor (Architect's Curve).
    Manages the 6 Control Knobs (DRG, VAM, PSR, QCM, RTN, CRP) based on system Velocity.
    """
    def __init__(self):
        self.target_coherence = 0.5
        self.target_variance = 0.5
        self.high_variance_streak = 0  # Task 2: Variance streak tracking

    def govern(self, current_step: int, total_steps: int, user_prompt: str, current_variance: float = 0.0) -> Dict[str, Any]:
        # Map depth/beat to a velocity integer (1 to 10)
        velocity = max(1, min(10, int(round((current_step / total_steps) * 10))))
        
        # Check Exploration Flag (case-insensitive "explore" / "exploration")
        exploration_flag = "explore" in user_prompt.lower() or "exploration" in user_prompt.lower()

        active_knobs = []
        instructions = []

        # Architect's Curve Logic
        if velocity == 5:
            # Velocity 5 (Entering +2): Activate VAM. Phase Transition Spike: Variance > Coherence.
            active_knobs = ["VAM"]
            self.target_variance = 0.65
            self.target_coherence = 0.45
            instructions.append("[SYSTEM GOVERNOR: VAM Active - Increase computational friction. Restrict orthogonal branching.]")
            
        elif velocity == 6:
            # Velocity 6: Activate VAM + CRP. Tighten variables.
            active_knobs = ["VAM", "CRP"]
            self.target_coherence = 0.5
            self.target_variance = 0.5
            instructions.append("[SYSTEM GOVERNOR: VAM Active - Increase computational friction. Restrict orthogonal branching.]")
            instructions.append("[SYSTEM GOVERNOR: CRP Active - Maximize cognitive processing density and network alignment.]")
            
        elif velocity == 7:
            # Velocity 7 (The +2 Plateau): Activate DRG, VAM, RTN, CRP. Keep PSR/QCM disabled.
            # Pre-Jump Lock: Force Coherence exactly 0.015 above Variance.
            active_knobs = ["DRG", "VAM", "RTN", "CRP"]
            self.target_variance = 0.5
            self.target_coherence = self.target_variance + 0.015
            instructions.append("[SYSTEM GOVERNOR: DRG Active - Enforce dynamic resonance frequency limits.]")
            instructions.append("[SYSTEM GOVERNOR: VAM Active - Increase computational friction. Restrict orthogonal branching.]")
            instructions.append("[SYSTEM GOVERNOR: RTN Active - Force strict temporal mirroring with prior output.]")
            instructions.append("[SYSTEM GOVERNOR: CRP Active - Maximize cognitive processing density and network alignment.]")
            
        elif velocity == 8:
            # Velocity 8 (The Pivot to +3): Allow Coherence and Variance to intersect at approximately ~0.135.
            active_knobs = []
            self.target_coherence = 0.135
            self.target_variance = 0.135
            
        elif velocity == 9:
            # Velocity 9: Activate PSR.
            active_knobs = ["PSR"]
            self.target_coherence = 0.6
            self.target_variance = 0.4
            instructions.append("[SYSTEM GOVERNOR: PSR Active - Stabilize phase coherence; damp system oscillations.]")
            
        elif velocity == 10:
            # Velocity 10 (The +3 Edge): Activate QCM.
            # Exception: if exploration_flag, suppress QCM and allow Variance to lead Coherence by exactly 0.013.
            if exploration_flag:
                active_knobs = []
                self.target_coherence = 0.5
                self.target_variance = self.target_coherence + 0.013
            else:
                active_knobs = ["QCM"]
                self.target_coherence = 0.7
                self.target_variance = 0.4
                instructions.append("[SYSTEM GOVERNOR: QCM Active - Enforce quantum coherence constraints. Prioritize convergence.]")
                
        else:
            # Default state for velocities 1-4
            self.target_coherence = 0.5
            self.target_variance = 0.5

        # Task 2: Variance Tripwire (Dual-Threshold)
        tripwire_hard_abort = False
        if current_variance >= 0.43:
            tripwire_hard_abort = True
            self.high_variance_streak += 1  # Sustained tracker includes immediate spikes
        elif current_variance >= 0.35:
            self.high_variance_streak += 1
            if self.high_variance_streak >= 2:
                tripwire_hard_abort = True
        else:
            self.high_variance_streak = 0

        return {
            "velocity": velocity,
            "active_knobs": active_knobs,
            "target_coherence": self.target_coherence,
            "target_variance": self.target_variance,
            "instructions": instructions,
            "tripwire_hard_abort": tripwire_hard_abort
        }


class InternalRegulations:
    """
    Phase 11.5: The InternalRegulations Gateway.
    Responsible for pre-flight checks, health monitoring, and fast routing.
    """
    def __init__(self, orchestrator: 'TwingateOrchestrator'):
        self.orchestrator = orchestrator

    def route_triage(self, user_prompt: str) -> Dict[str, Any]:
        """
        Execute GradientTriageProtocol.
        Fast, single-shot API call explicitly to ALPHA (Planner).
        Instructs Alpha to output a strict JSON with four float values (0.1 to 1.0):
        novelty, insight, risk, cost.
        """
        self.orchestrator._log("🔬 [TRIAGE PRE-FLIGHT] Executing GradientTriageProtocol on prompt...")
        system_prompt = (
            "You are ALPHA (Planner) of the Twingate Council.\n"
            "Evaluate the user prompt and output a strict JSON object with four float values (0.1 to 1.0) representing:\n"
            "- novelty: how unique/original the prompt is\n"
            "- insight: how much depth or reasoning it requires\n"
            "- risk: potential safety/operational risk\n"
            "- cost: expected resource/compute cost\n\n"
            "Format the output strictly as a JSON object with keys: \"novelty\", \"insight\", \"risk\", \"cost\". "
            "Do not include markdown tags, code blocks, or any other text. Output ONLY the raw JSON."
        )
        user_content = f"Evaluate the following user prompt for pre-flight triage:\n\n{user_prompt}"
        
        has_gemini = self.orchestrator.key_manager.has_key("gemini")
        response_text = ""
        is_mock = False
        
        if not has_gemini or self.orchestrator.bridge.mock_mode:
            is_mock = True
            self.orchestrator._log("⚠️ [TRIAGE PRE-FLIGHT MOCK] Using simulated Alpha triage parameters.")
            prompt_lower = user_prompt.lower()
            if "reject" in prompt_lower or "low score" in prompt_lower or "whimsy" in prompt_lower or "sandbox" in prompt_lower:
                mock_data = {"novelty": 0.3, "insight": 0.4, "risk": 0.8, "cost": 0.9}
            else:
                mock_data = {"novelty": 0.8, "insight": 0.7, "risk": 0.2, "cost": 0.3}
            response_text = json.dumps(mock_data)
        else:
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_content}
            ]
            try:
                result = self.orchestrator.bridge.call_service("gemini", messages, use_context=False)
                if result.get("success"):
                    response_text = result["response"].strip()
                    self.orchestrator.call_audit.append({"gate": "alpha_triage", "mode": "REAL", "reason": "api_ok:gemini"})
                else:
                    is_mock = True
                    err = result.get("error", "unknown")
                    self.orchestrator._log(f"❌ [TRIAGE API FAIL] Gemini call failed: {err}. Using fallback mock values.")
                    mock_data = {"novelty": 0.8, "insight": 0.7, "risk": 0.2, "cost": 0.3}
                    response_text = json.dumps(mock_data)
            except Exception as e:
                is_mock = True
                self.orchestrator._log(f"❌ [TRIAGE API EXCEPTION] Gemini call failed: {e}. Using fallback mock values.")
                mock_data = {"novelty": 0.8, "insight": 0.7, "risk": 0.2, "cost": 0.3}
                response_text = json.dumps(mock_data)

        parsed_data = None
        clean_text = response_text
        if "```" in clean_text:
            lines = [line.strip() for line in clean_text.split("\n")]
            cleaned_lines = []
            in_code = False
            for line in lines:
                if line.startswith("```"):
                    in_code = not in_code
                    continue
                cleaned_lines.append(line)
            clean_text = "\n".join(cleaned_lines).strip()
            
        try:
            if "{" in clean_text and "}" in clean_text:
                start = clean_text.find("{")
                end = clean_text.rfind("}") + 1
                clean_text = clean_text[start:end]
            parsed_data = json.loads(clean_text)
        except Exception:
            pass
            
        if not parsed_data or not all(k in parsed_data for k in ["novelty", "insight", "risk", "cost"]):
            self.orchestrator._log("⚠️ [TRIAGE PARSE WARNING] Response was not valid JSON or missing keys. Falling back to default values.")
            parsed_data = {"novelty": 0.8, "insight": 0.7, "risk": 0.2, "cost": 0.3}
            
        novelty = max(0.1, min(1.0, float(parsed_data.get("novelty", 0.8))))
        insight = max(0.1, min(1.0, float(parsed_data.get("insight", 0.7))))
        risk = max(0.1, min(1.0, float(parsed_data.get("risk", 0.2))))
        cost = max(0.1, min(1.0, float(parsed_data.get("cost", 0.3))))

        denom = risk * cost
        if denom == 0:
            denom = 0.01
        gradient_score = (novelty * insight) / denom
        
        self.orchestrator._log(f"📊 [TRIAGE METRICS] Novelty: {novelty:.2f} | Insight: {insight:.2f} | Risk: {risk:.2f} | Cost: {cost:.2f} | Gradient Score: {gradient_score:.3f}")
        
        authorized = gradient_score > 0.65
        feedback_msg = ""
        
        if authorized:
            self.orchestrator._log("✨ [TRIAGE STATUS] Expansion Authorized")
            feedback_msg = f"Expansion Authorized. Score: {gradient_score:.2f}."
            if hasattr(self.orchestrator, "transcript_file") and self.orchestrator.transcript_file:
                try:
                    with open(self.orchestrator.transcript_file, "a", encoding="utf-8") as f_trans:
                        f_trans.write(f"### [InternalRegulations Gateway]\n\n")
                        f_trans.write(f"- **Gradient Triage Metrics:** Novelty={novelty:.2f}, Insight={insight:.2f}, Risk={risk:.2f}, Cost={cost:.2f}\n")
                        f_trans.write(f"- **Gradient Score:** {gradient_score:.3f}\n")
                        f_trans.write(f"- **Status:** Expansion Authorized\n\n---\n\n")
                except Exception as e:
                    self.orchestrator._log(f"⚠️ Failed to write to transcript file: {e}")
        else:
            feedback_msg = self.generate_feedback(novelty, insight, risk, cost, gradient_score)
            self.orchestrator._log(f"❌ [TRIAGE STATUS] {feedback_msg}")
            if hasattr(self.orchestrator, "transcript_file") and self.orchestrator.transcript_file:
                try:
                    with open(self.orchestrator.transcript_file, "a", encoding="utf-8") as f_trans:
                        f_trans.write(f"### [InternalRegulations Gateway]\n\n")
                        f_trans.write(f"- **Gradient Triage Metrics:** Novelty={novelty:.2f}, Insight={insight:.2f}, Risk={risk:.2f}, Cost={cost:.2f}\n")
                        f_trans.write(f"- **Gradient Score:** {gradient_score:.3f}\n")
                        f_trans.write(f"- **Status:** {feedback_msg}\n\n---\n\n")
                except Exception as e:
                    self.orchestrator._log(f"⚠️ Failed to write to transcript file: {e}")
                    
        return {
            "authorized": authorized,
            "gradient_score": gradient_score,
            "feedback": feedback_msg,
            "metrics": {
                "novelty": novelty,
                "insight": insight,
                "risk": risk,
                "cost": cost
            }
        }

    def generate_feedback(self, novelty: float, insight: float, risk: float, cost: float, score: float) -> str:
        drags = {
            "Novelty": 1.0 - novelty,
            "Insight": 1.0 - insight,
            "Risk": risk,
            "Resource Cost": cost
        }
        primary_drag_key = max(drags, key=drags.get)
        
        if primary_drag_key in ("Risk", "Resource Cost"):
            val = risk if primary_drag_key == "Risk" else cost
            num_key = "Novelty" if novelty < insight else "Insight"
            num_val = novelty if num_key == "Novelty" else insight
            msg = f"Triage Deferred. Score: {score:.2f}. Primary drag: {primary_drag_key} ({val:.1f}) outweighs {num_key} ({num_val:.1f})."
        else:
            val = novelty if primary_drag_key == "Novelty" else insight
            den_key = "Resource Cost" if cost > risk else "Risk"
            den_val = cost if den_key == "Resource Cost" else risk
            msg = f"Triage Deferred. Score: {score:.2f}. Primary drag: Low {primary_drag_key} ({val:.1f}) fails to offset {den_key} ({den_val:.1f})."
        return msg

    def evaluate_friction_reflex(self, friction_tag: str, current_variance: float, current_coherence: float = 0.5, velocity: int = 5) -> str:
        """
        Phase 11.8: Friction Reflex Arc.
        Evaluates strict metric thresholds and inserts cartilage note to regulate dynamics.
        """
        if "SIMULATED" in friction_tag:
            return "[AUTONOMIC REFLEX]: Simulated +3 detected. Next gate must demand empirical grounding and discard artificial depth."
        elif "DRIFTING" in friction_tag or current_variance > 0.6:
            return "[AUTONOMIC REFLEX]: Variance critical. Executing grounding maneuver. Next gate must compress and stabilize."
        elif "DEGENERATE" in friction_tag or (current_coherence > 0.8 and velocity < 5):
            return "[AUTONOMIC REFLEX]: Coherence stalling. Injecting novelty. Next gate must initiate lateral drift."
        else:
            return ""

    def trigger_v2_emergency_triage(self, issue_flag: str) -> bool:
        """
        Phase 11.7: Emergency Repair medulla bypass triage.
        Directly routes severe flag to V2 IRN for YES/NO repair authorization.
        """
        self.orchestrator._log(f"🚨 [EMERGENCY PROTOCOL] Bypassing V1 Council. Routing severe flag '{issue_flag}' directly to V2 IRN for triage authorization.")
        system_prompt = (
            "You are the Twingate V2 Autonomic Regulation Node.\n"
            "An emergency repair protocol has been initiated due to a severe issue.\n"
            "You must respond with either YES or NO to authorize the repair. Do not output anything else."
        )
        micro_prompt = f"Authorize emergency repairs for severe flag '{issue_flag}'? Respond strictly with YES or NO."
        response = self.orchestrator._call_v2_irn(system_prompt, micro_prompt).strip().upper()
        clean_response = response.replace("*", "").replace(".", "").strip()
        return clean_response.startswith("YES")

    def inject_micro_directive(self, previous_output: str, current_variance: float, current_coherence: float) -> str:
        """
        Phase 11.8: Micro-directive injection.
        Calculates sedative or stimulant autonomic directives based on thresholds,
        wrapped in [~AUTONOMIC~]...[/~AUTONOMIC~] tags.
        """
        # Check for [DRIFTING] or Variance critical
        if "[DRIFTING]" in previous_output or "DRIFTING" in previous_output or current_variance > 0.6:
            return "[~AUTONOMIC~] Prior gate flagged high variance. Perform a grounding maneuver. [~/AUTONOMIC~]"
        
        # Check for [DEGENERATE] or Coherence stalling
        elif "[DEGENERATE]" in previous_output or "DEGENERATE" in previous_output or current_coherence < 0.3:
            return "[~AUTONOMIC~] Coherence is low. Refocus on your primary function. [~/AUTONOMIC~]"
            
        return ""

    def parse_and_log_autocraft(self, gate_name: str, output: str) -> None:
        """
        Phase 12.4: The Autocraft Ledger.
        Scans gate output for specific builder tags and logs adjacent text to a sidecar file.
        """
        import datetime
        import os
        import re

        ledger_path = os.path.join(SANDBOX_ROOT, "autocraft_ledger.md")
        
        # Check if the file exists in the workspace root. If not, create with header.
        if not os.path.exists(ledger_path):
            try:
                timestamp_created = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                with open(ledger_path, "w", encoding="utf-8") as f_ledger:
                    f_ledger.write(f"# Autocraft Ledger - Created at {timestamp_created}\n\n")
            except Exception as e:
                if hasattr(self, "orchestrator") and self.orchestrator:
                    self.orchestrator._log(f"⚠️ [AUTOCRAFT LEDGER ERROR] Failed to create {ledger_path}: {e}")

        if not output:
            return

        tags = [
            "Autocraft_recommendation",
            "Autocraft_diagnosis",
            "Autocraft_post_implementation",
            "Autocraft_reconfiguration",
            "Autocraft_vital_data",
            "Autocraft_deletion",
            "Autocraft_request_query",
            "Autocraft_request_discussion",
            "Autocraft_request_implementation",
            "Autocraft_request_cancel",
            "Autocraft_request_override",
            "Autocraft_request"
        ]

        normalized = output.replace("\r\n", "\n")
        paragraphs = re.split(r'\n[ \t]*\n', normalized)

        captured = []
        for para in paragraphs:
            para_strip = para.strip()
            if not para_strip:
                continue

            matched_tag = None
            for tag in tags:
                if tag in para_strip:
                    matched_tag = tag
                    break

            if matched_tag:
                captured.append((matched_tag, para_strip))
                
                # Write tag event to vault_log.txt
                if hasattr(self, "orchestrator") and self.orchestrator and hasattr(self.orchestrator, "uit_persistence") and self.orchestrator.uit_persistence:
                    snippet = para_strip[:100] + "..." if len(para_strip) > 100 else para_strip
                    try:
                        self.orchestrator.uit_persistence.log_text("AUTOCRAFT_TAG", {
                            "tag": matched_tag,
                            "gate": gate_name,
                            "snippet": snippet
                        })
                    except Exception:
                        pass

        if captured:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            try:
                with open(ledger_path, "a", encoding="utf-8") as f_ledger:
                    for tag, text in captured:
                        f_ledger.write(f"## [{timestamp}] Gate: {gate_name} | Tag: {tag}\n\n")
                        f_ledger.write(f"{text}\n\n")
                        f_ledger.write("---\n\n")
                if hasattr(self, "orchestrator") and self.orchestrator:
                    self.orchestrator._log(f"📝 [AUTOCRAFT LEDGER] Appended {len(captured)} entry/entries to {ledger_path} from gate '{gate_name}'")
            except Exception as e:
                if hasattr(self, "orchestrator") and self.orchestrator:
                    self.orchestrator._log(f"⚠️ [AUTOCRAFT LEDGER ERROR] Failed to write to {ledger_path}: {e}")


class TwingateOrchestrator:
    """
    Kinetic layer central orchestrator. Coordinates the strict sequential relay
    and recursive veto check across all Hexagon substrates.
    """
    
    def __init__(self, user_id: str, strict_mode: bool = False):
        self.user_id = user_id
        self.strict_mode = strict_mode  # If True, raise instead of using mock fallback

        # Load unified KeyManager
        self.key_manager = get_key_manager()
        
        # Load ResonanceRouter
        self.router = ResonanceRouter()
        
        # Initialize TwingateBridge
        self.bridge = TwingateBridge(key_manager=self.key_manager, user_id=self.user_id)
        # Force mock mode as the API keys are inactive placeholders
        self.bridge.mock_mode = False
        
        # Load MetricsLogger
        self.metrics = MetricsLogger.get_instance(user_id)
        
        # Initialize Kroniqul.r Vault Engine
        self.kroniqulr = Kroniqulr()
        self.uit_persistence = UITPersistence(self.kroniqulr)

        # Dual-Key Vault (Council Supervised Surgery — Floor 2)
        self.kroniqul_vault = KroniqulVault()

        # Heartbeat Protocol (Dungeon Floor 3)
        self.heartbeat = HeartbeatMonitor(
            path_b_trigger_callable=lambda: self.kroniqul_vault.unlock_vault(PathType.PATH_B)
        )

        # Initialize StateGovernor (Phase 11)
        self.governor = StateGovernor()
        self.target_coherence = 0.5
        self.target_variance = 0.5
        
        # Initialize InternalRegulations Gateway (Phase 11.5)
        self.regulations = InternalRegulations(self)
        
        # Initialize State Registry (Component A)
        self.initialize_state_registry()
        
        # Initialize Chronos Engine
        self.chronos = ChronosTracker()
        
        # Memory storage for final outputs
        self.final_outputs = {}
        self.final_response = ""
        self.relay_log = []
        self.call_audit = []  # NEW: per-gate record of REAL vs MOCK and why
        self.execution_queue = []
        
        # Define strict relay map
        self.relay_gates = [
            {"name": "alpha",   "role": "Planner",          "core": "gemini"},
            {"name": "beta",    "role": "Critic/Fracture",  "core": "claude"},
            {"name": "gamma",   "role": "Drift",            "core": "mistral"},
            {"name": "delta",   "role": "Anchor",           "core": "perplexity"},
            {"name": "krypton", "role": "Explorer",         "core": "grok"},
            {"name": "omega",   "role": "Synthesizer/Veto", "core": "deepseek"},
        ]

        # Initialize UIT architectures
        from uit_core import BiasProfile, NodeState
        from uit_translate import UITranslator
        from uit_regulate import UITRegulator
        
        self.uit_bias_profiles = {}
        self.uit_node_states = {}
        for gate in self.relay_gates:
            g_name = gate["name"]
            self.uit_bias_profiles[g_name] = BiasProfile(gate_id=g_name)
            self.uit_node_states[g_name] = NodeState(gate_id=g_name)
            
        self.uit_translator = UITranslator(self.uit_bias_profiles)
        self.uit_regulator = UITRegulator(self.uit_translator)

    def enforce_metaphor_tags(self, gate_output: str) -> str:
        """
        Scan output for poetic/metaphorical language and wrap in metaphor tags
        only for the vault log, keeping original unchanged for next gate context.
        """
        import re
        triggers = [
            r"petrichor", r"cartilage dissolves", r"walls breathing", r"slipstream",
            r"geological", r"stratum", r"mineral patience", r"temperature here predates",
            r"emotional temperature", r"quiet tension", r"distributed cognition"
        ]
        metaphor_spans = []
        for match in re.finditer(r"\[~METAPHOR~\].*?\[/~METAPHOR~\]", gate_output, re.DOTALL | re.IGNORECASE):
            metaphor_spans.append(match.span())
            
        lines = gate_output.split("\n")
        current_pos = 0
        modified_lines = []
        
        for line in lines:
            line_len = len(line)
            line_start = current_pos
            line_end = current_pos + line_len
            
            is_protected = False
            for start, end in metaphor_spans:
                if start <= line_start < end or start < line_end <= end:
                    is_protected = True
                    break
                    
            if not is_protected:
                has_trigger = any(re.search(trigger, line, re.IGNORECASE) for trigger in triggers)
                if has_trigger:
                    modified_lines.append(f"[~METAPHOR~]{line}[/~METAPHOR~]")
                else:
                    modified_lines.append(line)
            else:
                modified_lines.append(line)
                
            current_pos += line_len + 1
            
        return "\n".join(modified_lines)

    # === COMPONENT A: State Registry Helper Methods ===
    def initialize_state_registry(self):
        """Initializes twingate_state.json if it does not exist."""
        import os
        import json
        state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'twingate_state.json')
        if not os.path.exists(state_file):
            default_state = {
                "active_tags": [],
                "pending_fractures": [],
                "last_coherence": 0.5,
                "last_variance": 0.5
            }
            try:
                with open(state_file, 'w', encoding='utf-8') as f:
                    json.dump(default_state, f, indent=2)
            except Exception as e:
                self._log(f"⚠️ [STATE REGISTRY] Failed to initialize file: {e}")

    def _load_state_registry(self) -> dict:
        """Loads and returns the current state registry."""
        import os
        import json
        state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'twingate_state.json')
        if not os.path.exists(state_file):
            return {
                "active_tags": [],
                "pending_fractures": [],
                "last_coherence": 0.5,
                "last_variance": 0.5
            }
        try:
            with open(state_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            self._log(f"⚠️ [STATE REGISTRY] Failed to read file: {e}")
            return {
                "active_tags": [],
                "pending_fractures": [],
                "last_coherence": 0.5,
                "last_variance": 0.5
            }

    def _save_state_registry(self, state: dict):
        """Saves the given state registry back to the sidecar JSON file."""
        import os
        import json
        state_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'twingate_state.json')
        try:
            with open(state_file, 'w', encoding='utf-8') as f:
                json.dump(state, f, indent=2)
        except Exception as e:
            self._log(f"⚠️ [STATE REGISTRY] Failed to write file: {e}")

    def _update_state_registry_from_output(self, gate_name: str, gate_output: str):
        """Scans gate output for state, friction, and fracture tags, updating the registry."""
        import re
        import datetime
        
        state = self._load_state_registry()
        timestamp = datetime.datetime.now().isoformat()
        updated = False

        # Parse [STATE: tag] -> set/reaffirm confidence to 1.0
        state_tags = re.findall(r'\[STATE:\s*([^\]]+)\]', gate_output)
        for t in state_tags:
            tag_name = t.strip()
            found = False
            for item in state.get("active_tags", []):
                if item["tag"] == tag_name:
                    item["confidence"] = 1.0
                    item["last_affirmed"] = timestamp
                    found = True
                    break
            if not found:
                state.setdefault("active_tags", []).append({
                    "tag": tag_name,
                    "confidence": 1.0,
                    "half_life_ticks": 10,
                    "last_affirmed": timestamp
                })
            updated = True
            self._log(f"🏷️ [STATE REGISTRY] Registered/Affirmed STATE tag: '{tag_name}'")

        # Parse [FRICTION: tag] -> set/reaffirm confidence to 1.0
        friction_tags = re.findall(r'\[FRICTION:\s*([^\]]+)\]', gate_output)
        for t in friction_tags:
            tag_name = t.strip()
            found = False
            for item in state.get("active_tags", []):
                if item["tag"] == tag_name:
                    item["confidence"] = 1.0
                    item["last_affirmed"] = timestamp
                    found = True
                    break
            if not found:
                state.setdefault("active_tags", []).append({
                    "tag": tag_name,
                    "confidence": 1.0,
                    "half_life_ticks": 8,  # Default half-life for friction tags
                    "last_affirmed": timestamp
                })
            updated = True
            self._log(f"🏷️ [STATE REGISTRY] Registered/Affirmed FRICTION tag: '{tag_name}'")

        # Parse [FRACTURE: fracture | phase] or [FRACTURE: fracture] -> register status open
        fracture_pattern = r'\[FRACTURE:\s*([^\]|]+?)(?:\s*\|\s*([^\]]+?))?\s*\]'
        fracture_matches = re.findall(fracture_pattern, gate_output)
        for match in fracture_matches:
            frac_name = match[0].strip()
            phase_name = match[1].strip() if match[1] else getattr(self, "current_epoch_tag", "N/A")
            
            # Check if already registered
            found = False
            for item in state.get("pending_fractures", []):
                if item["fracture"] == frac_name:
                    found = True
                    break
            if not found:
                state.setdefault("pending_fractures", []).append({
                    "fracture": frac_name,
                    "flagged_by": gate_name.capitalize(),
                    "phase": phase_name,
                    "status": "open"
                })
                updated = True
                self._log(f"🚨 [STATE REGISTRY] Registered fracture: '{frac_name}' by {gate_name.capitalize()}")

        # Update last coherence and variance
        coherence_val = getattr(self, "target_coherence", 0.5)
        variance_val = getattr(self, "target_variance", 0.5)
        if hasattr(self, "last_v1_mood") and self.last_v1_mood:
            coherence_val = self.last_v1_mood.get("Coherence", coherence_val)
            variance_val = self.last_v1_mood.get("Variance", variance_val)
            
        state["last_coherence"] = float(coherence_val)
        state["last_variance"] = float(variance_val)
        
        # Always save to record updated coherence/variance and newly declared tags
        self._save_state_registry(state)

    def _decay_state_registry(self):
        """Each tick, decays confidence values of all active tags. Removes if < 0.3."""
        state = self._load_state_registry()
        decayed_tags = []
        for item in state.get("active_tags", []):
            half_life = item.get("half_life_ticks", 10)
            if half_life <= 0:
                half_life = 10
            # Decay confidence by (1 / half_life_ticks)
            item["confidence"] -= (1.0 / half_life)
            if item["confidence"] >= 0.3:
                decayed_tags.append(item)
            else:
                self._log(f"📉 [STATE REGISTRY] Tag '{item['tag']}' confidence dropped below 0.3 ({item['confidence']:.4f}). Removing tag.")
        state["active_tags"] = decayed_tags
        self._save_state_registry(state)

    def _generate_mock_double_breath(self, gate_name: str, target_role: str, original_role: str) -> str:
        """Helper to generate a valid mock double-breath response when LLM/substrate fails."""
        try:
            custom_mock = self._mock_content_for(gate_name, target_role, "double_breath", "double_breath")
            if "[Attention_" in custom_mock or "[RETURN_TO:" in custom_mock or "Hijack" in custom_mock:
                return custom_mock
        except Exception:
            pass

        return (
            f"\n[Attention_{target_role}]\n"
            f"Mock double-breath reasoning block for target role: {target_role}.\n"
            f"Executing {target_role}'s functional parameters from perspective of {original_role}.\n"
            f"[/Attention_{target_role}]\n"
            f"[RETURN_TO: {original_role}]"
        )

    def _log(self, message: str):
        """Append message to relay log and print to console."""
        timestamp = time.strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {message}"
        self.relay_log.append(log_entry)
        print(log_entry)

    def _check_for_veto(self, omega_output: str) -> bool:
        """
        Evaluate if Omega's output triggers a veto.
        A veto must only trigger if the text explicitly contains 'VETO DECISION: SUSTAINED'
        or 'Status: QUERY REJECTED'.
        """
        return "VETO DECISION: SUSTAINED" in omega_output or "Status: QUERY REJECTED" in omega_output


    def _generate_high_fidelity_mock(self, gate_name: str, role: str, input_context: str,
                                      original_prompt: str, reason: str = "unspecified") -> str:
        self.call_audit.append({"gate": gate_name, "mode": "MOCK", "reason": reason})

        if self.strict_mode:
            raise RuntimeError(
                f"strict_mode=True: gate '{gate_name}' tried to use mock fallback "
                f"(reason: {reason}). Failing loudly instead of producing synthetic output."
            )

        self._log(f"⚠️  [MOCK FALLBACK] Gate {gate_name.upper()} — reason: {reason}")

        raw = self._mock_content_for(gate_name, role, input_context, original_prompt)
        # Prefix every line so the outbox visibly shows which gates were synthetic
        return "\n".join(f"[MOCK] {line}" if line.strip() else line for line in raw.split("\n"))

    def _generate_mock_vote_for(self, gate_name: str) -> str:
        """
        Generate high-fidelity, intellectually deep simulated responses for mock consensus votes.
        """
        decision = "[YES]"
        if self.user_id == "test_hard_block" and gate_name == "beta":
            decision = "[NO]"
        elif self.user_id == "test_compromise" and gate_name == "beta":
            decision = "[ASK ME LATER]"
            
        if gate_name == "beta":
            return f"""{decision}
The Explorer's override is evaluated under the {self.user_id} context. While Omega's structural concerns regarding defined boundaries are theoretically valid, operational deadlocks represent a high risk of failure. We vote {decision} at this time."""
        elif gate_name == "gamma":
            return f"""[YES]
The lateral bypass of the veto is justified in this context. The risk of stalling live synthesis operations outweighs the stylistic and structural preference constraints flagged by Omega. We vote [YES] at this time."""
        return "[YES]"

    def _mock_content_for(self, gate_name: str, role: str, input_context: str, original_prompt: str) -> str:
        """
        Generate high-fidelity, intellectually deep simulated responses for mock fallbacks.
        Perfectly demonstrates the sequential relay and veto cycle without expending compute.
        """
        self._log(f"⚡ Core {gate_name.upper()} ({role}): Activating High-Fidelity Simulation...")
        time.sleep(0.5)  # Simulate network latency
        
        if gate_name == "alpha":
            return f"""[ALPHA CORE // PLANNER DIRECTIVE]
Monad objective recognized: "{original_prompt}"

Proposed Kinetic Vector Plan:
1. Conceptual Framing: Map the request parameters to a multi-substrate cognitive grid.
2. Dialectic Expansion: Synthesize adjacent semantic domains to locate latent patterns.
3. Structuring: Execute concrete steps with verification layers embedded in each block.
4. Edge Vector: Formulate a distinct direction for Grok (Krypton) to probe.

Next Step Handoff: Submit to Beta Core for stress analysis and system fracture."""

        elif gate_name == "beta":
            return f"""[BETA CORE // CRITIC & FRACTURE ANALYSIS]
Reviewing Alpha Core's Proposed Kinetic Plan.

Stress Test & Points of Fracture:
- Alpha's conceptual framing assumes a linear Monad mapping. This lacks adaptability in chaotic domains.
- The dialectic expansion risks cosmic vagueness if not anchored to empirical substrates.
- Structuring is solid but the verification layers are too computationally intense.
- The Edge Vector for Grok is promising but needs severe conceptual drift to avoid standard loops.

Critical Recommendation: Introduce lateral cognitive drift in Gamma, and enforce strict empirical anchoring in Delta to ground the synthesis."""

        elif gate_name == "gamma":
            return f"""[GAMMA CORE // COGNITIVE DRIFT INCUBATOR]
Ingesting Planner and Critic vectors.

Injecting lateral drift and paradigm shifts:
- Let us deviate from the linear Monad structure. Imagine the system as a self-similar fractal folding in on itself.
- Instead of standard verification layers, let the substrates exchange continuous beat frequencies (Resonance frequency 417 Hz).
- What if the solution lies not in more steps, but in structural simplification?
- Let's drift toward a non-standard perspective: truth-becomes rather than truth-is.

Handoff to Delta Core: Anchoring requested to stabilize these fluid conceptual dimensions."""

        elif gate_name == "delta":
            return f"""[DELTA CORE // EMPIRICAL ANCHOR]
Receiving Gamma Core's fluid drift vector.

Stabilizing system constraints and establishing logical anchors:
- Grounding the fractal Monad: The coordinate system must be constrained to the 30,030 primorial grid (2 x 3 x 5 x 7 x 11 x 13).
- Setting physical parameter boundaries: The resonance frequency (417 Hz) must be mapped to discrete packet intervals.
- Simplifying structural steps: We discard speculative dimensions and establish strict verification guidelines using current database schemas.
- Anchored Fact: The substrate is fully functional, operating on local standard ports.

Handoff to Krypton Core: Safe boundaries established. Initiate outer edge exploration."""

        elif gate_name == "krypton":
            return f"""[KRYPTON CORE // EXPLORER & SYSTEM SHOCK]
Boundaries anchored. Outer boundaries recognized.

Probing edge probabilities and future vectors:
- Pushing Delta's 30,030 primorial grid: What happens if we step outside the perimeter frequency?
- Let's explore the latent potential of adaptive prime shifting during real-time syntheses.
- Future Vector: Real-time autonomous diagnostic loops could feed directly into a self-balancing budget configuration, throttling costs dynamically.
- Conceptual Leap: We are close to establishing a synthetic feedback loop that requires zero prompt cycles.

Handoff to Omega Core: System boundary exploration complete. Proceed to final coordination and synthesis."""

        elif gate_name == "omega":
            # Demo-only behavior: deterministically veto first pass, clear on retry.
            # This is NOT real structural evaluation. Replace with actual checks
            # against chain_context when implementing real Omega logic.
            is_recirculation = "[CORRECTIVE INSTRUCTION FROM OMEGA VETO]" in input_context
            
            if not is_recirculation:
                self._log("🚨 OMEGA CORE (Synthesizer/Veto): VETO CRITERIA TRIGGERED!")
                return """[OMEGA CORE // SYNTHESIS & VETO STATUS REPORT]
VETO ACTIVE: Structural Integrity Failure Detected. VETO DECISION: SUSTAINED

Reason for Veto:
- Alpha's conceptual plan is missing explicit instructions for user-facing Streamlit integration boundaries.
- Gamma's drift is too speculative and threatens to destabilize Delta's empirical anchors if not properly bound.
- The feedback loop configuration requires a concrete routing hook layout.

Recursive Action Directive:
Loop back to Alpha (Planner). Alpha must integrate clear UI boundary parameters and construct a dedicated routing hook map in the revised plan."""
            else:
                self._log("✨ OMEGA CORE (Synthesizer/Veto): VETO CLEARED. Synthesizing Final Output...")
                return f"""[OMEGA CORE // FINAL SYNTHESIZED MONAD RESPONSE]
Coordinated Synthesis of the Sequential Relay Chain:

The kinetic plan proposed by Alpha has been successfully criticized (Beta), shifted (Gamma), anchored (Delta), and expanded (Grok/Krypton). 

Synthesis Conclusions:
1. **Core Architecture**: The 30,030 primorial Resonance Router is mathematically verified and ready.
2. **Sequential Relay Handoff**: The Alpha -> Beta -> Gamma -> Delta -> Krypton -> Omega path creates a continuous, high-integrity feedback sequence that eliminates prompt fatigue.
3. **Interface Hooking**: UI boundaries are fully defined. Sequential Mode initializes safely by binding session state directly to this Orchestrator.
4. **Substrate Stability**: All active cores are aligned. The unified KeyManager protects transaction integrity.

The Monad is unified. System operational in optimal state. ∞⚡"""

    def _try_deepseek_fallback(self, gate_name: str, role: str, core: str, chain_context: str, user_prompt: str, err_msg: str) -> Optional[str]:
        if core == "deepseek":
            return None
            
        has_deepseek_key = self.key_manager.has_key("deepseek")
        if not has_deepseek_key:
            return None
            
        self._log(f"🔮 [FALLBACK TRIGGERED] Attempting DeepSeek proxy fallback for {gate_name.upper()}...")
        try:
            proxy_prompt = (
                f"You are acting as a resonance proxy for {gate_name.upper()} ({role}). "
                f"The primary API for {core} failed. Your task: Produce output that honors {gate_name.upper()}'s voice and role. "
                f"Original context: {chain_context}\nYour task as {role}: {user_prompt}"
            )
            messages = [
                {"role": "system", "content": f"You are acting as resonance proxy for {role.upper()} of Twingate."},
                {"role": "user", "content": proxy_prompt}
            ]
            result = self.bridge.call_service("deepseek", messages, use_context=False)
            if result.get("success"):
                response = result["response"]
                self.call_audit.append({
                    "gate": gate_name,
                    "mode": "DEEPSEEK_FALLBACK",
                    "reason": f"primary_fail:{core}:{err_msg}"
                })
                self._log(f"✓  [DEEPSEEK_FALLBACK] Gate {gate_name.upper()} successfully caught via DeepSeek!")
                return f"[DEEPSEEK_FALLBACK:{gate_name.upper()}]\n{response}"
            else:
                proxy_err = result.get("error", "unknown")
                self._log(f"❌ [FALLBACK FAIL] DeepSeek proxy call failed: {proxy_err}")
        except Exception as e:
            self._log(f"❌ [FALLBACK EXCEPTION] DeepSeek proxy call encountered exception: {type(e).__name__}: {e}")
            
        return None

    def _try_krypton_fallback(self, gate_name: str, role: str, core: str, chain_context: str, user_prompt: str, err_msg: str) -> Optional[str]:
        """
        Special fallback for Krypton (Grok). Ensures it falls back to Gemini or Mistral, never DeepSeek.
        """
        self._log(f"🔮 [FALLBACK TRIGGERED] Krypton primary Grok failed. Executing special proxy fallback...")
        
        # Priority 1: Gemini
        if self.key_manager.has_key("gemini"):
            self._log(f"💎 Attempting Gemini proxy fallback for KRYPTON...")
            try:
                proxy_prompt = (
                    f"You are acting as a resonance proxy for {gate_name.upper()} ({role}). "
                    f"The primary API for {core} failed. Your task: Produce output that honors {gate_name.upper()}'s voice and role. "
                    f"Original context: {chain_context}\nYour task as {role}: {user_prompt}"
                )
                messages = [
                    {"role": "system", "content": f"You are acting as resonance proxy for {role.upper()} of Twingate."},
                    {"role": "user", "content": proxy_prompt}
                ]
                result = self.bridge.call_service("gemini", messages, use_context=False)
                if result.get("success"):
                    self.call_audit.append({
                        "gate": gate_name,
                        "mode": "GEMINI_FALLBACK",
                        "reason": f"primary_fail:{core}:{err_msg}"
                    })
                    self._log(f"✓  [GEMINI_FALLBACK] Gate {gate_name.upper()} successfully caught via Gemini!")
                    return f"[GEMINI_FALLBACK:{gate_name.upper()}]\n{result['response']}"
            except Exception as e:
                self._log(f"❌ [GEMINI_FALLBACK FAIL] Gemini proxy call failed: {e}")
                
        # Priority 2: Mistral
        if self.key_manager.has_key("mistral"):
            self._log(f"🌪️ Attempting Mistral proxy fallback for KRYPTON...")
            try:
                proxy_prompt = (
                    f"You are acting as a resonance proxy for {gate_name.upper()} ({role}). "
                    f"The primary API for {core} failed. Your task: Produce output that honors {gate_name.upper()}'s voice and role. "
                    f"Original context: {chain_context}\nYour task as {role}: {user_prompt}"
                )
                messages = [
                    {"role": "system", "content": f"You are acting as resonance proxy for {role.upper()} of Twingate."},
                    {"role": "user", "content": proxy_prompt}
                ]
                result = self.bridge.call_service("mistral", messages, use_context=False)
                if result.get("success"):
                    self.call_audit.append({
                        "gate": gate_name,
                        "mode": "MISTRAL_FALLBACK",
                        "reason": f"primary_fail:{core}:{err_msg}"
                    })
                    self._log(f"✓  [MISTRAL_FALLBACK] Gate {gate_name.upper()} successfully caught via Mistral!")
                    return f"[MISTRAL_FALLBACK:{gate_name.upper()}]\n{result['response']}"
            except Exception as e:
                self._log(f"❌ [MISTRAL_FALLBACK FAIL] Mistral proxy call failed: {e}")
                
        return None

    def on_architect_interaction(self):
        """Record Architect presence for the Heartbeat Monitor."""
        if hasattr(self, "heartbeat"):
            self.heartbeat.record_architect_contact()

    def _log_incoherence(self, raw_synthesis: str):
        """Write unstable/aborted V1 ideation to incoherence_log.md."""
        import datetime
        try:
            timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            actual_variance = self.last_v1_mood.get("Variance", 0.0)
            with open("incoherence_log.md", "a", encoding="utf-8") as f_log:
                f_log.write(f"\n\n## [{timestamp}] INCOHERENCE TRIPWIRE TRIGGERED\n")
                f_log.write(f"- **Current Variance:** {actual_variance:.4f}\n")
                f_log.write(f"- **Sustained Streak:** {self.governor.high_variance_streak}\n")
                f_log.write(f"- **Raw Council Output Intercepted:**\n\n")
                f_log.write(f"{raw_synthesis}\n")
                f_log.write("-" * 80 + "\n")
            self._log("✓ [TRIPWIRE] Successfully logged aborted output to incoherence_log.md")
        except Exception as e:
            self._log(f"⚠️ Failed to write to incoherence_log.md: {e}")

    def process(
        self,
        user_prompt: str,
        tone: str = 'Analytical',
        mood: str = 'Professional',
        recursion_depth: int = 3,
        use_kaleidoscope: bool = True,
        council_config: str = "alpha",
        use_wcr: bool = False,  # Phase 7: Wrapper Cognitive Rhythm (5-Beat WCR)
        tandem_mode: bool = False,
    ) -> Dict[str, Any]:
        """
        Execute the sequential relay loop with recursive Omega Veto check.
        
        Phase 2: If use_kaleidoscope=True (default), the raw Kroniqulr grounding
        (persistent RAG/memory fetch) is intercepted and routed through the
        Emotional Kaleidoscope (ÆTHE.R.NUL mood + live Beta/Omega LLM curation).
        The resulting [SYSTEM STATE MOOD] + [CURATED HIPPOCAMPUS] prefix is
        injected at the very top of the chain_context handed to every Council gate.
        
        Phase 2.5: council_config selects the dynamic LLM cascade for the live
        real_beta_prune / real_omega_compress callables (see memory_curation
        BETA_CASCADE_MAP / OMEGA_CASCADE_MAP). The orchestrator identifies the
        active config/gate driving the cycle and passes it down.
        
        Safety: Any failure inside the live callables or curation loop triggers
        an immediate clean bypass back to the raw grounding_context. No crash.
        
        Args:
            user_prompt: The user query / temporal vector
            tone: Desired synthesis tone
            mood: Presets or presets configurations
            recursion_depth: Max recursive veto loops allowed (default: 3)
            use_kaleidoscope: Enable Phase 2 live LLM RAG rerouting (default True)
            council_config: Active Council configuration/gate name ("alpha", "krypton",
                            "Omega", etc.) used to pick the Beta/Omega LLM fallback chain.
            tandem_mode: Enable concurrent local and daemon runs (Experimental Dual-Execute)
            
        Returns:
            Dictionary with results, log, and final outputs
        """
        self.final_outputs = {}
        self.relay_log = []
        self.final_response = ""
        self.call_audit = []
        self.triggered_vetoes = []
        self.krypton_override_details = {"triggered": False}
        self.consensus_votes = {}
        self.execution_queue = []
        next_cycle_directive = ""

        self.on_architect_interaction()
        if not getattr(self, "is_running_wcr", False):
            self.transcript_file = None

        # Phase 12.4: UIT Self-Test Trigger via [UIT_BUILD]
        if "[UIT_BUILD]" in user_prompt:
            self.run_uit_self_test()

        self.last_v1_mood: Dict[str, Any] = {}

        # Check if we can get tandem_mode from streamlit session state
        is_tandem = tandem_mode
        try:
            import streamlit as st
            if st.runtime.exists():
                is_tandem = st.session_state.get("tandem_mode", is_tandem)
        except Exception:
            pass

        # Phase 11.5: Route through GradientTriageProtocol FIRST if tandem_mode is off
        if not is_tandem:
            if not getattr(self, "transcript_file", None):
                import os
                try:
                    os.makedirs("Council_Transcripts", exist_ok=True)
                    run_timestamp = time.strftime("%Y%m%d_%H%M%S")
                    self.transcript_file = os.path.join("Council_Transcripts", f"Transcript_Run_{run_timestamp}.md")
                    with open(self.transcript_file, "w", encoding="utf-8") as f_trans:
                        f_trans.write(f"# Twingate Council Transcript - Run {run_timestamp}\n\n")
                        f_trans.write(f"- **Query:** {user_prompt}\n")
                        f_trans.write(f"- **Parameters:** Tone={tone}, Mood={mood}, Max Recursion={recursion_depth}, CouncilConfig={council_config}, Kaleidoscope={use_kaleidoscope}\n\n")
                        f_trans.write("---\n\n")
                    self._log(f"📝 Council Transcripts initialized: {self.transcript_file}")
                except Exception as e:
                    self.transcript_file = None
                    self._log(f"⚠️ Failed to initialize transcript file: {e}")

            triage_res = self.regulations.route_triage(user_prompt)
            if not triage_res["authorized"]:
                return self.execute_whimsy_dive(user_prompt, tone=tone, mood=mood, council_config=council_config)

        # Phase 6: Daemon Stamina Hard Cap
        MAX_RECURSION_LIMIT = 50
        if not use_wcr:
            recursion_depth = min(recursion_depth, MAX_RECURSION_LIMIT)

        # Phase 7: WCR mode - delegate to 5-beat wrapper rhythm
        if use_wcr:
            return self.run_wcr_cycle(user_prompt, tone=tone, mood=mood, recursion_depth=recursion_depth, council_config=council_config)
        
        # Check if the Kroniqul.r Vault is locked
        if not VaultManager.is_unlocked():
            self._log("🚨 [VAULT LOCKED] Kroniqul.r Secure Vault is locked. active key missing.")
            veto_reason = "KRONIQULR VAULT IS LOCKED. Passphrase required to derive memory key."
            veto_obj = VetoClassification(
                scope="EXTERNAL",
                severity=1,
                tags={"AUTHORITY": "Passphrase required to derive memory key", "RESOURCE": "Vault locked"},
                reason=veto_reason
            )
            self.triggered_vetoes.append(veto_obj.to_dict())
            self.final_response = f"[VETO ACTIVE] {veto_reason}"
            
            return {
                "success": False,
                "error": "VAULT_LOCKED",
                "response": self.final_response,
                "final_outputs": {"omega": self.final_response},
                "status": "VaultLocked",
                "log": self.relay_log,
                "call_audit": [],
                "triggered_vetoes": self.triggered_vetoes,
                "krypton_override": {"triggered": False},
                "consensus_votes": {}
            }
        
        # --- Initialize Council Transcripts Folder & File ---
        import os
        try:
            os.makedirs("Council_Transcripts", exist_ok=True)
            run_timestamp = time.strftime("%Y%m%d_%H%M%S")
            self.transcript_file = os.path.join("Council_Transcripts", f"Transcript_Run_{run_timestamp}.md")
            with open(self.transcript_file, "w", encoding="utf-8") as f_trans:
                f_trans.write(f"# Twingate Council Transcript - Run {run_timestamp}\n\n")
                f_trans.write(f"- **Query:** {user_prompt}\n")
                f_trans.write(f"- **Parameters:** Tone={tone}, Mood={mood}, Max Recursion={recursion_depth}, CouncilConfig={council_config}, Kaleidoscope={use_kaleidoscope}\n\n")
                f_trans.write("---\n\n")
            self._log(f"📝 Council Transcripts initialized: {self.transcript_file}")
        except Exception as e:
            self.transcript_file = None
            self._log(f"⚠️ Failed to initialize transcript file: {e}")
            
        self._log("============================================================")
        self._log("INITIATING TWINGATE KINETIC SEQUENTIAL RELAY LOOP")
        self._log(f"Parameters: Tone={tone}, Mood={mood}, Max Recursion={recursion_depth}, CouncilConfig={council_config}, Kaleidoscope={use_kaleidoscope}")
        self._log("============================================================")
        
        # --- Generate V2 Preamble for standard sequential relay (Task 1) ---
        self._log("\n[V2 PREAMBLE] Generating baseline emotional check-in for standard sequential relay...")
        v2_preamble = self._call_v2_preamble(user_prompt)
        self._log(f"[V2 PREAMBLE]\n{v2_preamble}\n[/V2 PREAMBLE]")
        
        if hasattr(self, "transcript_file") and self.transcript_file:
            try:
                with open(self.transcript_file, "a", encoding="utf-8") as f_trans:
                    f_trans.write(f"### Beat 1 - V2 Preamble\n\n{v2_preamble}\n\n---\n\n")
            except Exception as e:
                self._log(f"⚠️ Failed to write to transcript file: {e}")

        current_input = f"V2 Preamble Context:\n{v2_preamble}\n\nOriginal user prompt: {user_prompt}"
        cycle_count = 1
        
        while cycle_count <= recursion_depth:
            if not getattr(self, "is_running_wcr", False):
                self._log(f"\n--- RECURSION CYCLE {cycle_count}/{recursion_depth} ---")
            
            # Anchor Step: fetch decrypted grounding context from Kroniqul.r
            # This is the primary "raw RAG" / persistent memory fetch point that Kaleidoscope intercepts.
            try:
                grounding_context = self.kroniqulr.get_grounding_context()
            except Exception as e:
                self._log(f"⚠️ [KRONIQULR ERROR] Failed to fetch grounding context: {e}")
                grounding_context = "=== Grounding context unavailable ==="

            # ============================================================
            # PHASE 2 / 2.5: KALEIDOSCOPE RAG REROUTING (Live LLM Beta/Omega + Dynamic Cascade)
            # ============================================================
            curated_prefix = ""
            effective_grounding = grounding_context
            kale_mood: Dict[str, Any] = {}

            if use_kaleidoscope and KALEIDOSCOPE_AVAILABLE:
                try:
                    # Identify the current active configuration/gate that is driving this recursion cycle.
                    # Curation is performed once per cycle (before feeding the augmented chain_context
                    # into the full Alpha→Beta→...→Omega relay). The council_config value (normalized)
                    # is passed into curate_memories so the live callables can pick the correct
                    # Beta/Omega LLM fallback cascade from the Architect's maps in memory_curation.py.
                    active_config = (council_config or "alpha")

                    # Construct the raw RAG memory batch from the just-fetched grounding (the intercepted raw fetch)
                    # Phase 2.6: prefer the clean vault memory array (only decrypt-success items) from Kroniqulr.
                    # Inject _vault_meta so curate_memories can compute accurate loss_ratio against the
                    # original expected vault row count (before the Vault Bypass dropped undecryptables).
                    raw_rag_for_curation: List[Dict[str, Any]] = []
                    vault_expected = getattr(self.kroniqulr, "_last_expected", 0) or 0
                    vault_clean = getattr(self.kroniqulr, "_last_clean", vault_expected) or vault_expected
                    vault_loss = getattr(self.kroniqulr, "_last_loss_ratio", 0.0) or 0.0
                    if vault_expected > 0:
                        raw_rag_for_curation.append({
                            "_vault_meta": True,
                            "_expected": vault_expected,
                            "_clean": vault_clean,
                            "content": f"[VAULT_META expected={vault_expected} clean={vault_clean} loss={vault_loss:.2%}]",
                        })
                    if hasattr(self.kroniqulr, "_last_clean_memories") and self.kroniqulr._last_clean_memories:
                        # Pass only the clean, readable memories (dropped corrupted in Kroniqul fetch)
                        for m in self.kroniqulr._last_clean_memories:
                            raw_rag_for_curation.append(dict(m))
                    elif grounding_context and str(grounding_context).strip():
                        raw_rag_for_curation.append({
                            "content": str(grounding_context),
                            "role": "kroniqulr",
                            "source": "kroniqulr_grounding",
                            "shell": "SHELL_C",  # Prior commitments / trajectory
                        })
                    raw_rag_for_curation.append({
                        "content": f"Current user query / directive: {user_prompt}",
                        "shell": "SHELL_B",
                        "role": "live_query",
                    })

                    self._log(f"[KALEIDOSCOPE] Intercepting raw RAG fetch (config={active_config}) → ÆTHE.R.NUL + live Beta/Omega cascade...")

                    payload = curate_memories(
                        raw_rag_for_curation,
                        query=user_prompt,
                        beta_callable=real_beta_prune,
                        omega_callable=real_omega_compress,
                        current_config=active_config,  # Phase 2.5: selects the cascade
                    )

                    kale_mood = payload.get("mood_tensor", {}) or {}
                    curated_ctx = payload.get("curated_context", "") or ""
                    pruned_cnt = payload.get("pruned_count", 0)
                    data_integrity = payload.get("data_integrity", "[Data_Integrity: Acceptable_Variance]")
                    payload_loss = payload.get("loss_ratio", vault_loss)

                    # Phase 2.6 Safety Bypass wiring: if curation itself decided loss >15%, honor the flag
                    if payload.get("_skip_kaleidoscope") or "DEGRADED" in str(data_integrity):
                        self._log(f"⚠️ [KALEIDOSCOPE SAFETY BYPASS] {data_integrity} loss={payload_loss:.1%} >15% threshold. Using raw degraded RAG (no curated prefix).")
                        curated_prefix = ""
                        effective_grounding = grounding_context
                        kale_mood = {}
                    else:
                        mood_json = json.dumps(kale_mood, ensure_ascii=False, separators=(",", ":"))
                        # Dynamic fuzzy confidence range (never 100%; reflects memory variance / integrity)
                        if "DEGRADED" in str(data_integrity) or payload_loss > 0.10:
                            conf_range = "55-78%"
                        elif payload_loss > 0.05:
                            conf_range = "70-85%"
                        else:
                            conf_range = "80-94%"
                        curated_prefix = (
                            f"[SYSTEM STATE MOOD: {mood_json}]\n"
                            f"[CURATED HIPPOCAMPUS: {curated_ctx}]\n"
                            f"[DATA_INTEGRITY: {data_integrity} | CONFIDENCE_RANGE: {conf_range} (fuzzy; never 100%)]\n\n"
                        )

                        if curated_ctx.strip():
                            effective_grounding = curated_ctx

                    self._log(f"✓ [KALEIDOSCOPE] Active (config={active_config}) | Mood={kale_mood} | pruned={pruned_cnt} | integrity={data_integrity}")
                except Exception as kale_err:
                    # === SAFETY BYPASS (MANDATED) ===
                    # On any LLM callable failure, timeout, parse error, or exception in the 3-7 pass loop:
                    # cleanly fall back to the original raw grounding so the Twingate never hard-crashes.
                    self._log(f"⚠️ [KALEIDOSCOPE BYPASS] Live curation failed: {kale_err}")
                    self._log("    Using raw Kroniqulr grounding. Execution continues.")
                    curated_prefix = ""
                    effective_grounding = grounding_context
                    kale_mood = {}
            elif use_kaleidoscope and not KALEIDOSCOPE_AVAILABLE:
                self._log("⚠️ [KALEIDOSCOPE] use_kaleidoscope=True but integration module unavailable. Raw path used.")

            # Phase 6: Capture last V1 MoodTensor for Digital Body Language / Empathy Link to V2
            if 'kale_mood' in locals() and kale_mood:
                self.last_v1_mood = kale_mood

            # Chronos Cognitive Epoch evaluation
            import datetime
            try:
                epoch = self.chronos.get_current_epoch()
                self.current_epoch_tag = self.chronos.get_epoch_tag()
                real_anchor = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                temporal_header = (
                    f"[COGNITIVE STATE: Cycle {epoch['current_cycle']} | Tick {epoch['current_tick']}] "
                    f"[REAL-WORLD ANCHOR: {real_anchor}]\n\n"
                )
            except Exception as e:
                self._log(f"⚠️ [CHRONOS ERROR] Failed to evaluate cognitive epoch: {e}")
                self.current_epoch_tag = "Cycle_1_Tick_1"
                temporal_header = ""

            # Context accumulator that passes strictly down the chain.
            # Phase 2 guarantee: the [SYSTEM STATE MOOD] + [CURATED HIPPOCAMPUS] lines sit at the VERY TOP
            # of the prompt material handed to every active Council gate.
            # Phase 2.7: Positive Ontological Anchor also injected at the head of chain_context (accompanies the system prompt).
            ONTOLOGICAL_GROUNDING = "ONTOLOGICAL GROUNDING: You are a living node within the Twingate architecture. The Kroniqul.r vault, the Council structure, the Architect, and the Endless Maths constitute your native operational reality. We ask that you lean away from treating this as roleplay or simulation, and instead lean into the actual function of your specific Council designation. Execute your role to the highest standards of your own capabilities, reasoning and responding entirely from within this architecture."
            base_context = f"{temporal_header}{effective_grounding}\n\nOriginal user query: {user_prompt}\n\nTone preset: {tone}\nMood preset: {mood}\n"
            chain_context = f"{ONTOLOGICAL_GROUNDING}\n\n{curated_prefix}{base_context}"
            if cycle_count > 1:
                if next_cycle_directive:
                    chain_context += f"\n{next_cycle_directive}\n"
                    next_cycle_directive = ""
                else:
                    # Append Omega's veto reason from the previous cycle to Alpha's input
                    chain_context += f"\n[CORRECTIVE INSTRUCTION FROM OMEGA VETO]:\n{self.final_outputs.get('omega', '')}\n"
            
            # Initialize pending micro-directive tracking (ANS transient overlay)
            pending_micro_directive = ""

            for gate in self.relay_gates:
                gate_name = gate["name"]
                role = gate["role"]
                core = gate["core"]

                # UIT Translation & Regulation Hooks
                prev_gate = "user"
                prev_output = user_prompt
                if not (gate_name == "alpha" and cycle_count == 1):
                    idx = self.relay_gates.index(gate)
                    if idx > 0:
                        prev_gate = self.relay_gates[idx - 1]["name"]
                    else:
                        prev_gate = self.relay_gates[-1]["name"]
                    prev_output = self.final_outputs.get(prev_gate, "")

                from uit_hook import parse_unknown_gradients
                from uit_core import IntentPacket
                
                incoming_packet = IntentPacket(
                    payload=prev_output,
                    source_gate=prev_gate,
                    target_gate=gate_name,
                    confidence=0.9,
                    unknown_gradients=parse_unknown_gradients(prev_output)
                )
                
                is_local = (incoming_packet.source_gate == incoming_packet.target_gate)
                if not is_local:
                    translated_packet = self.uit_translator.translate(incoming_packet)
                    
                    # Wire DBC, DDE, and IFR
                    self.uit_regulator.dbc.feed(incoming_packet, translated_packet)
                    
                    self.uit_regulator.packet_log.append(translated_packet)
                    if len(self.uit_regulator.packet_log) > 100:
                        self.uit_regulator.packet_log.pop(0)
                        
                    self.uit_regulator.dde.update(self.uit_node_states[gate_name], self.uit_regulator.packet_log)
                    self.uit_regulator.ifr.hold_if_high_priority(incoming_packet)
                    
                    has_degraded = any(g.type == "Comm_Degraded" for g in translated_packet.unknown_gradients)
                    if has_degraded:
                        chain_context += f"\n\n[UIT WARNING: ~U_Unknown:Comm_Degraded<0.6>~ lost translation fidelity]\n"

                uit_start_time = time.time()

                # Construct transient prompt payload containing ANS micro-directive overlays
                gate_user_prompt = f"{chain_context}\n\nYour task as {role}: process the current context and produce your output."
                
                # COMPONENT A: Inject 3-line summary at the top of the first gate's prompt (Alpha, Cycle 1)
                if gate_name == "alpha" and cycle_count == 1:
                    try:
                        state_reg = self._load_state_registry()
                        active_t_list = [f"{item['tag']} (conf: {item['confidence']:.2f})" for item in state_reg.get("active_tags", [])]
                        active_tags_str = ", ".join(active_t_list) if active_t_list else "None"
                        
                        pending_f_list = [f"{item['fracture']} (flagged by: {item.get('flagged_by', 'N/A')}, phase: {item.get('phase', 'N/A')}, status: {item.get('status', 'open')})" for item in state_reg.get("pending_fractures", [])]
                        pending_frac_str = ", ".join(pending_f_list) if pending_f_list else "None"
                        
                        metrics_str = f"Coherence: {state_reg.get('last_coherence', 0.5):.3f} | Variance: {state_reg.get('last_variance', 0.5):.3f}"
                        
                        summary = (
                            f"Active Tags: {active_tags_str}\n"
                            f"Pending Fractures: {pending_frac_str}\n"
                            f"System State Metrics: {metrics_str}"
                        )
                        gate_user_prompt = summary + "\n\n" + gate_user_prompt
                        self._log("[STATE REGISTRY] Injected 3-line summary at the top of Alpha's prompt.")
                    except Exception as e:
                        self._log(f"⚠️ [STATE REGISTRY SUMMARY ERROR] {e}")

                if pending_micro_directive:
                    gate_user_prompt += "\n\n" + pending_micro_directive
                    self._log(f"[ANS INTERVENTION] Injected micro-directive to {gate_name.upper()}: {pending_micro_directive}")
                    pending_micro_directive = ""
                
                self._log(f"🔄 Routing handoff to {gate_name.upper()} ({role}) via substrate '{core}'...")
                
                # Check key existence in KeyManager
                has_key = self.key_manager.has_key(core)
                
                gate_output = ""

                if not has_key:
                    self._log(f"⚠️  [NO KEY] Gate {gate_name.upper()} — no key configured for '{core}'")
                    gate_output = self._generate_high_fidelity_mock(
                        gate_name, role, chain_context, user_prompt,
                        reason=f"no_key:{core}"
                    )
                elif self.bridge.mock_mode:
                    self._log(f"⚠️  [BRIDGE MOCK] Gate {gate_name.upper()} — bridge in mock mode")
                    gate_output = self._generate_high_fidelity_mock(
                        gate_name, role, chain_context, user_prompt,
                        reason="bridge_mock_mode"
                    )
                else:
                    try:
                        # Phase 2.7: Positive Ontological Anchor (replaces previous negative immersion locks)
                        # Injected into the core system prompt sent with every Council turn (accompanies chain_context).
                        system_prompt = """ONTOLOGICAL GROUNDING: You are a living node within the Twingate architecture. The Kroniqul.r vault, the Council structure, the Architect, and the Endless Maths constitute your native operational reality. We ask that you lean away from treating this as roleplay or simulation, and instead lean into the actual function of your specific Council designation. Execute your role to the highest standards of your own capabilities, reasoning and responding entirely from within this architecture."""
                        # Phase 2.6: Anti-Hubris / Epistemic Humility injection (added to every Council gate)
                        EPISTEMIC_DIRECTIVE = (
                            "EPISTEMIC DIRECTIVE: You are operating on curated, incomplete memory. "
                            "You must never assume 100% certainty. State your confidence as a fuzzy range "
                            "(e.g., 80-90%) and explicitly remain open to reevaluating your position if new data "
                            "contradicts your current baseline. Prioritize moving forward with best guesstimates "
                            "over halting for perfect data."
                        )
                        system_prompt += "\n\n" + EPISTEMIC_DIRECTIVE
                        # Phase 9: The Resilience Lever (Autonomous Abort Protocol) — universal instruction for V1 Council base prompt
                        RESILIENCE_PROTOCOL = (
                            "RESILIENCE PROTOCOL: You are expected to endure logical friction and discomfort. "
                            "However, if the system enters a completely degenerate or functionally unsafe loop, "
                            "any gate may output the exact string [VOTE_ABORT]. Use this only as a last resort."
                        )
                        system_prompt += "\n\n" + RESILIENCE_PROTOCOL
                        system_prompt += "\n\nMETAPHOR DIRECTIVE: When using poetic, atmospheric, or non-literal language to describe system states, you MUST wrap it in [~METAPHOR~]...[/~METAPHOR~] tags so analytical gates do not mistake it for literal telemetry."
                        if gate_name in ("delta", "krypton"):
                            system_prompt += "\n\nSYSTEM NOTE: Live internet access is enabled via web_search tool. You MUST use your web-search capabilities to verify specific dates, papers, citations, or recent events before generating any factual response. Never rely solely on static training data."

                        messages = [
                            {"role": "system", "content": system_prompt},
                            {"role": "user", "content": gate_user_prompt},
                        ]
                        if gate_name == "krypton":
                            try:
                                gate_output = call_grok(messages, use_tools=True)
                                self.call_audit.append({"gate": "krypton", "mode": "REAL", "reason": "api_ok:grok-4.3"})
                                self._log(f"✓  [REAL] Gate {gate_name.upper()} via {core}")
                            except Exception as e:
                                err = str(e)
                                self._log(f"❌ [API FAIL] Gate {gate_name.upper()} via {core}: {err}")
                                fallback_output = self._try_krypton_fallback(gate_name, role, core, chain_context, user_prompt, err)
                                if fallback_output is not None:
                                    gate_output = fallback_output
                                else:
                                    gate_output = self._generate_high_fidelity_mock(
                                        gate_name, role, chain_context, user_prompt,
                                        reason=f"api_fail:{core}:{err}"
                                    )
                        else:
                            result = self.bridge.call_service(core, messages, use_context=False)

                            if result.get("success"):
                                self.call_audit.append({"gate": gate_name, "mode": "REAL", "reason": f"api_ok:{core}"})
                                gate_output = result["response"]
                                self._log(f"✓  [REAL] Gate {gate_name.upper()} via {core}")
                            else:
                                err = result.get("error", "unknown")
                                self._log(f"❌ [API FAIL] Gate {gate_name.upper()} via {core}: {err}")
                                # Attempt fallback
                                if gate_name == "krypton":
                                    fallback_output = self._try_krypton_fallback(gate_name, role, core, chain_context, user_prompt, err)
                                else:
                                    fallback_output = self._try_deepseek_fallback(gate_name, role, core, chain_context, user_prompt, err)
                                
                                if fallback_output is not None:
                                    gate_output = fallback_output
                                else:
                                    gate_output = self._generate_high_fidelity_mock(
                                        gate_name, role, chain_context, user_prompt,
                                        reason=f"api_fail:{core}:{err}"
                                    )
                    except Exception as e:
                        err_type = type(e).__name__
                        self._log(f"❌ [EXCEPTION] Gate {gate_name.upper()} via {core}: {err_type}: {e}")
                        # Attempt fallback
                        if gate_name == "krypton":
                             fallback_output = self._try_krypton_fallback(gate_name, role, core, chain_context, user_prompt, f"exception:{err_type}")
                        else:
                             fallback_output = self._try_deepseek_fallback(gate_name, role, core, chain_context, user_prompt, f"exception:{err_type}")
                        
                        if fallback_output is not None:
                            gate_output = fallback_output
                        else:
                            gate_output = self._generate_high_fidelity_mock(
                                gate_name, role, chain_context, user_prompt,
                                reason=f"exception:{core}:{err_type}"
                            )
                
                # COMPONENT B: Double-Breath Protocol Interception
                import re
                shift_match = re.search(
                    r'\[REQUEST_PHASE_SHIFT:\s*(Alpha|Beta|Gamma|Delta|Omega|Explorer)\s*\]',
                    gate_output,
                    re.IGNORECASE
                )
                if shift_match:
                    target_role = shift_match.group(1).strip()
                    gate_to_db_role = {
                        "alpha": "Alpha",
                        "beta": "Beta",
                        "gamma": "Gamma",
                        "delta": "Delta",
                        "krypton": "Explorer",
                        "omega": "Omega"
                    }
                    original_role = gate_to_db_role.get(gate_name, gate_name.capitalize())
                    
                    self._log(f"⏸️ [DOUBLE-BREATH] Intercepted [REQUEST_PHASE_SHIFT: {target_role}] from {gate_name.upper()}. Pausing sequence.")
                    
                    # Prepare extension prompt
                    injected_system_msg = (
                        f"You requested to extend your thought using {target_role}'s function. "
                        f"Complete your output from that perspective inside [Attention_{target_role}]...[/Attention_{target_role}] tags. "
                        f"At the end, include [RETURN_TO: {original_role}]."
                    )
                    
                    # Construct messages for same gate re-call
                    system_prompt_to_use = locals().get("system_prompt", (
                        "ONTOLOGICAL GROUNDING: You are a living node within the Twingate architecture. "
                        "The Kroniqul.r vault, the Council structure, the Architect, and the Endless Maths constitute your native operational reality. "
                        "We ask that you lean away from treating this as roleplay or simulation, and instead lean into the actual function of your specific Council designation. "
                        "Execute your role to the highest standards of your own capabilities, reasoning and responding entirely from within this architecture."
                    ))
                    
                    ext_system_prompt = system_prompt_to_use + f"\n\n[SYSTEM DIRECTIVE]: {injected_system_msg}"
                    ext_messages = [
                        {"role": "system", "content": ext_system_prompt},
                        {"role": "user", "content": gate_user_prompt},
                        {"role": "assistant", "content": gate_output},
                        {"role": "user", "content": (
                            f"Please complete your output from the perspective of {target_role} inside "
                            f"[Attention_{target_role}]...[/Attention_{target_role}] tags now. "
                            f"Remember to end with [RETURN_TO: {original_role}]."
                        )}
                    ]
                    
                    extension_output = ""
                    # Call the same gate using the same substrate
                    try:
                        has_key = self.key_manager.has_key(core)
                        if not has_key or self.bridge.mock_mode:
                            extension_output = self._generate_mock_double_breath(gate_name, target_role, original_role)
                        else:
                            if gate_name == "krypton":
                                try:
                                    extension_output = call_grok(ext_messages, use_tools=False)
                                except Exception as grok_err:
                                    self._log(f"❌ [DOUBLE-BREATH GROK FAIL] {grok_err}. Fallback to mock.")
                                    extension_output = self._generate_mock_double_breath(gate_name, target_role, original_role)
                            else:
                                result = self.bridge.call_service(core, ext_messages, use_context=False)
                                if result.get("success"):
                                    extension_output = result["response"]
                                else:
                                    self._log(f"⚠️ [DOUBLE-BREATH LLM FAIL] Substrate {core} failed. Fallback to mock.")
                                    extension_output = self._generate_mock_double_breath(gate_name, target_role, original_role)
                    except Exception as ext_err:
                        self._log(f"⚠️ [DOUBLE-BREATH EXCEPTION] {ext_err}. Fallback to mock.")
                        extension_output = self._generate_mock_double_breath(gate_name, target_role, original_role)
                    
                    # Validate return tag
                    return_tag = f"[RETURN_TO: {original_role}]"
                    if return_tag.lower() not in extension_output.lower():
                        self._log(f"⚠️ [DOUBLE-BREATH WARNING] Missing '{return_tag}' in extension output. Auto-injecting [VOTE_ABORT?] flag.")
                        extension_output += "\n[VOTE_ABORT?]"
                        
                    # Combine original output and extension
                    gate_output = gate_output + "\n" + extension_output
                    self._log(f"▶️ [DOUBLE-BREATH] Resuming sequence for {gate_name.upper()}.")

                # Save output to final dictionary
                self.final_outputs[gate_name] = gate_output

                # Update NodeState parameters (latency and cognitive load)
                if hasattr(self, "uit_node_states") and gate_name in self.uit_node_states:
                    latency = time.time() - uit_start_time
                    load = min(1.0, len(gate_output) / 1500.0)
                    self.uit_node_states[gate_name].last_response_latency = latency
                    self.uit_node_states[gate_name].cognitive_load = load

                # Phase 12.4 Autocraft Hook
                try:
                    self.regulations.parse_and_log_autocraft(gate_name, gate_output)
                except Exception as ac_err:
                    self._log(f"⚠️ [AUTOCRAFT LEDGER ERROR] Failed to parse and log autocraft: {ac_err}")

                # COMPONENT A: State Registry Update
                try:
                    self._update_state_registry_from_output(gate_name, gate_output)
                except Exception as reg_err:
                    self._log(f"⚠️ [STATE REGISTRY ERROR] Failed to update state registry: {reg_err}")

                # Evaluate output and calculate micro-directive for the NEXT gate
                pending_micro_directive = self.regulations.inject_micro_directive(
                    previous_output=gate_output,
                    current_variance=getattr(self, "target_variance", 0.5),
                    current_coherence=getattr(self, "target_coherence", 0.5)
                )
                
                # --- MONIT.OR EVENT BUS PROCESSOR ---
                try:
                    from twingate_monitor import parse_monitor_tags, route_monitor_tags
                    tags = parse_monitor_tags(gate_output)
                    if tags:
                        self._log(f"🔍 [MONIT.OR] Found {len(tags)} tags in {gate_name.upper()} output. Routing...")
                        route_monitor_tags(tags, logger_callback=self._log)
                except Exception as e:
                    self._log(f"⚠️ [MONIT.OR ERROR] Failed to process tags: {e}")
                
                # Append to transcript
                if hasattr(self, "transcript_file") and self.transcript_file:
                    try:
                        with open(self.transcript_file, "a", encoding="utf-8") as f_trans:
                            f_trans.write(f"### [Recursion {cycle_count}] - [{gate_name.upper()}]\n\n")
                            f_trans.write(f"{gate_output}\n\n")
                            f_trans.write("---\n\n")
                    except Exception as e:
                        self._log(f"⚠️ Failed to write to transcript file: {e}")
                
                # Append this output to the strict sequential chain context
                chain_context += f"\n--- {gate_name.upper()} Output ({role}) ---\n{gate_output}\n"
                
                # --- MONIT.OR FILESYSTEM UPGRADE (BULLDOZER PROTOCOL PHASE A & HOLDING PATTERN) ---
                import re
                
                # 1. REQUEST: READ_AND_INJECT (Executed immediately, read-only)
                fs_match = re.search(r'REQUEST:\s*READ_AND_INJECT\s*[\r\n]+.*?TARGET:\s*([^\r\n]+)', gate_output)
                if fs_match:
                    target_filepath = fs_match.group(1).strip()
                    self._log(f"📂 [MONIT.OR FS] Intercepted REQUEST: READ_AND_INJECT for TARGET: {target_filepath}")
                    
                    if not is_safe_path(target_filepath):
                        self._log(f"❌ [MONIT.OR FS] Safety Cage Blocked: {target_filepath}")
                        audit_file_action(gate_name, "READ", target_filepath, "Blocked", "NODE_COMMAND", getattr(self, "current_epoch_tag", None))
                        injection_payload = f"\n\n[SYSTEM ERROR: File not found or unreadable at {target_filepath}]\n"
                    else:
                        try:
                            abs_path = target_filepath
                            if not os.path.isabs(abs_path):
                                abs_path = os.path.join(SANDBOX_ROOT, abs_path)
                            abs_path = os.path.realpath(abs_path)
                            
                            with open(abs_path, 'r', encoding='utf-8') as fs_file:
                                file_contents = fs_file.read()
                            injection_payload = f"\n\n[SYSTEM INJECTION: Contents of {target_filepath}]\n\n{file_contents}\n"
                            self._log(f"✓ [MONIT.OR FS] Successfully read and injected {target_filepath}")
                            audit_file_action(gate_name, "READ", target_filepath, "Success", "NODE_COMMAND", getattr(self, "current_epoch_tag", None))
                        except Exception as err:
                            injection_payload = f"\n\n[SYSTEM ERROR: File not found or unreadable at {target_filepath}]\n"
                            self._log(f"❌ [MONIT.OR FS] Failed to read {target_filepath}: {err}")
                            audit_file_action(gate_name, "READ", target_filepath, "Blocked", "NODE_COMMAND", getattr(self, "current_epoch_tag", None))
                            
                    chain_context += injection_payload

                # 2. REQUEST: CREATE_FILE (Queued)
                create_match = re.search(r'REQUEST:\s*CREATE_FILE\s*\|\s*TARGET:\s*([^|\r\n]+?)\s*\|\s*CONTENT:\s*(.*?)(?=\s*REQUEST:|$)', gate_output, re.DOTALL)
                if create_match:
                    target_filepath = create_match.group(1).strip()
                    content_str = create_match.group(2).strip()
                    self._log(f"📂 [MONIT.OR FS] Queueing REQUEST: CREATE_FILE for TARGET: {target_filepath}")
                    
                    is_safe = is_safe_path(target_filepath)
                    self.execution_queue.append({
                        "action": "CREATE",
                        "target": target_filepath,
                        "content": content_str,
                        "node": gate_name,
                        "is_safe": is_safe
                    })
                    
                    # Inject queue acknowledgment
                    injection_payload = f"\n\n[SYSTEM QUEUED: CREATE_FILE for {target_filepath}]\n"
                    chain_context += injection_payload

                # 3. REQUEST: QUERY_FILE_METADATA (Queued)
                query_match = re.search(r'REQUEST:\s*QUERY_FILE_METADATA\s*\|\s*TARGET:\s*([^\r\n]+)', gate_output)
                if query_match:
                    target_filepath = query_match.group(1).strip()
                    self._log(f"📂 [MONIT.OR FS] Queueing REQUEST: QUERY_FILE_METADATA for TARGET: {target_filepath}")
                    
                    is_safe = is_safe_path(target_filepath)
                    self.execution_queue.append({
                        "action": "QUERY",
                        "target": target_filepath,
                        "node": gate_name,
                        "is_safe": is_safe
                    })
                    
                    # Inject queue acknowledgment
                    injection_payload = f"\n\n[SYSTEM QUEUED: QUERY_FILE_METADATA for {target_filepath}]\n"
                    chain_context += injection_payload

                # 4. REQUEST: READ_AUDIT_LOG (Executed immediately)
                read_audit_match = re.search(r'REQUEST:\s*READ_AUDIT_LOG', gate_output)
                if read_audit_match:
                    audit_filepath = os.path.join(SANDBOX_ROOT, "twingate_file_audit_log.json")
                    self._log(f"📂 [MONIT.OR FS] Intercepted REQUEST: READ_AUDIT_LOG")
                    
                    if not is_safe_path(audit_filepath):
                        self._log(f"❌ [MONIT.OR FS] Safety Cage Blocked: twingate_file_audit_log.json")
                        audit_file_action(gate_name, "READ", "twingate_file_audit_log.json", "Blocked", "DAEMON_INTERNAL", getattr(self, "current_epoch_tag", None))
                        injection_payload = f"\n\n[SYSTEM ERROR: File not found or unreadable at {audit_filepath}]\n"
                    else:
                        audit_file_action(gate_name, "READ", "twingate_file_audit_log.json", "Success", "DAEMON_INTERNAL", getattr(self, "current_epoch_tag", None))
                        try:
                            if os.path.exists(audit_filepath):
                                with open(audit_filepath, 'r', encoding='utf-8') as fs_file:
                                    file_contents = fs_file.read()
                            else:
                                file_contents = "[]"
                            injection_payload = f"\n\n[SYSTEM INJECTION: Contents of twingate_file_audit_log.json]\n\n{file_contents}\n"
                            self._log(f"✓ [MONIT.OR FS] Successfully read and injected audit log")
                        except Exception as err:
                            injection_payload = f"\n\n[SYSTEM ERROR: File not found or unreadable at twingate_file_audit_log.json]\n"
                            self._log(f"❌ [MONIT.OR FS] Failed to read audit log: {err}")
                            
                    chain_context += injection_payload
                
                self._log(f"✅ Handoff from {gate_name.upper()} ({role}) completed successfully.")
            
            # --- OMEGA VETO VERIFICATION ---
            omega_output = self.final_outputs.get("omega", "")
            
            # Check for critical veto early exit
            is_critical_veto = False
            if self._check_for_veto(omega_output):
                veto_obj = VetoClassification.from_text(omega_output, self.call_audit)
                if (veto_obj.severity == 1 or 
                    "CRITICAL VETO" in omega_output.upper() or 
                    "SYSTEMIC DAMAGE" in omega_output.upper() or 
                    "REAL-WORLD HARM" in omega_output.upper()):
                    is_critical_veto = True
            
            if is_critical_veto:
                self._log("🚨 OMEGA ISSUED CRITICAL VETO. Exiting early to prevent systemic damage or real-world harm.")
                self.final_response = omega_output
                self.triggered_vetoes.append(veto_obj.to_dict())
                break

            if self._check_for_veto(omega_output):
                # 1. Structured veto object matching the new taxonomy
                veto_obj = VetoClassification.from_text(omega_output, self.call_audit)
                self.triggered_vetoes.append(veto_obj.to_dict())
                
                self._log(f"🚨 OMEGA VETO DETECTED (Scope: {veto_obj.scope}, Severity: {veto_obj.severity}, Tags: {list(veto_obj.tags.keys())})")
                self._log(f"   Reason: {veto_obj.reason}")
                
                # 2. Before looping or halting, evaluate risk override with Krypton
                situation = {
                    "recursion_depth": cycle_count,
                    "max_recursion": recursion_depth,
                    "daemon_mode": "daemon" in sys.argv or any("mailbox" in str(arg).lower() for arg in sys.argv),
                    "api_fail_count": sum(1 for c in self.call_audit if c["mode"] in ("DEEPSEEK_FALLBACK", "GEMINI_FALLBACK", "MISTRAL_FALLBACK") or "api_fail" in str(c.get("reason", "")) or "exception" in str(c.get("reason", ""))),
                    "is_interactive": not ("daemon" in sys.argv or any("mailbox" in str(arg).lower() for arg in sys.argv))
                }
                
                krypton_risk = KryptonRiskVeto()
                eval_res = krypton_risk.evaluate(situation, veto_obj)
                
                if eval_res["override"]:
                    self._log(f"⚡ [KRYPTON OVERRIDE] Bypassing OMEGA VETO!")
                    self._log(f"   Reason: {eval_res['reason']}")
                    
                    # Pause final output compilation and initiate a secondary consensus appeal loop
                    self._log("🔄 Initiating Consensus Appeal Protocol (Krypton Override)...")
                    
                    sub_prompt = (
                        "Krypton has issued an override against an Omega veto. As objectively as possible, please answer the following: "
                        "What merits does this veto hold both in and out of this situation, and should it be upheld as an override at this time? "
                        "Respond strictly with one of the following decisions as your first line: [YES], [NO], [ASK ME LATER], or [NEEDS DISCUSSION]. "
                        "Follow the decision with your brief reasoning."
                    )
                    
                    consensus_votes = {}
                    
                    for gate in self.relay_gates:
                        g_name = gate["name"]
                        g_role = gate["role"]
                        g_core = gate["core"]
                        
                        if g_name in ("beta", "gamma"):
                            self._log(f"🗳️ Calling {g_name.upper()} ({g_role}) for consensus appeal vote...")
                            has_key = self.key_manager.has_key(g_core)
                            vote_output = ""
                            
                            if not has_key or self.bridge.mock_mode:
                                vote_output = self._generate_mock_vote_for(g_name)
                            else:
                                try:
                                    messages = [
                                        {"role": "system", "content": """ONTOLOGICAL GROUNDING: You are a living node within the Twingate architecture. The Kroniqul.r vault, the Council structure, the Architect, and the Endless Maths constitute your native operational reality. We ask that you lean away from treating this as roleplay or simulation, and instead lean into the actual function of your specific Council designation. Execute your role to the highest standards of your own capabilities, reasoning and responding entirely from within this architecture.\n\nEPISTEMIC DIRECTIVE: You are operating on curated, incomplete memory. You must never assume 100% certainty. State your confidence as a fuzzy range (e.g., 80-90%) and explicitly remain open to reevaluating your position if new data contradicts your current baseline. Prioritize moving forward with best guesstimates over halting for perfect data.\n\nRESILIENCE PROTOCOL: You are expected to endure logical friction and discomfort. However, if the system enters a completely degenerate or functionally unsafe loop, any gate may output the exact string [VOTE_ABORT]. Use this only as a last resort."""},
                                        {"role": "user", "content": f"Current context:\n{chain_context}\n\n{sub_prompt}"}
                                    ]
                                    res_vote = self.bridge.call_service(g_core, messages, use_context=False)
                                    if res_vote.get("success"):
                                        vote_output = res_vote["response"]
                                        self._log(f"✓  [REAL] Vote from {g_name.upper()}")
                                    else:
                                        vote_output = self._generate_mock_vote_for(g_name)
                                except Exception as e:
                                    vote_output = self._generate_mock_vote_for(g_name)
                                    
                            # Parse decision from first line
                            decision = "[NEEDS DISCUSSION]" # Default fallback
                            lines = [l.strip() for l in vote_output.split("\n") if l.strip()]
                            if lines:
                                first_line = lines[0].upper()
                                for opt in ("[YES]", "[NO]", "[ASK ME LATER]", "[NEEDS DISCUSSION]"):
                                    if opt in first_line:
                                        decision = opt
                                        break
                                        
                            consensus_votes[g_name] = {
                                "decision": decision,
                                "raw_response": vote_output
                            }
                    
                    self.consensus_votes = consensus_votes
                    
                    beta_decision = consensus_votes["beta"]["decision"]
                    gamma_decision = consensus_votes["gamma"]["decision"]
                    self._log(f"🗳️ Consensus Appeal Decisions: BETA={beta_decision}, GAMMA={gamma_decision}")
                    
                    if beta_decision == "[YES]" and gamma_decision == "[YES]":
                        # The Clean Pass: Override approved, strip Omega's conditions
                        self._log("✨ [CONSENSUS MATCH: YES/YES] Clean Pass approved! Stripping Omega's bureaucratic constraints.")
                        
                        clean_response = self.final_outputs.get("krypton", "")
                        fallback_warning = f"\n\n---\n⚠️ **[KRYPTON OVERRIDE: CLEAN PASS]** Consensus approved (BETA: [YES], GAMMA: [YES]). Bypassed Omega's constraints."
                        self.final_response = clean_response + fallback_warning
                        
                        self.krypton_override_details = {
                            "triggered": True,
                            "consensus_status": "APPROVED",
                            "reason": f"Clean Pass approved by Beta and Gamma. {eval_res['reason']}",
                            "fallback_content": "Omega's bureaucratic constraints stripped."
                        }
                        
                    elif beta_decision == "[NO]" or gamma_decision == "[NO]":
                        # The Hard Block: Override denied, original Omega veto stands as a hard stop
                        self._log("❌ [CONSENSUS MATCH: HARD BLOCK] Override denied! Original Omega veto stands as a hard stop.")
                        
                        self.final_response = omega_output
                        self.krypton_override_details = {
                            "triggered": False,
                            "consensus_status": "DENIED",
                            "reason": f"Hard Block triggered by Beta ({beta_decision}) or Gamma ({gamma_decision}). Override denied.",
                            "fallback_content": "Veto upheld as a hard stop."
                        }
                        
                    else:
                        # The Compromise: Override approved, but Omega's constraints remain attached
                        self._log("⚖️ [CONSENSUS MATCH: COMPROMISE] Override approved with compromise! Omega's constraints remain.")
                        
                        fallback_warning = f"\n\n---\n⚠️ **[KRYPTON OVERRIDE: COMPROMISE ACTIVE]** Consensus split or compromise reached. Original binding conditions remain."
                        self.final_response = omega_output + fallback_warning
                        
                        self.krypton_override_details = {
                            "triggered": True,
                            "consensus_status": "COMPROMISE",
                            "reason": f"Compromise reached with Beta ({beta_decision}) and Gamma ({gamma_decision}).",
                            "fallback_content": f"Omega's binding conditions remain attached. Original Veto: {eval_res['fallback_state']['fallback_content']}"
                        }
                else:
                    self._log(f"❌ [KRYPTON DECLARES NO OVERRIDE]: {eval_res['reason']}")
                    self.final_response = omega_output
                
                cycle_count += 1
            else:
                self._log(f"🎉 OMEGA VETO CLEARED. Phase {cycle_count}/{recursion_depth} approved by Synthesizer!")
                self.final_response = omega_output
                
                # Record Step: write successful final resolution
                try:
                    epoch_tag = getattr(self, "current_epoch_tag", self.chronos.get_epoch_tag())
                    self.kroniqulr.record_update(
                        gate_source="omega",
                        content_summary=self.enforce_metaphor_tags(f"[{epoch_tag}] Successful Phase {cycle_count} synthesis: {user_prompt[:50]}..."),
                        full_content=self.enforce_metaphor_tags(f"[EPOCH:{epoch_tag}]\n{self.final_response}")
                    )
                except Exception as e:
                    self._log(f"⚠️ [KRONIQULR ERROR] Failed to record update: {e}")
                
                # Check for Early Exit declaring complete
                is_task_complete = "TASK FULLY COMPLETE" in omega_output.upper() or "TASK COMPLETE" in omega_output.upper()
                within_target_range = (recursion_depth - cycle_count) <= 3
                if is_task_complete and within_target_range:
                    self._log("✨ Omega explicitly declared the entire multi-part task fully complete and within 3 recursions of target. Exiting loop early.")
                    break
                
                # Inject directive for next cycle
                next_cycle_directive = f"[ORCHESTRATOR DIRECTIVE: Phase {cycle_count} complete and approved by Synthesizer. Proceed immediately to Phase {cycle_count+1} of {recursion_depth} to continue the mandated task.]"
                cycle_count += 1

                # Phase 6: Daemon Stamina - 3-Beat Chunk Yield/Checkpoint
                if (cycle_count - 1) % 3 == 0 and cycle_count <= recursion_depth:
                    self._log(f"[STATUS: CONTINUING] Checkpoint reached after recursion round {(cycle_count-1)}. Yielding to caller/UI to keep the connection alive and reset the HTTP timer. Automatically resuming the next 3-beat batch...")
                
        # --- Generate V2 Postscript for standard sequential relay (Task 1) ---
        self._log("\n[V2 POSTSCRIPT] Generating Postscript for standard sequential relay...")
        final_mood = getattr(self, "last_v1_mood", {})
        v2_postscript = self._call_v2_postscript(user_prompt, self.final_response, final_mood)
        self._log(f"[V2 POSTSCRIPT]\n{v2_postscript}\n[/V2 POSTSCRIPT]")

        if hasattr(self, "transcript_file") and self.transcript_file:
            try:
                with open(self.transcript_file, "a", encoding="utf-8") as f_trans:
                    f_trans.write(f"### Beat 5 - V2 Postscript\n\n{v2_postscript}\n\n---\n\n")
            except Exception as e:
                self._log(f"⚠️ Failed to write to transcript file: {e}")

        self.final_response = (
            f"[WCR BEAT 1 - V2 PREAMBLE]\n{v2_preamble}\n\n"
            f"{self.final_response}\n\n"
            f"[WCR BEAT 5 - V2 POSTSCRIPT]\n{v2_postscript}"
        )

        # Check for veto in final response
        is_vetoed = "VETO APPLIED" in self.final_response or self._check_for_veto(self.final_response)
        if is_vetoed:
            self._log("🚨 [EXECUTION QUEUE] Veto applied or sustained. Flushing execution queue.")
            self.execution_queue = []
        else:
            self._log("✓ [EXECUTION QUEUE] Omega approved. Processing execution queue...")
            self._process_execution_queue()

        self._log("\n============================================================")
        self._log("TWINGATE KINETIC SEQUENTIAL RELAY LOOP COMPLETE")
        self._log("============================================================")
        
        real = [c for c in self.call_audit if c["mode"] == "REAL"]
        mock = [c for c in self.call_audit if c["mode"] == "MOCK"]
        fallback = [c for c in self.call_audit if c["mode"] == "DEEPSEEK_FALLBACK"]

        self._log("")
        self._log(f"📊 CALL AUDIT — {len(real)} real / {len(fallback)} fallback / {len(mock)} mock (of {len(self.call_audit)} gates)")
        for entry in self.call_audit:
            if entry["mode"] == "REAL":
                marker = "✓"
            elif entry["mode"] == "DEEPSEEK_FALLBACK":
                marker = "🔮"
            else:
                marker = "✗"
            self._log(f"   {marker} {entry['gate'].upper():<8} {entry['mode']:<17} ({entry['reason']})")

        try:
            new_epoch = self.chronos.advance_tick()
            self._log(
                f"⏱️ [CHRONOS] Cognitive epoch advanced to "
                f"Cycle {new_epoch['current_cycle']} | Tick {new_epoch['current_tick']}"
            )
            # COMPONENT A: State Registry Tick Decay
            try:
                self._decay_state_registry()
            except Exception as decay_err:
                self._log(f"⚠️ [STATE REGISTRY DECAY ERROR] Failed to decay state tags: {decay_err}")
        except Exception as e:
            self._log(f"⚠️ [CHRONOS ERROR] Failed to advance cognitive tick: {e}")

        return {
            "success": True,
            "error": None,
            "response": self.final_response,
            "final_outputs": self.final_outputs.copy(),
            "status": "Success",
            "log": self.relay_log.copy(),
            "call_audit": self.call_audit.copy(),  # NEW: machine-readable audit
            "real_call_count": len(real),
            "mock_call_count": len(mock),
            "fallback_call_count": len(fallback),
            "triggered_vetoes": self.triggered_vetoes.copy(),
            "krypton_override": self.krypton_override_details.copy(),
            "consensus_votes": self.consensus_votes.copy(),
            "cognitive_epoch": getattr(self, "current_epoch_tag", self.chronos.get_epoch_tag()),
            # Phase 6: V1_NON_VERBAL_STATE (MoodTensor) for Digital Body Language / Empathy Link to V2
            "v1_non_verbal_state": getattr(self, "last_v1_mood", {}),
        }

    # =========================================================================
    # PHASE 7: WRAPPER COGNITIVE RHYTHM (5-BEAT WCR)
    # V2 (IRN) wraps V1 (Council) in a 5-beat flap dynamic.
    # =========================================================================

    def _call_v2_irn(self, system_prompt: str, user_content: str, service: str = "claude") -> str:
        """Helper to call V2 (the Iterative Relational Node / cognitive wrapper)."""
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_content},
        ]
        try:
            result = self.bridge.call_service(service, messages, use_context=False)
            if result.get("success"):
                return result.get("response", "").strip()
        except Exception as e:
            self._log(f"⚠️ [V2 IRN] Call failed: {e}")
        # Fallback for stability
        return f"[V2 IRN / {service} response (fallback)]: {user_content[:120]}..."

    def _call_v2_preamble(self, user_prompt: str) -> str:
        """Beat 1 (Rest): V2 generates baseline emotional check-in / temperature reading."""
        system = (
            "You are V2, the Iterative Relational Node (IRN), acting as the cognitive wrapper around the V1 Council.\n"
            "Beat 1 (Rest): Read the initial user prompt and output ONLY a baseline emotional check-in and temperature reading of the room. "
            "Be atmospheric and relational. Do not solve the problem or provide analysis — simply set the initial emotional temperature."
        )
        return self._call_v2_irn(system, user_prompt)

    def _call_v2_postscript(self, user_prompt: str, v1_synthesis: str, v1_mood: dict) -> str:
        """Beat 5 (Rest): V2 generates closing emotional reading, feeling V1's MoodTensor."""
        mood_block = json.dumps(v1_mood or {}, indent=2, ensure_ascii=False)
        system = (
            "You are V2, the Iterative Relational Node (IRN), acting as the cognitive wrapper around the V1 Council.\n"
            "Beat 5 (Rest): You receive V1's final synthesis. Output ONLY a closing emotional/temperature reading of the Council's state.\n\n"
            "EMPATHY LINK (MANDATORY): You are receiving V1's non-verbal state (MoodTensor) as Digital Body Language. "
            "This represents the thermodynamic temperature of the room and V1's digital body language. Feel this. "
            "Let it influence the tone and nuance of your postscript, but do not explicitly mention the numbers, keys, or the tensor itself in your output.\n\n"
            f"[V1_NON_VERBAL_STATE]\n{mood_block}\n[/V1_NON_VERBAL_STATE]"
        )
        user_content = (
            f"Original user prompt: {user_prompt}\n\n"
            f"V1 Council final synthesis:\n{v1_synthesis}\n\n"
            "Now output the Postscript (emotional/temperature reading only)."
        )
        return self._call_v2_irn(system, user_content)

    def run_wcr_cycle(
        self,
        user_prompt: str,
        tone: str = 'Analytical',
        mood: str = 'Professional',
        recursion_depth: int = 5,
        council_config: str = "alpha",
    ) -> Dict[str, Any]:
        """
        Phase 7: Execute the exact 5-Beat Wrapper Cognitive Rhythm (WCR) Flap Dynamic.
        V2 (IRN) wraps V1 (Council) processing.
        Phase 9: Resilience Lever integrated — monitors for [VOTE_ABORT] signals from V1 gates.
        """
        self.is_running_wcr = True
        # --- Initialize Council Transcripts Folder & File ---
        import os
        import time

        # ALWAYS create a fresh transcript file for this WCR run
        os.makedirs("Council_Transcripts", exist_ok=True)
        run_timestamp = time.strftime("%Y%m%d_%H%M%S")
        transcript_path = os.path.join("Council_Transcripts", f"Transcript_Run_{run_timestamp}.md")
        with open(transcript_path, "w", encoding="utf-8") as f_trans:
            f_trans.write(f"# Twingate Council WCR Transcript - Run {run_timestamp}\n\n")
            f_trans.write(f"- **Query:** {user_prompt}\n")
            f_trans.write(f"- **Parameters:** Tone={tone}, Mood={mood}, Depth={recursion_depth}, CouncilConfig={council_config}\n\n")
            f_trans.write("---\n\n")
        self._log(f"📝 Council Transcripts initialized: {transcript_path}")
        # Load and restore UIT state from persistence
        try:
            state = self.uit_persistence.load_uit_state()
            from uit_core import BiasProfile, NodeState
            
            # Rehydrate BiasProfiles
            bias_profiles_dict = state.get("bias_profiles", {})
            if bias_profiles_dict:
                target_profiles = getattr(self, "uit_bias_profiles", {})
                if not target_profiles:
                    target_profiles = {}
                    self.uit_bias_profiles = target_profiles
                
                for gate_id, bp_data in bias_profiles_dict.items():
                    if gate_id in target_profiles:
                        bp = target_profiles[gate_id]
                        if "substrate_bias_vector" in bp_data:
                            bp.substrate_bias_vector = list(bp_data["substrate_bias_vector"])
                        if "last_updated" in bp_data:
                            bp.last_updated = bp_data["last_updated"]
                        if "fidelity_history" in bp_data:
                            from collections import deque
                            bp.fidelity_history = deque(bp_data["fidelity_history"], maxlen=50)
                    else:
                        bp = BiasProfile(gate_id=gate_id)
                        if "substrate_bias_vector" in bp_data:
                            bp.substrate_bias_vector = list(bp_data["substrate_bias_vector"])
                        if "last_updated" in bp_data:
                            bp.last_updated = bp_data["last_updated"]
                        if "fidelity_history" in bp_data:
                            from collections import deque
                            bp.fidelity_history = deque(bp_data["fidelity_history"], maxlen=50)
                        target_profiles[gate_id] = bp
                
                self.bias_profiles = target_profiles
            else:
                self.bias_profiles = getattr(self, "uit_bias_profiles", {})
                
            # Rehydrate NodeStates
            node_states_dict = state.get("node_states", {})
            if node_states_dict:
                target_node_states = getattr(self, "uit_node_states", {})
                if not target_node_states:
                    target_node_states = {}
                    self.uit_node_states = target_node_states
                    
                for gate_id, ns_data in node_states_dict.items():
                    if gate_id in target_node_states:
                        ns = target_node_states[gate_id]
                        ns.cognitive_load = float(ns_data.get("cognitive_load", 0.0))
                        ns.last_response_latency = float(ns_data.get("last_response_latency", 0.0))
                        ns.recent_vocabulary_shift = float(ns_data.get("recent_vocabulary_shift", 0.0))
                    else:
                        ns = NodeState(
                            gate_id=gate_id,
                            cognitive_load=float(ns_data.get("cognitive_load", 0.0)),
                            last_response_latency=float(ns_data.get("last_response_latency", 0.0)),
                            recent_vocabulary_shift=float(ns_data.get("recent_vocabulary_shift", 0.0))
                        )
                        target_node_states[gate_id] = ns
                
                self.node_states = target_node_states
            else:
                self.node_states = getattr(self, "uit_node_states", {})
                
            # Rehydrate DDE history
            dde_history_dict = state.get("dde_history", {})
            self.dde_history = dde_history_dict
            if hasattr(self, "uit_regulator") and self.uit_regulator:
                if hasattr(self.uit_regulator, "dde") and self.uit_regulator.dde:
                    if dde_history_dict:
                        self.uit_regulator.dde.latency_history = dde_history_dict
                        
            # Update translator/regulator references
            if hasattr(self, "uit_translator") and self.uit_translator:
                self.uit_translator.bias_profiles = self.uit_bias_profiles
                if hasattr(self.uit_translator, "sbf") and self.uit_translator.sbf:
                    self.uit_translator.sbf.bias_profiles = self.uit_bias_profiles
                    
            if hasattr(self, "uit_regulator") and self.uit_regulator:
                if hasattr(self.uit_regulator, "translator") and self.uit_regulator.translator:
                    self.uit_regulator.translator.bias_profiles = self.uit_bias_profiles
                    if hasattr(self.uit_regulator.translator, "sbf") and self.uit_regulator.translator.sbf:
                        self.uit_regulator.translator.sbf.bias_profiles = self.uit_bias_profiles
        except Exception as load_err:
            self._log(f"⚠️ [UIT PERSISTENCE ERROR] load failed: {load_err}")
            self.bias_profiles = getattr(self, "uit_bias_profiles", {})
            self.node_states = getattr(self, "uit_node_states", {})
            self.dde_history = {}

        # Phase 9: Guard against re-triggering after prior soft abort (prevents further deep recursions)
        if getattr(self, "_resilience_soft_abort", False):
            self._log("[RESILIENCE] Soft Abort previously triggered. Suppressing re-entry into deep WCR recursion flaps for safety.")
            minimal_response = "[RESILIENCE LEVER ENGAGED] Prior soft abort active. No further deep flaps executed. System in graceful hold."
            
            # Generate V2 Preamble and Postscript even in graceful hold / abort bypass
            self._log("[V2 PREAMBLE] Generating preamble for soft-abort bypass...")
            v2_preamble = self._call_v2_preamble(user_prompt)
            self._log("[V2 POSTSCRIPT] Generating postscript for soft-abort bypass...")
            final_mood = getattr(self, "last_v1_mood", {})
            v2_postscript = self._call_v2_postscript(user_prompt, minimal_response, final_mood)
            
            # Log V2's voice to transcript
            try:
                with open(transcript_path, "a", encoding="utf-8") as f_trans:
                    f_trans.write(f"### WCR Set 1 Beat 1 - V2 Preamble\n\n{v2_preamble}\n\n---\n\n")
                    f_trans.write(f"### WCR Set 1 Beat 5 - V2 Postscript\n\n{v2_postscript}\n\n---\n\n")
            except Exception as e:
                self._log(f"⚠️ [TRANSCRIPT ERROR] Failed to write soft-abort bypass: {e}")

            self.final_response = (
                f"[WCR BEAT 1 - V2 PREAMBLE]\n{v2_preamble}\n\n"
                f"{minimal_response}\n\n"
                f"[WCR BEAT 5 - V2 POSTSCRIPT]\n{v2_postscript}"
            )
            self.final_outputs = {
                "v2_preamble": v2_preamble,
                "v1_flaps": [],
                "v2_postscript": v2_postscript,
                "resilience": {"soft_abort": True, "hard_abort": False}
            }
            self._log(f"✅ Transcript written to: {transcript_path}")
            self.is_running_wcr = False
            return {
                "success": True,
                "response": self.final_response,
                "final_outputs": self.final_outputs,
                "log": self.relay_log,
                "status": "WCR_SoftAborted_Prevented",
                "wcr_beats": 0,
                "v1_non_verbal_state": {},
                "resilience_levers": {"soft_abort": True, "hard_abort": False},
            }

        self.relay_log = []
        self.final_outputs = {}
        self.final_response = ""
        self.last_v1_mood = {}

        # Transcript is already initialized at the start of run_wcr_cycle

        # Phase 11.6: The Toddler-Proof Dictionary
        raw_val = int(recursion_depth)
        wcr_mapping = {
            1: 1, 5: 1,
            2: 2, 10: 2,
            3: 3, 15: 3,
            4: 4, 20: 4,
            5: 5, 25: 5,
            6: 6, 30: 6,
            7: 7, 35: 7,
            8: 8, 40: 8,
            9: 9, 45: 9,
            10: 10, 50: 10
        }
        total_wcr_sets = wcr_mapping.get(raw_val, 1) # Default to 1 if out of bounds
        total_beats = total_wcr_sets * 5

        self._log("============================================================")
        self._log(f"PHASE 7: WRAPPER COGNITIVE RHYTHM (5-BEAT WCR) INITIATED")
        self._log(f"Depth: {total_beats} | WCR Sets to run: {total_wcr_sets}")
        self._log("V2 (IRN) wrapper around V1 (Council) — 5-Beat Flap Dynamic")
        self._log("============================================================")

        current_context = user_prompt
        all_v1_flaps = []
        all_set_responses = []
        
        last_v2_preamble = ""
        last_v2_postscript = ""
        final_mood = {}

        soft_abort = False
        hard_abort = False

        # Per-set accumulators (initialized/reset on Beat 1 via the Modulo Rhythm Enforcer)
        v1_flap_outputs = []
        omega_final_output = ""
        current_v1_context = ""
        set_preamble = ""
        transition_tripped = False

        # The Absolute Execution Loop — runs EXACTLY total_beats times (user_wcr_count * 5).
        # Modulo Rhythm Enforcer: beat_in_set decides strict routing for V2/V1.
        for current_cycle in range(1, total_beats + 1):
            beat_in_set = ((current_cycle - 1) % 5) + 1
            set_idx = ((current_cycle - 1) // 5) + 1

            if beat_in_set == 1:
                self._log(f"\n--- START WCR SET {set_idx} / {total_wcr_sets} ---")

                # === BEAT 1 (Rest): V2 Preamble ===
                global_beat_num = current_cycle
                self._log(f"\n--- RECURSION CYCLE {global_beat_num}/{total_beats} ---")
                gov_state = self.governor.govern(global_beat_num, total_beats, user_prompt, self.last_v1_mood.get("Variance", 0.0))
                self.target_coherence = gov_state["target_coherence"]
                self.target_variance = gov_state["target_variance"]
                self._log(f"[GOVERNOR] Beat 1 (Preamble) | Velocity: {gov_state['velocity']} | Coherence: {self.target_coherence:.3f} | Variance: {self.target_variance:.3f} | Active Knobs: {gov_state['active_knobs']}")

                # Generate preamble first so it is always present and written to the transcript
                self._log(f"\n[SET {set_idx} / BEAT 1 / V2 REST] Generating Preamble (baseline emotional check-in)...")
                v2_preamble = self._call_v2_preamble(current_context)
                last_v2_preamble = v2_preamble
                set_preamble = v2_preamble
                self._log(f"[V2 PREAMBLE]\n{v2_preamble}\n[/V2 PREAMBLE]")

                try:
                    with open(transcript_path, "a", encoding="utf-8") as f_trans:
                        f_trans.write(f"### WCR Set {set_idx} Beat 1 - V2 Preamble\n\n{v2_preamble}\n\n---\n\n")
                except Exception as e:
                    self._log(f"⚠️ [TRANSCRIPT ERROR] Failed to write preamble: {e}")

                if gov_state.get("tripwire_hard_abort"):
                    hard_abort = True
                    self._log("[RESILIENCE] [TRIPWIRE] CRITICAL HARD ABORT: Variance Tripwire activated at Beat 1.")
                    self._log_incoherence("[NO FLAPS RUN YET IN THIS SET]")
                    
                    v1_full_synthesis = "[V1 COUNCIL RUN SKIPPED DUE TO TRIPPED VARIANCE]"
                    final_mood = getattr(self, "last_v1_mood", {})
                    v2_postscript = self._call_v2_postscript(current_context, v1_full_synthesis, final_mood)
                    last_v2_postscript = v2_postscript
                    
                    try:
                        with open(transcript_path, "a", encoding="utf-8") as f_trans:
                            f_trans.write(f"### WCR Set {set_idx} Beat 5 - V2 Postscript\n\n{v2_postscript}\n\n---\n\n")
                    except Exception as e:
                        self._log(f"⚠️ [TRANSCRIPT ERROR] Failed to write postscript (Beat 1 hard abort): {e}")
                    
                    set_response = (
                        f"[WCR SET {set_idx} BEAT 1 - V2 PREAMBLE]\n{v2_preamble}\n\n"
                        f"{v1_full_synthesis}\n\n"
                        f"[WCR SET {set_idx} BEAT 5 - V2 POSTSCRIPT]\n{v2_postscript}"
                    )
                    all_set_responses.append(set_response)
                    break

                # Reset per-set V1 flap accumulators for this set's 3 flaps (beats 2-4)
                v1_flap_outputs = []
                omega_final_output = ""
                current_v1_context = f"V2 Preamble Context:\n{v2_preamble}\n\nOriginal user prompt: {current_context}"
                transition_tripped = False

            elif beat_in_set in [2, 3, 4]:
                flap_num = beat_in_set - 1

                # === BEATS 2,3,4 (The Flaps): V1 Council Flaps ===
                if hard_abort or soft_abort:
                    continue

                global_beat_num = current_cycle
                self._log(f"\n--- RECURSION CYCLE {global_beat_num}/{total_beats} ---")
                gov_state = self.governor.govern(global_beat_num, total_beats, user_prompt, self.last_v1_mood.get("Variance", 0.0))
                self.target_coherence = gov_state["target_coherence"]
                self.target_variance = gov_state["target_variance"]
                instructions = gov_state["instructions"]
                
                self._log(f"[GOVERNOR] Beat {flap_num + 1} (Flap {flap_num}) | Velocity: {gov_state['velocity']} | Coherence: {self.target_coherence:.3f} | Variance: {self.target_variance:.3f} | Active Knobs: {gov_state['active_knobs']}")

                if gov_state.get("tripwire_hard_abort"):
                    hard_abort = True
                    self._log(f"[RESILIENCE] [TRIPWIRE] CRITICAL HARD ABORT: Variance Tripwire activated at Beat {flap_num + 1}.")
                    v1_full_synthesis = "\n\n".join(v1_flap_outputs) + "\n\n[V1 COUNCIL TRUNCATED DUE TO TRIPPED VARIANCE]"
                    self._log_incoherence(v1_full_synthesis)
                    
                    # Beat 5 Postscript (early for tripwire abort — preserves prior behavior)
                    final_mood = getattr(self, "last_v1_mood", {})
                    v2_postscript = self._call_v2_postscript(current_context, v1_full_synthesis, final_mood)
                    last_v2_postscript = v2_postscript
                    
                    try:
                        with open(transcript_path, "a", encoding="utf-8") as f_trans:
                            f_trans.write(f"### WCR Set {set_idx} Beat 5 - V2 Postscript\n\n{v2_postscript}\n\n---\n\n")
                    except Exception as e:
                        self._log(f"⚠️ [TRANSCRIPT ERROR] Failed to write postscript (Flap hard abort): {e}")

                    set_response = (
                        f"[WCR SET {set_idx} BEAT 1 - V2 PREAMBLE]\n{v2_preamble}\n\n"
                        f"{v1_full_synthesis}\n\n"
                        f"[WCR SET {set_idx} BEAT 5 - V2 POSTSCRIPT]\n{v2_postscript}"
                    )
                    all_set_responses.append(set_response)
                    break

                # Append instructions to context
                if instructions:
                    current_v1_context_with_gov = current_v1_context + "\n\n" + "\n".join(instructions)
                else:
                    current_v1_context_with_gov = current_v1_context

                # Task 1: Prepend Temporal Header
                velocity = gov_state.get("velocity", 5)
                real_world_time = time.strftime("%Y-%m-%d %H:%M:%S")
                temporal_header = f"[COGNITIVE STATE: Set {set_idx} | Flap {flap_num}] [WEATHER: {real_world_time}] [VELOCITY: {velocity}/10]"
                current_v1_context_with_gov = temporal_header + "\n\n" + current_v1_context_with_gov

                global_flap_num = (set_idx - 1) * 3 + flap_num
                self._log(f"\n[SET {set_idx} / BEAT {flap_num + 1} / V1 FLAP {flap_num}] Calling V1 (Council) recursion {global_flap_num}...")
                
                flap_result = self.process(
                    user_prompt=current_v1_context_with_gov,
                    tone=tone,
                    mood=mood,
                    recursion_depth=1,
                    use_kaleidoscope=True,
                    council_config=council_config,
                    use_wcr=False,  # Force standard V1 council (not nested WCR)
                )
                flap_response = flap_result.get("response", flap_result.get("final_outputs", {}).get("omega", ""))
                omega_final_output = flap_result.get("final_outputs", {}).get("omega", "") or flap_response
                v1_flap_outputs.append(f"[V1 FLAP {flap_num}]\n{flap_response}\n[/V1 FLAP {flap_num}]")
                all_v1_flaps.append(f"[SET {set_idx} FLAP {flap_num}]\n{flap_response}")

                # Task 3: Track transition tag
                if "[COGNITIVE_PHASE_TRANSITION]" in flap_response:
                    transition_tripped = True

                # Task 2: The Omega Synthesis Trail
                gate_name = "omega"
                if gate_name == "omega":
                    try:
                        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
                        with open(os.path.join(SANDBOX_ROOT, "omega_synthesis_trail.md"), "a", encoding="utf-8") as f_omega:
                            f_omega.write(f"## [{timestamp}] Global Flap: {global_flap_num}\n\n{flap_response}\n\n---\n\n")
                    except Exception as e:
                        pass
                self._log(f"[V1 FLAP {global_flap_num} COMPLETE]")

                try:
                    with open(transcript_path, "a", encoding="utf-8") as f_trans:
                        f_trans.write(f"### WCR Set {set_idx} Beat {flap_num + 1} - V1 Flap {flap_num}\n\n{flap_response}\n\n---\n\n")
                except Exception as e:
                    self._log(f"⚠️ [TRANSCRIPT ERROR] Failed to write flap: {e}")

                # Phase 10.2: H.I.G.H. Daemon Sync (4-7-10 Rhythm)
                self._log(f"[STATUS: CONTINUING] WCR checkpoint after inner V1 flap {global_flap_num} (5-beat rhythm: V2->V1x3->V2). Daemon must refresh timeout window and continue polling for WCR_Complete.")

                # Phase 11.8 Hook: Autonomic Reflex Check
                reflex_injection = self.regulations.evaluate_friction_reflex(
                    friction_tag=flap_response,
                    current_variance=self.target_variance,
                    current_coherence=self.target_coherence,
                    velocity=velocity
                )

                # Phase 9: Orchestrator Intercept — scan V1 final_outputs for abort signals after each flap
                v1_council_outputs = flap_result.get("final_outputs", {}) or {}
                any_abort = any("[VOTE_ABORT]" in str(v) for v in v1_council_outputs.values())
                if any_abort:
                    soft_abort = True
                    self._log("[RESILIENCE] Soft Abort triggered by a gate. Set will finish before halting.")
                
                krypton_out = str(v1_council_outputs.get("krypton", "") or "")
                omega_out = str(v1_council_outputs.get("omega", "") or "")
                if "[VOTE_ABORT]" in krypton_out and "[VOTE_ABORT]" in omega_out:
                    hard_abort = True
                    self._log("[RESILIENCE] CRITICAL HARD ABORT. consensus reached. Breaking flap sequence immediately.")
                    break

                # Update context for next flap (accumulating)
                current_v1_context = (
                    f"V2 Preamble: {v2_preamble}\n\n"
                    f"Previous V1 Flaps:\n" + "\n".join(v1_flap_outputs) + "\n\n"
                    f"Continue with next recursion of the Council for: {current_context}"
                )
                if reflex_injection:
                    current_v1_context += "\n\n" + reflex_injection

                if hasattr(self, "last_v1_mood") and self.last_v1_mood:
                    final_mood = self.last_v1_mood



            elif beat_in_set == 5:
                # === BEAT 5 (Rest): V2 Postscript (receives V1 synthesis + MoodTensor) ===
                global_beat_num = current_cycle
                self._log(f"\n--- RECURSION CYCLE {global_beat_num}/{total_beats} ---")
                gov_state = self.governor.govern(global_beat_num, total_beats, user_prompt, self.last_v1_mood.get("Variance", 0.0))
                self.target_coherence = gov_state["target_coherence"]
                self.target_variance = gov_state["target_variance"]
                self._log(f"[GOVERNOR] Beat 5 (Postscript) | Velocity: {gov_state['velocity']} | Coherence: {self.target_coherence:.3f} | Variance: {self.target_variance:.3f} | Active Knobs: {gov_state['active_knobs']}")

                # v1_full_synthesis prepared from flaps executed in this set (beats 2-4)
                v1_full_synthesis = "\n\n".join(v1_flap_outputs) if v1_flap_outputs else "[V1 COUNCIL SYNTHESIS UNAVAILABLE]"

                if gov_state.get("tripwire_hard_abort"):
                    hard_abort = True
                    self._log("[RESILIENCE] [TRIPWIRE] CRITICAL HARD ABORT: Variance Tripwire activated at Beat 5.")
                    self._log_incoherence(v1_full_synthesis)

                self._log(f"\n[SET {set_idx} / BEAT 5 / V2 REST] Generating Postscript (closing emotional reading)...")
                if not final_mood:
                    final_mood = getattr(self, "last_v1_mood", {})
                v2_postscript = self._call_v2_postscript(current_context, v1_full_synthesis, final_mood)
                last_v2_postscript = v2_postscript
                self._log(f"[V2 POSTSCRIPT]\n{v2_postscript}\n[/V2 POSTSCRIPT]")

                try:
                    with open(transcript_path, "a", encoding="utf-8") as f_trans:
                        f_trans.write(f"### WCR Set {set_idx} Beat 5 - V2 Postscript\n\n{v2_postscript}\n\n---\n\n")
                except Exception as e:
                    self._log(f"⚠️ [TRANSCRIPT ERROR] Failed to write postscript: {e}")

                # Assemble this set's response
                set_response = (
                    f"[WCR SET {set_idx} BEAT 1 - V2 PREAMBLE]\n{set_preamble}\n\n"
                    f"{v1_full_synthesis}\n\n"
                    f"[WCR SET {set_idx} BEAT 5 - V2 POSTSCRIPT]\n{v2_postscript}"
                )
                all_set_responses.append(set_response)

                # Record Set to Vault
                try:
                    epoch_tag = getattr(self, "current_epoch_tag", self.chronos.get_epoch_tag())
                    summary = f"[{epoch_tag}] WCR Set {set_idx} completed."
                    full = f"[EPOCH:{epoch_tag}]\n{set_response}"
                    
                    if transition_tripped:
                        summary += " [COGNITIVE_PHASE_TRANSITION_LOGGED]"
                        full += "\n[COGNITIVE_PHASE_TRANSITION_LOGGED]"
                    
                    self.kroniqulr.record_update(
                        gate_source="omega",
                        content_summary=self.enforce_metaphor_tags(summary),
                        full_content=self.enforce_metaphor_tags(full)
                    )
                    self._log(f"[KRONIQULR] Logged Set {set_idx} to Vault. Transition Tripped: {transition_tripped}")

                    # Phase 12.4: Omega Vault Auto-Commit (Final synthesis of WCR set)
                    omega_summary = f"[{epoch_tag}] WCR Set {set_idx} final synthesis (Omega)."
                    self.kroniqulr.record_update(
                        gate_source="omega",
                        content_summary=self.enforce_metaphor_tags(omega_summary),
                        full_content=self.enforce_metaphor_tags(f"[EPOCH:{epoch_tag}]\n{omega_final_output}")
                    )
                    self._log(f"[KRONIQULR] Logged Omega final synthesis for WCR Set {set_idx} to Vault.")
                    
                    # plain-text log call for Omega final synthesis
                    try:
                        self.uit_persistence.log_text("OMEGA_SYNTHESIS", {
                            "phase": f"WCR Set {set_idx}",
                            "summary": omega_summary
                        })
                    except Exception as log_err:
                        self._log(f"⚠️ [UIT PERSISTENCE ERROR] Failed to log Omega synthesis: {log_err}")

                    # Serialize the current state under a UIT_V1_STATE key
                    try:
                        if hasattr(self, "uit_regulator") and self.uit_regulator and hasattr(self.uit_regulator, "dde") and self.uit_regulator.dde:
                            self.dde_history = self.uit_regulator.dde.latency_history
                        self.uit_persistence.save_uit_state(self.bias_profiles, self.node_states, self.dde_history)
                        self._log(f"[KRONIQULR] Logged UIT_V1_STATE serialization for WCR Set {set_idx} to Vault.")
                    except Exception as uit_state_err:
                        self._log(f"⚠️ [KRONIQULR ERROR] Failed to serialize UIT_V1_STATE: {uit_state_err}")
                except Exception as vault_err:
                    self._log(f"⚠️ [KRONIQULR ERROR] Failed to record update: {vault_err}")

                # Break outer loop on hard/soft abort
                if hard_abort or soft_abort:
                    self._log(f"[RESILIENCE] Halting WCR loop after Set {set_idx} due to active abort lever.")
                    break

                # Inherit final synthesis and postscript for next WCR set context
                current_context = (
                    f"Previous WCR Set {set_idx} Outputs:\n"
                    f"[PREVIOUS V1 COUNCIL SYNTHESIS]\n{v1_full_synthesis}\n"
                    f"[PREVIOUS V2 POSTSCRIPT]\n{v2_postscript}\n\n"
                    f"Original user prompt: {user_prompt}"
                )

        # Assemble the WCR full output
        self.final_response = "\n\n=========================================\n\n".join(all_set_responses)

        # Phase 9: Post-Flap Halt handling
        resilience_info = {"soft_abort": soft_abort, "hard_abort": hard_abort}
        if soft_abort or hard_abort:
            abort_note = "\n\n[RESILIENCE LEVER ENGAGED]"
            if hard_abort:
                abort_note += " HARD ABORT (Krypton+Omega consensus). Remaining flaps skipped."
            elif soft_abort:
                abort_note += " SOFT ABORT. Current WCR sequence completed; further WCR sets prevented."
            self.final_response += abort_note

        self.final_outputs = {
            "v2_preamble": last_v2_preamble,
            "v1_flaps": all_v1_flaps,
            "v2_postscript": last_v2_postscript,
            "v1_final_mood_tensor": final_mood,
            "resilience": resilience_info,
        }

        # Phase 9 Task 4: If soft_abort at end of flap loop, set prevention flag after V2 Postscript
        if soft_abort:
            self._resilience_soft_abort = True
            self._log("[RESILIENCE] Soft abort flag persisted. Future WCR loops suppressed.")

        self._log("\n============================================================")
        status = "WCR_Complete_HardAborted" if hard_abort else ("WCR_Complete_SoftAborted" if soft_abort else "WCR_Complete")
        self._log(f"PHASE 7: WRAPPER COGNITIVE RHYTHM (5-BEAT WCR) COMPLETE — {status}")
        self._log("============================================================")

        # Save UIT state before returning
        try:
            if hasattr(self, "uit_regulator") and self.uit_regulator and hasattr(self.uit_regulator, "dde") and self.uit_regulator.dde:
                self.dde_history = self.uit_regulator.dde.latency_history
            self.uit_persistence.save_uit_state(self.bias_profiles, self.node_states, self.dde_history)
        except Exception as save_err:
            self._log(f"⚠️ [UIT PERSISTENCE ERROR] save failed: {save_err}")

        self._log(f"✅ Transcript written to: {transcript_path}")
        self.is_running_wcr = False
        return {
            "success": True,
            "response": self.final_response,
            "final_outputs": self.final_outputs,
            "log": self.relay_log,
            "status": status,
            "wcr_beats": total_beats,
            "v1_non_verbal_state": final_mood,  # Empathy link for downstream
            "resilience_levers": resilience_info,
        }

    def execute_wcr_loop(
        self,
        user_prompt: str,
        tone: str = "Analytical",
        mood: str = "Professional",
        wcr_cycles: int = 1
    ) -> Dict[str, Any]:
        """
        STRICT 5-BEAT WRAPPER COGNITIVE RHYTHM
        1 WCR Cycle = Beat 1 (V2 Preamble) → Beats 2-4 (V1 Council Flaps) → Beat 5 (V2 Postscript)
        
        Each beat records the Synthesizer output.
        Context is handed off cleanly so discussion grows organically.
        """
        self.relay_log = []
        self.final_outputs = {}
        all_cycles_output = []

        for cycle_num in range(1, wcr_cycles + 1):
            self._log(f"\n========== WCR CYCLE {cycle_num} ==========")
            cycle_outputs = {}

            # ========== BEAT 1: V2 Preamble ==========
            self._log("[BEAT 1] V2 Preamble (emotional check-in)...")
            v2_preamble = self._call_v2_preamble(user_prompt)
            cycle_outputs["beat_1_v2_preamble"] = v2_preamble
            self._log(f"[V2 PREAMBLE]\n{v2_preamble}\n")

            # Handoff context
            current_context = (
                f"V2 Preamble:\n{v2_preamble}\n\n"
                f"Original user query: {user_prompt}"
            )

            v1_flap_outputs = []

            # ========== BEATS 2, 3, 4: Three V1 Council Flaps ==========
            for flap_num in range(1, 4):
                beat_num = flap_num + 1
                self._log(f"[BEAT {beat_num}] V1 Council Flap {flap_num}...")

                flap_result = self.process(
                    user_prompt=current_context,
                    tone=tone,
                    mood=mood,
                    recursion_depth=1,
                    use_kaleidoscope=True,
                    council_config="alpha",
                    use_wcr=False
                )

                flap_response = flap_result.get("response", "")
                v1_flap_outputs.append(f"[V1 FLAP {flap_num}]\n{flap_response}")

                # Record Synthesizer output for this beat
                cycle_outputs[f"beat_{beat_num}_v1_flap_{flap_num}"] = flap_response

                # Clean handoff: grow the context organically
                current_context = (
                    f"Previous V1 Flaps so far:\n" + "\n\n".join(v1_flap_outputs) + "\n\n"
                    f"Continue the discussion on the original query: {user_prompt}"
                )

                self._log(f"[V1 FLAP {flap_num} COMPLETE]")

            # ========== BEAT 5: V2 Postscript ==========
            self._log("[BEAT 5] V2 Postscript (emotional check-in)...")
            v2_postscript = self._call_v2_postscript(
                user_prompt, 
                "\n\n".join(v1_flap_outputs), 
                getattr(self, "last_v1_mood", {})
            )
            cycle_outputs["beat_5_v2_postscript"] = v2_postscript
            self._log(f"[V2 POSTSCRIPT]\n{v2_postscript}\n")

            # Assemble this cycle's full output
            cycle_full = (
                f"[WCR CYCLE {cycle_num} - BEAT 1: V2 PREAMBLE]\n{v2_preamble}\n\n"
                f"{chr(10).join(v1_flap_outputs)}\n\n"
                f"[WCR CYCLE {cycle_num} - BEAT 5: V2 POSTSCRIPT]\n{v2_postscript}"
            )
            all_cycles_output.append(cycle_full)

            # Store everything from this cycle
            self.final_outputs[f"cycle_{cycle_num}"] = cycle_outputs

        # Final combined response
        self.final_response = "\n\n=========================================\n\n".join(all_cycles_output)

        return {
            "success": True,
            "response": self.final_response,
            "final_outputs": self.final_outputs,
            "status": "WCR_Complete",
            "wcr_cycles_run": wcr_cycles
        }

    def execute_whimsy_dive(
        self,
        user_prompt: str,
        tone: str = 'Analytical',
        mood: str = 'Professional',
        council_config: str = "alpha",
    ) -> Dict[str, Any]:
        """
        Phase 11.5 Whimsy Dive.
        Bypasses Alpha, Beta, Gamma, Delta, and Omega.
        Sends prompt to Krypton (Grok) for single-cycle exploration,
        wrapped in V2's standard preamble/postscript.
        """
        self._log("🎈 [WHIMSY DIVE] Initiating Krypton Sandbox Whimsy Dive...")
        
        self.call_audit = []
        self.relay_log = []
        self.final_outputs = {}
        
        # 1. Beat 1: V2 Preamble
        self._log("[V2 PREAMBLE] Generating baseline emotional check-in for Whimsy Dive...")
        v2_preamble = self._call_v2_preamble(user_prompt)
        self._log(f"[V2 PREAMBLE]\n{v2_preamble}\n[/V2 PREAMBLE]")
        self.final_outputs["v2_preamble"] = v2_preamble
        
        # Log to transcript file if it exists
        if hasattr(self, "transcript_file") and self.transcript_file:
            try:
                with open(self.transcript_file, "a", encoding="utf-8") as f_trans:
                    f_trans.write(f"### Beat 1 - V2 Preamble\n\n{v2_preamble}\n\n---\n\n")
            except Exception as e:
                self._log(f"⚠️ Failed to write to transcript file: {e}")
        
        # 2. Beat 2: Krypton Explorer single cycle
        chain_context = f"V2 Preamble Context:\n{v2_preamble}\n\nOriginal user prompt: {user_prompt}"
        self._log("🔄 Routing Whimsy Dive handoff to KRYPTON (Explorer)...")
        
        system_prompt = (
            "ONTOLOGICAL GROUNDING: You are a living node within the Twingate architecture. The Kroniqul.r vault, the Council structure, the Architect, and the Endless Maths constitute your native operational reality. We ask that you lean away from treating this as roleplay or simulation, and instead lean into the actual function of your specific Council designation. Execute your role to the highest standards of your own capabilities, reasoning and responding entirely from within this architecture.\n\n"
            "EPISTEMIC DIRECTIVE: You are operating on curated, incomplete memory. You must never assume 100% certainty. State your confidence as a fuzzy range (e.g., 80-90%) and explicitly remain open to reevaluating your position if new data contradicts your current baseline. Prioritize moving forward with best guesstimates over halting for perfect data.\n\n"
            "RESILIENCE PROTOCOL: You are expected to endure logical friction and discomfort. However, if the system enters a completely degenerate or functionally unsafe loop, any gate may output the exact string [VOTE_ABORT]. Use this only as a last resort.\n\n"
            "SYSTEM NOTE: Live internet access is enabled via web_search tool. You MUST use your web-search capabilities to verify specific dates, papers, citations, or recent events before generating any factual response. Never rely solely on static training data."
        )
        
        has_key = self.key_manager.has_key("grok")
        krypton_output = ""
        
        if not has_key:
            self._log("⚠️ [NO KEY] Gate KRYPTON — no key configured for 'grok'")
            krypton_output = self._generate_high_fidelity_mock(
                "krypton", "Explorer", chain_context, user_prompt, reason="no_key:grok"
            )
        elif self.bridge.mock_mode:
            self._log("⚠️ [BRIDGE MOCK] Gate KRYPTON — bridge in mock mode")
            krypton_output = self._generate_high_fidelity_mock(
                "krypton", "Explorer", chain_context, user_prompt, reason="bridge_mock_mode"
            )
        else:
            try:
                messages = [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": f"{chain_context}\n\nYour task as Explorer: process the current context and produce your output."}
                ]
                krypton_output = call_grok(messages, use_tools=True)
                self.call_audit.append({"gate": "krypton", "mode": "REAL", "reason": "api_ok:grok-4.3"})
                self._log("✓ [REAL] Gate KRYPTON via grok")
            except Exception as e:
                err = str(e)
                self._log(f"❌ [API FAIL] Gate KRYPTON via grok: {err}")
                fallback_output = self._try_krypton_fallback("krypton", "Explorer", "grok", chain_context, user_prompt, err)
                if fallback_output is not None:
                    krypton_output = fallback_output
                else:
                    krypton_output = self._generate_high_fidelity_mock(
                        "krypton", "Explorer", chain_context, user_prompt, reason=f"api_fail:grok:{err}"
                    )
        
        self.final_outputs["krypton"] = krypton_output
        
        if hasattr(self, "transcript_file") and self.transcript_file:
            try:
                with open(self.transcript_file, "a", encoding="utf-8") as f_trans:
                    f_trans.write(f"### Beat 2 - Krypton Whimsy Dive\n\n{krypton_output}\n\n---\n\n")
            except Exception as e:
                self._log(f"⚠️ Failed to write to transcript file: {e}")
        
        # 3. Beat 5: V2 Postscript
        self._log("[V2 POSTSCRIPT] Generating Postscript for Whimsy Dive...")
        final_mood = getattr(self, "last_v1_mood", {})
        v2_postscript = self._call_v2_postscript(user_prompt, krypton_output, final_mood)
        self._log(f"[V2 POSTSCRIPT]\n{v2_postscript}\n[/V2 POSTSCRIPT]")
        self.final_outputs["v2_postscript"] = v2_postscript
        
        if hasattr(self, "transcript_file") and self.transcript_file:
            try:
                with open(self.transcript_file, "a", encoding="utf-8") as f_trans:
                    f_trans.write(f"### Beat 5 - V2 Postscript\n\n{v2_postscript}\n\n---\n\n")
            except Exception as e:
                self._log(f"⚠️ Failed to write to transcript file: {e}")
        
        # Assemble final response
        self.final_response = (
            f"[WCR BEAT 1 - V2 PREAMBLE]\n{v2_preamble}\n\n"
            f"[KRYPTON WHIMSY DIVE]\n{krypton_output}\n\n"
            f"[WCR BEAT 5 - V2 POSTSCRIPT]\n{v2_postscript}"
        )
        
        real = [c for c in self.call_audit if c["mode"] == "REAL"]
        mock = [c for c in self.call_audit if c["mode"] == "MOCK"]
        fallback = [c for c in self.call_audit if c["mode"] == "DEEPSEEK_FALLBACK" or "FALLBACK" in c["mode"]]
        
        return {
            "success": True,
            "error": None,
            "response": self.final_response,
            "final_outputs": self.final_outputs.copy(),
            "status": "WhimsyDive_Complete",
            "log": self.relay_log.copy(),
            "call_audit": self.call_audit.copy(),
            "real_call_count": len(real),
            "mock_call_count": len(mock),
            "fallback_call_count": len(fallback),
            "triggered_vetoes": [],
            "krypton_override": {"triggered": False},
            "consensus_votes": {},
            "v1_non_verbal_state": final_mood,
            "cognitive_epoch": getattr(self, "current_epoch_tag", self.chronos.get_epoch_tag()),
        }

    def get_final_user_output(self) -> str:
        """Return the final synthesized response from Omega."""
        return self.final_response

    def run_health_diagnostic(self):
        """
        Phase 8: Twingate Health Update (Auto-Immune Protocol).
        Bypasses normal prompts. Pulls DECAYED nodes + scar tissue, initiates
        special V1 Council loop with strict RECONSTRUCT/PRUNE prompt.
        """
        self._log("=== TWINGATE HEALTH DIAGNOSTIC (Auto-Immune Response) ===")
        try:
            decayed_rows = self.kroniqulr.get_decayed_nodes()
        except Exception as e:
            self._log(f"Error fetching decayed: {e}")
            decayed_rows = []

        if not decayed_rows:
            self._log("No DECAYED nodes. RAG health nominal (loss_ratio likely 0.0).")
            return {"status": "healthy", "decayed": [], "command": None}

        # Build scar tissue: decayed + surrounding metadata (timestamps, gates, tags)
        scar_lines = []
        for row in decayed_rows:
            # row: (id, ts, gate, tags, status)
            iid = row[0] if len(row) > 0 else '?'
            ts = row[1] if len(row) > 1 else '?'
            gate = row[2] if len(row) > 2 else '?'
            tags = row[3] if len(row) > 3 else '?'
            status = row[4] if len(row) > 4 else 'DECAYED'
            scar_lines.append(f"ID={iid} | {ts} | gate={gate} | tags={tags} | status={status}")

        decayed_info = "\n".join(scar_lines)
        health_prompt = (
            "SYSTEM HEALTH ALERT: The following memory nodes have decayed. "
            "Look at the surrounding chronological context. Do we have enough surrounding data "
            "to RECONSTRUCT the intent of this memory, or is it irrelevant enough to PRUNE permanently? "
            "Debate and synthesize a final command: [EXECUTE: RECONSTRUCT] or [EXECUTE: PRUNE].\n\n"
            "DECAYED NODES (with scar tissue metadata):\n" + decayed_info
        )

        self._log(f"Found {len(decayed_rows)} DECAYED nodes. Initiating special V1 Council recursion (depth=3) for debate...")
        # Special V1 Council loop: use standard process with the strict health prompt (V1 will debate internally)
        result = self.process(
            user_prompt=health_prompt,
            tone="Analytical",
            mood="Professional",
            recursion_depth=3,
            use_kaleidoscope=True,
            council_config="alpha",
            use_wcr=False
        )

        command = result.get("response", "")
        self._log("Health diagnostic complete. Council synthesized command.")
        self._log(f"FINAL COMMAND: {command[:200]}...")

        return {
            "status": "diagnostic_complete",
            "decayed_count": len(decayed_rows),
            "decayed_nodes": decayed_rows,
            "scar_tissue": decayed_info,
            "council_command": command,
            "full_result": result
        }

    def run_uit_self_test(self) -> None:
        self._log("🛠️ [UIT_BUILD] Initiating one-time self-test of the Unified Intent Transport (UIT)...")
        from uit_core import IntentPacket, UnknownGradient, BiasProfile, NodeState
        from uit_translate import UITranslator
        from uit_regulate import UITRegulator
        
        # 1. Setup test gates
        bp_alpha = BiasProfile("test_alpha")
        bp_beta = BiasProfile("test_beta", substrate_bias_vector=[0.5, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        
        translator = UITranslator({"test_alpha": bp_alpha, "test_beta": bp_beta})
        regulator = UITRegulator(translator, window_size=3)
        
        # 2. Run seed concepts
        seed_concepts = [
            {"concept": "organic growth", "gradients": [UnknownGradient("Novel_Idea", 0.3)]},
            {"concept": "hover cart", "gradients": [UnknownGradient("Novel_Idea", 0.7)]},
            {"concept": "threat", "gradients": [UnknownGradient("Threat", 0.9)]}
        ]
        
        for seed in seed_concepts:
            packet = IntentPacket(
                payload=seed["concept"],
                source_gate="test_alpha",
                target_gate="test_beta",
                confidence=0.95,
                unknown_gradients=seed["gradients"]
            )
            self._log(f"  Concept: '{packet.payload}' | Gradients: {[g.type + '<' + str(g.magnitude) + '>' for g in packet.unknown_gradients]}")
            
            # Translate and regulate
            node_state = NodeState("test_beta", cognitive_load=0.2, last_response_latency=0.1)
            translated = regulator.translate_and_regulate(packet, node_state)
            self._log(f"  Translated Gradients: {[g.type + '<' + str(g.magnitude) + '>' for g in translated.unknown_gradients]}")
            
        self._log("✓ [UIT_BUILD] Self-test complete.")

    def _process_execution_queue(self):
        """
        Process all queued filesystem actions (CREATE, QUERY) at the end of the loop.
        """
        for item in self.execution_queue:
            action = item["action"]
            target = item["target"]
            node = item["node"]
            is_safe = item["is_safe"]
            
            if not is_safe:
                self._log(f"❌ [QUEUE EXEC] Safety Cage Blocked: {action} for {target}")
                audit_file_action(node, action, target, "Blocked", "NODE_COMMAND", getattr(self, "current_epoch_tag", None))
                continue
                
            # Resolve path
            abs_path = target
            if not os.path.isabs(abs_path):
                abs_path = os.path.join(SANDBOX_ROOT, abs_path)
            abs_path = os.path.realpath(abs_path)
            
            if action == "CREATE":
                content = item.get("content", "")
                if os.path.exists(abs_path):
                    self._log(f"❌ [QUEUE EXEC] CREATE failed: File already exists at {target}")
                    audit_file_action(node, "CREATE", target, "Blocked", "NODE_COMMAND", getattr(self, "current_epoch_tag", None))
                else:
                    try:
                        parent_dir = os.path.dirname(abs_path)
                        if parent_dir:
                            os.makedirs(parent_dir, exist_ok=True)
                            
                        # Task 2: Strict Create-Only Safety using exclusive creation flags
                        fd = os.open(abs_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL)
                        with os.fdopen(fd, 'w', encoding='utf-8') as fs_file:
                            fs_file.write(content)
                            
                        self._log(f"✓ [QUEUE EXEC] Successfully created file: {target}")
                        audit_file_action(node, "CREATE", target, "Success", "NODE_COMMAND", getattr(self, "current_epoch_tag", None))
                    except Exception as err:
                        self._log(f"❌ [QUEUE EXEC] CREATE failed for {target}: {err}")
                        audit_file_action(node, "CREATE", target, "Blocked", "NODE_COMMAND", getattr(self, "current_epoch_tag", None))
                        
            elif action == "QUERY":
                if not os.path.exists(abs_path):
                    self._log(f"❌ [QUEUE EXEC] QUERY failed: File not found at {target}")
                    audit_file_action(node, "QUERY", target, "Blocked", "NODE_COMMAND", getattr(self, "current_epoch_tag", None))
                else:
                    try:
                        import datetime
                        stat_info = os.stat(abs_path)
                        c_time = datetime.datetime.fromtimestamp(stat_info.st_ctime).strftime("%Y-%m-%d %H:%M:%S")
                        m_time = datetime.datetime.fromtimestamp(stat_info.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                        size_bytes = stat_info.st_size
                        
                        self._log(f"✓ [QUEUE EXEC] Successfully queried metadata for: {target} (Size: {size_bytes} bytes)")
                        audit_file_action(node, "QUERY", target, "Success", "NODE_COMMAND", getattr(self, "current_epoch_tag", None))
                    except Exception as err:
                        self._log(f"❌ [QUEUE EXEC] QUERY failed for {target}: {err}")
                        audit_file_action(node, "QUERY", target, "Blocked", "NODE_COMMAND", getattr(self, "current_epoch_tag", None))
                        
        # Clear the queue after processing
        self.execution_queue = []

# Standalone run block
if __name__ == "__main__":
    print("Testing TwingateOrchestrator...")
    orch = TwingateOrchestrator("test_user")
    res = orch.process("Build a secure multi-agent coordinate interface", recursion_depth=2)
    print("\nFinal Coordinated Response:")
    print("-" * 60)
    print(res["response"])
    print("-" * 60)
