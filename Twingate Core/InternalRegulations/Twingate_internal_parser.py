#InternalRegulations_Subsystem
# FILENAME: Twingate_internal_parser.py
"""
Internal Regulations Parser - The Scanner
Reads raw gate outputs and extracts Autocraft tags and their context.
"""
import re
from typing import Dict, List, Any
from .Twingate_internal_config import AUTOCRAFT_WRITE_TAGS, AUTOCRAFT_CONTROL_TAGS

WCR_REMINDER_ROUTE_TARGETS = ["PLANN_R", "ANCH_OR"]

class AutocraftParser:
    """Scans text for [Tag] and extracts the following paragraph."""

    def parse_output(self, gate_name: str, raw_text: str) -> Dict[str, Any]:
        """
        Returns a dictionary containing:
        - write_entries: List of dicts with 'tag' and 'content'
        - control_commands: List of dicts with 'command' and 'value'
        """
        results = {
            "write_entries": [],
            "control_commands": []
        }

        # 1. Parse Write Tags (Extracts up to 1000 chars or until a double newline)
        for tag in AUTOCRAFT_WRITE_TAGS:
            # Matches [Tag_Name] followed by text, stopping at \n\n or end of string
            pattern = r"\[" + tag + r"\]\s*(.*?)(?=\n\n|\Z)"
            matches = re.finditer(pattern, raw_text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                content = match.group(1).strip()
                if content:
                    results["write_entries"].append({
                        "gate": gate_name,
                        "tag": tag,
                        "content": content
                    })

        # 2. Parse Control Tags (Soft Brakes / Halts / Queries)
        # Matches [AUTOCRAFT_PULSE_SHIFT: 4] or [AUTOCRAFT_EMERGENCY_HALT]
        for cmd in AUTOCRAFT_CONTROL_TAGS:
            pattern = r"\[" + cmd + r"(?:\:\s*([a-zA-Z0-9_]+))?\]"
            matches = re.finditer(pattern, raw_text, re.IGNORECASE)
            for match in matches:
                value = match.group(1) if match.group(1) else None
                results["control_commands"].append({
                    "gate": gate_name,
                    "command": cmd,
                    "value": value
                })

        # Actively route control tags instead of just logging them
        active_commands = self.evaluate_active_controls(raw_text)
        results["active_commands"] = active_commands
        # (Ensure active_commands is passed back to the Orchestrator/Daemon in your return payload)

        return results

    def evaluate_active_controls(self, parsed_text: str) -> dict:
        """Scans for active Autocraft tags that require immediate system routing."""
        import re
        active_routes = {
            "vault_query": None,
            "votr_override": False,
            "build_flip": False,
            "build_emergency": False,
            "inspector_approved": False,
            
            # --- NEW DISPATCH.R ROUTES ---
            "dispatch_notes": [],       # Catches [NOTE: target=X | body...]
            "plus3_shift": False,
            "ephemeral_log": False,
            "summon_arbit_r": False
            # Notice: No pulse_shift catcher here. Pulse shifts are handled cleanly 
            # by the main parse_output loop finding AUTOCRAFT_PULSE_SHIFT in the control tags list.
        }

        # Route 1: RAG/Vault Retrieval
        query_match = re.search(r'\[AUTOCRAFT_QUERY_LOG:\s*(.*?)\]', parsed_text)
        if query_match:
            active_routes["vault_query"] = query_match.group(1).strip()

        # Route 2: Emergency Vot.r Escalation & Agenda Reviews
        override_tags = ["[Autocraft_request_override]", "[Autocraft_reconfiguration]", "[AGENDA_INJECTION]", "[VOTR_OVERRIDE]"]
        if any(tag in parsed_text for tag in override_tags):
            active_routes["votr_override"] = True

        # Route 3: Build & Inspec.tor Flow
        # Route 3: Build flip (Omega-approved hand-off to CONTRAC_TOR)
        # Uses regex to ensure it is not just being mentioned inside backticks 
        # or immediately followed by "NOT ISSUED".
        import re
        if re.search(r'(?<!`)\[BUILD_APPROVED\](?!`)', parsed_text):
            # Extra safety: ensure it's not just in a status table row saying "FALSE" or "NOT ISSUED"
            if "NOT ISSUED" not in parsed_text and "FALSE" not in parsed_text.split("[BUILD_APPROVED]")[-1][:20]:
                active_routes["build_flip"] = True
        if "[INSPECTOR_CLEARED]" in parsed_text: active_routes["inspector_approved"] = True
        if "[BUILD_EMERGENCY]" in parsed_text: active_routes["build_emergency"] = True

        # --- ROUTE 4: DISPATCH.R CATCHERS ---
        # Note catcher: Looks for [NOTE: target=PLANN_R | ... ]
        note_matches = re.finditer(r'\[NOTE:\s*target=([A-Za-z0-9_]+)\s*\|\s*(.*?)\]', parsed_text, re.IGNORECASE)
        for match in note_matches:
            active_routes["dispatch_notes"].append({
                "target": match.group(1).strip().upper(),
                "body": match.group(2).strip()
            })

        if "[PLUS3_SHIFT]" in parsed_text: active_routes["plus3_shift"] = True
        if "[EPHEMERAL_LOG]" in parsed_text: active_routes["ephemeral_log"] = True
        if "[SUMMON_ARBIT_R]" in parsed_text: active_routes["summon_arbit_r"] = True

        return active_routes