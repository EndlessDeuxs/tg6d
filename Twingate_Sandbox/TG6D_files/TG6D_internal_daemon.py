#InternalRegulations_Subsystem
# FILENAME: Twingate_internal_daemon.py
"""
The H.I.G.H. Daemon (Heuristically Integrated Governing Heuristic)
Watches the data stream, triggers brakes, and compiles the Pre-Flight Beat 1 Inject.
"""

import time
from typing import Dict, Any, List
from .Twingate_internal_parser import AutocraftParser
from .Twingate_internal_logger import AutocraftLogger

class HIGHDaemon:
    def __init__(self, regulator_bus=None, dreamr_board=None):
        self.parser = AutocraftParser()
        self.logger = AutocraftLogger()
        self.bus = regulator_bus  
        self.dreamr_board = dreamr_board  # Injected from the Vault subsystem

    def build_preflight_context(self, analytics_output: str, current_mectick: int = 0, current_collectick: int = 0, current_tick: int = 0) -> str:
        """Assembles the Pre-Flight Payload combining Analytics parsing and Dream.r state."""
        payload = "=== H.I.G.H. DAEMON PRE-FLIGHT ASSEMBLY ===\n"
        payload += f"[ANALYTICS CONTEXT PARSE]:\n{analytics_output}\n\n"

        if self.dreamr_board:
            payload += self.dreamr_board.generate_preflight_inject(current_mectick, current_collectick, current_tick)
        else:
            payload += "[DREAM.R BOARD UNAVAILABLE - RUNNING WITHOUT HORIZON MATRIX]\n"

        # Pull decayed goals for council review
        decayed_goals = []
        if hasattr(self, 'dreamr_board') and self.dreamr_board:
            for category, goals in self.dreamr_board.goals.items():
                for goal in goals:
                    if goal.get("status") == "NEEDS_REVIEW":
                        decayed_goals.append(goal.get("content", "Unknown Goal"))
        
        # Inject into the pre-flight payload if necessary
        if decayed_goals:
            agenda_items = "\n".join([f"- {g}" for g in decayed_goals])
            payload += f"\n\n[AGENDA_INJECTION]\nThe following goals have exceeded their temporal decay limits and require immediate council review to DROP or REPLACE:\n{agenda_items}\n"

        return payload

    def inspect_gate_output(self, gate_name: str, raw_text: str, dispatchr_instance=None) -> Dict[str, Any]:
        """Runs immediately after any gate generates text to log tags, trigger brakes, and dispatch payloads."""
        parsed_data = self.parser.parse_output(gate_name, raw_text)
        daemon_directives = []
        emergency_halt = False

        # 1. IMMEDIATE TRIAGE: Does the driver need to slam the brakes right now?
        for cmd in parsed_data["control_commands"]:
            command_type = cmd["command"]
            val = cmd["value"]
            
            if command_type == "AUTOCRAFT_EMERGENCY_HALT":
                daemon_directives.append({"action": "HALT", "source": gate_name})
                print(f"🚨 [H.I.G.H. DAEMON] EMERGENCY HALT TRIGGERED BY {gate_name.upper()}!")
                emergency_halt = True
            
            elif command_type == "AUTOCRAFT_PULSE_SHIFT":
                pulse_level = int(val) if val and val.isdigit() else 4
                daemon_directives.append({"action": "SHIFT_PULSE", "level": pulse_level, "source": gate_name})
                print(f"⚙️ [H.I.G.H. DAEMON] Pulse shift to Level {pulse_level} requested by {gate_name.upper()}.")

            elif command_type == "AUTOCRAFT_QUERY_LOG":
                daemon_directives.append({"action": "INJECT_LOG", "log_target": val, "source": gate_name})

        # 2. THE DISPATCH.R "BUS STOP" LOGIC
        tags_found_count = len(parsed_data["write_entries"]) + len(parsed_data["control_commands"])
        dispatch_success = True

        if tags_found_count > 0 and not emergency_halt and dispatchr_instance:
            print(f"🚌 [BUSELZEBUB] Cargo detected from {gate_name.upper()}. Bus pulling over for Dispatch.r...")
            
            # Hand the clipboard to Dispatch.r (Assuming it has a start & check method)
            job_id = dispatchr_instance.start_processing(gate_name, parsed_data, raw_text)
            
            attempts = 0
            while attempts < 3:
                if dispatchr_instance.is_task_complete(job_id):
                    print("✅ [BUSELZEBUB] Dispatch.r confirms cargo loaded. Engine idling down, ready to resume.")
                    break
                
                attempts += 1
                print(f"⏱️ [BUSELZEBUB] Dispatch.r working... (Check {attempts}/3). Idling for 30 seconds.")
                time.sleep(30)
            else:
                # This 'else' triggers ONLY if the while loop hits 3 attempts without breaking
                print("🛑 [BUSELZEBUB] EMERGENCY BRAKE! Dispatch.r unresponsive after 90 seconds. Halting bus.")
                daemon_directives.append({"action": "HALT", "source": "DISPATCH_R_TIMEOUT"})
                dispatch_success = False
                
        # Legacy fallback if Dispatch.r isn't plugged in yet
        elif parsed_data["write_entries"] and not dispatchr_instance:
            self.logger.log_parsed_entries(parsed_data["write_entries"])

        return {
            "status": "inspected" if dispatch_success else "dispatch_timeout", 
            "tags_found": tags_found_count,
            "directives": daemon_directives
        }

    def evaluate_decay_protocols(self, current_tick: int, active_goals: list) -> list:
        """Evaluates active goals against the Chronos Tick to flag decayed items."""
        flagged_goals = []
        for goal in active_goals:
            if current_tick >= goal.get("decay_tick", float('inf')):
                flagged_goals.append(goal.get("id", "UNKNOWN_GOAL"))
        return flagged_goals

    def scan_wcr_handoff(self, gate_output: str, current_mood: str, pulse_level: str = "NOMINAL") -> dict:
        """The Buselzebub mid-cycle interceptor. Evaluates safety before passing the WCR envelope."""
        # Check 1: Aether Mood Drift
        if "CRITICAL_DRIFT" in current_mood or "VOID_STATE" in current_mood:
            return {"safe_to_proceed": False, "reason": "Aether mood drifted into critical instability."}
        
        # Check 2: Pulse Level Traffic
        if pulse_level == "OVERLOAD":
            return {"safe_to_proceed": False, "reason": "Pulse traffic limits exceeded."}
        
        # Check 3: Active Emergency Tags in Output
        if "[AUTOCRAFT_EMERGENCY_HALT]" in gate_output:
            return {"safe_to_proceed": False, "reason": "Emergency halt tag detected in WCR output."}
        
        return {"safe_to_proceed": True, "reason": "Nominal"}