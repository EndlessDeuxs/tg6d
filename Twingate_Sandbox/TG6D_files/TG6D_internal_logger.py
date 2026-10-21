#InternalRegulations_Subsystem
# FILENAME: Twingate_internal_logger.py
"""
Internal Logger - The Autocraft Logger
Writes routed logs to the paths defined in Twingate_internal_config.LOG_PATHS.

Routing intent:
  - _write(path, tag, entry): generic router; writes to whatever path is handed in.
    Used by circuit breakers and any orchestrator-side logging that picks its own
    destination from LOG_PATHS.
  - log_wcr_output(transcript, synth_output, chronos_stamp): splits the WCR cycle
    output into two timestamped files - council/ holds the full transcript,
    synthesiz_r/ holds the final synthesizer output. Both files are named with the
    same Chronos tick stamp so they can be cross-referenced.
  - log_daemon_pulse(severity_tag, message): routine behind-the-scenes pulse log.
    Goes to monit_or so it doesn't mix with council content.
"""

import os
import re
from datetime import datetime
from typing import Optional

from .Twingate_internal_config import LOG_PATHS
from .Twingate_internal_config import MASTER_LOG_BASE
from Behavior.Twingate_behavior_chronos import ChronosEngine


def _sanitize_for_filename(text: str) -> str:
    """Strip characters that Windows/Python file systems don't tolerate well."""
    # Replace anything that isn't alphanumeric, dash, underscore, or dot with underscore.
    return re.sub(r"[^A-Za-z0-9._-]+", "_", text).strip("_")


class AutocraftLogger:
    def __init__(self):   # whatever your current signature is
        # === SAFE DIRECTORY CREATION FOR LOG_PATHS ===
            for key, path in LOG_PATHS.items():
                if path and isinstance(path, str):
                    # If the path has a file extension (like .md), we only create the parent directory
                    if "." in os.path.basename(path):
                        target_dir = os.path.dirname(path)
                    else:
                        target_dir = path

                    if target_dir:
                        os.makedirs(target_dir, exist_ok=True)

    # ------------------------------------------------------------------ #
    # Generic routed writer - used by circuit breakers and any caller    #
    # that picks its own destination from LOG_PATHS.                     #
    # ------------------------------------------------------------------ #
    def _write(self, log_path: str, tag: str, entry: str):
        """
        Append a single tagged entry to the file at log_path.

        Parameters:
            log_path: Full filesystem path. Caller is expected to pass a value
                      from LOG_PATHS (e.g. LOG_PATHS["autocraft_emergency"]).
            tag:      Short label identifying the entry kind (e.g. "CIRCUIT BREAKER").
            entry:    The message body to record.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] [{tag}] {entry}\n"

        parent = os.path.dirname(log_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            # Logging failures must never crash the orchestrator. Surface to stderr
            # and move on; the circuit breaker has already done its job upstream.
            print(f"⚠️ [LOGGER FAULT] Failed to write to {log_path}: {e}")

    # ------------------------------------------------------------------ #
    # Autocraft Ledger - Handles the 11 AUTOCRAFT_WRITE_TAGS             #
    # ------------------------------------------------------------------ #
    def log_parsed_entries(self, entries: list):
        """
        Appends parsed Autocraft write tags to the autocraft ledger.
        entries: List of dicts with 'gate', 'tag', and 'content'
        """
        if not entries:
            return
            
        log_path = LOG_PATHS["autocraft_ledger"]
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        parent = os.path.dirname(log_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
            
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                for entry in entries:
                    gate = entry.get("gate", "UNKNOWN")
                    tag = entry.get("tag", "UNKNOWN_TAG")
                    content = entry.get("content", "")
                    
                    f.write(f"\n[{timestamp}] [{gate.upper()}] [{tag}]\n{content}\n")
                    f.write("-" * 50 + "\n")
        except Exception as e:
            print(f"⚠️ [LOGGER FAULT] Failed to write parsed entries to {log_path}: {e}")

    # ------------------------------------------------------------------ #
    # WCR cycle output - splits into council transcript and Synthesiz.r  #
    # final output. Both files share the same Chronos tick stamp in the  #
    # filename for cross-referencing.                                    #
    # ------------------------------------------------------------------ #
    def log_wcr_output(
        self,
        transcript: str,
        synthesiz_r_output: str,
        chronos_stamp: Optional[str] = None,
    ):
        """
        Write a completed WCR cycle to two separate files:
          - council/<stamp>.md          - full council transcript (for retrieval)
          - synthesiz_r/<stamp>.md      - final synthesizer output (for immediate review)

        Parameters:
            transcript:         The full council discussion text.
            synthesiz_r_output: Synthesiz.r's final synthesized output.
            chronos_stamp:      ChronosEngine.get_stamp() output, e.g.
                                "[2026-06-24 09:32:14 | MT0CT2-T7]".
                                If omitted, falls back to wall-clock-only naming.
        """
        import os
        import re
        from datetime import datetime
        
        wall_clock = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if chronos_stamp:
            # Use the Chronos tick portion as the filename anchor so council and
            # synthesiz_r files for the same cycle share the same base name.
            match = re.search(r"MT\d+CT\d+-T\d+", chronos_stamp)
            stamp_root = match.group(0) if match else _sanitize_for_filename(chronos_stamp)
        else:
            # Fallback: no Chronos stamp provided. Use wall clock.
            stamp_root = datetime.now().strftime("%Y%m%d_%H%M%S")

        # File extensions: .md keeps these readable in any markdown viewer.
        council_filename = f"{stamp_root}.md"
        synth_filename = f"{stamp_root}.md"

        council_path = os.path.join(LOG_PATHS["council"], council_filename)
        synth_path = os.path.join(LOG_PATHS["synthesiz_r"], synth_filename)

        council_body = (
            f"# Council Transcript (Append)\n\n"
            f"- Wall clock: {wall_clock}\n"
            f"- Chronos stamp: {chronos_stamp or '(not provided)'}\n\n"
            f"---\n\n"
            f"{transcript}\n"
        )
        synth_body = (
            f"# Synthesiz.r Output (Append)\n\n"
            f"- Wall clock: {wall_clock}\n"
            f"- Chronos stamp: {chronos_stamp or '(not provided)'}\n"
            f"- Paired council transcript: ../Council_Transcripts/{council_filename}\n\n"
            f"---\n\n"
            f"{synthesiz_r_output}\n"
        )

        try:
            # FIXED: Use the correct path from LOG_PATHS
            archive_path = LOG_PATHS.get("current_archive_transcript")
            
            if not archive_path:
                print("⚠️ [LOGGER] No 'current_archive_transcript' path found in LOG_PATHS")
                return

            # Make sure the directory exists
            archive_dir = os.path.dirname(archive_path)
            if archive_dir:
                os.makedirs(archive_dir, exist_ok=True)

            file_exists = os.path.exists(archive_path)

            with open(archive_path, "a", encoding="utf-8") as f:
                if file_exists:
                    f.write("\n\n" + "="*70 + "\n\n")  # visual separator between WCRs
                f.write(council_body)

            print(f"[LOGGER] Council round appended → {archive_path}")

        except Exception as e:
            print(f"⚠️ [LOGGER FAULT] Failed to write council transcript: {e}")

        try:
            os.makedirs(LOG_PATHS["synthesiz_r"], exist_ok=True)
            file_exists = os.path.exists(synth_path)
            
            # Switch to "a" for append mode
            with open(synth_path, "a", encoding="utf-8") as f:
                if file_exists:
                    f.write("\n\n" + "="*60 + "\n\n") # Visual separator between depths
                f.write(synth_body)
        except Exception as e:
            print(f"⚠️ [LOGGER FAULT] Failed to write synthesizer output {synth_path}: {e}")

    # ------------------------------------------------------------------ #
    # NEW: Lightweight council transcript logger
    # Call this after EVERY CONDENS_OR (intermediate handoff rounds + final)
    # This does NOT touch the Synthesiz.r output path at all.
    # ------------------------------------------------------------------ #
    def log_council_round(
        self,
        transcript: str,
        chronos_stamp: Optional[str] = None,
        round_label: str = "WCR"
    ):
        """
        Append-only write for council transcript after every CONDENS_OR.
        Used for both final rounds and intermediate handoff rounds.
        Does NOT write anything to the Synthesiz.r folder.
        """
        import os
        import re
        from datetime import datetime

        wall_clock = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if chronos_stamp:
            match = re.search(r"MT\d+CT\d+-T\d+", chronos_stamp)
            stamp_root = match.group(0) if match else _sanitize_for_filename(chronos_stamp)
        else:
            stamp_root = datetime.now().strftime("%Y%m%d_%H%M%S")

        council_filename = f"{stamp_root}.md"
        council_path = os.path.join(LOG_PATHS["council"], council_filename)

        council_body = (
            f"\n\n{'='*70}\n"
            f"=== {round_label} | Wall clock: {wall_clock} | Chronos: {chronos_stamp or '(none)'} ===\n"
            f"{'='*70}\n\n"
            f"{transcript}\n"
        )

        try:
            # FIXED: Use the directory of the council file, not the file path itself
            council_dir = os.path.dirname(council_path)
            if council_dir:
                os.makedirs(council_dir, exist_ok=True)

            file_exists = os.path.exists(council_path)

            with open(council_path, "a", encoding="utf-8") as f:
                if file_exists:
                    f.write("\n\n" + "="*60 + "\n\n")  # visual separator between rounds
                f.write(council_body)

            print(f"[LOGGER] Council round appended → {council_path}")

        except Exception as e:
            print(f"⚠️ [LOGGER FAULT] Failed to append council round {council_path}: {e}")

    # ------------------------------------------------------------------ #
    # Persistent Council Memory - ONE file, always appended, never wiped. #
    # The council's full running history. Read at the start of each dive  #
    # so the council stops forgetting prior conclusions.                  #
    # ------------------------------------------------------------------ #
    def log_persistent(self, transcript: str, synth_output: str, chronos_stamp: str = None):
        """
        Append one full dive's transcript + synthesis to the persistent memory file.
        Append mode only — this file grows and is never overwritten or rotated.

        Lives in LOG_PATHS under "council_memory" if defined, else falls back to a
        file in the council directory's parent (MASTER_LOG_BASE level).
        """
        from datetime import datetime
        stamp = chronos_stamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Resolve the persistent file path from config, with a safe fallback.
        path = LOG_PATHS.get("council_memory")
        if not path:
            # Fallback: sit it beside the council directory, one level up.
            path = os.path.join(os.path.dirname(council_dir), "current_ct_council_logs.md")
            council_dir = LOG_PATHS.get("council", ".")

        parent = os.path.dirname(path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        block = (
            f"\n\n{'='*60}\n"
            f"=== DIVE @ {stamp} ===\n"
            f"{'='*60}\n\n"
            f"{transcript}\n\n"
            f"--- SYNTHESIZ.R ---\n{synth_output}\n"
        )
        try:
            with open(path, "a", encoding="utf-8") as f:   # "a" = append, never wipes
                f.write(block)
        except Exception as e:
            print(f"⚠️ [LOGGER FAULT] Failed to write persistent memory to {path}: {e}")

    def read_persistent(self) -> str:
        """Read the entire persistent memory file for injection into the next dive."""
        path = LOG_PATHS.get("council_memory")
        if not path:
            council_dir = LOG_PATHS.get("council", ".")
            path = os.path.join(os.path.dirname(council_dir), "current_ct_council_logs.md")
        if not os.path.exists(path):
            return ""
        try:
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            print(f"⚠️ [LOGGER FAULT] Failed to read persistent memory from {path}: {e}")
            return ""

    # ------------------------------------------------------------------ #
    # Daemon pulse - routine behind-the-scenes status with severity tag. #
    # Goes to monit_or so it doesn't mix with council content.           #
    # ------------------------------------------------------------------ #
    def log_daemon_pulse(self, severity_tag: str, message: str):
        """
        Append a severity-tagged pulse line to the Monit.or routing log.

        Parameters:
            severity_tag: One of the strings from SEVERITY_LEVELS, e.g.
                          "[SEV-4: WARNING]" or "[SEV-5: CRITICAL]".
            message:      Human-readable status description.
        """
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {severity_tag} - {message}\n"

        log_path = LOG_PATHS["monit_or"]
        parent = os.path.dirname(log_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(line)
        except Exception as e:
            print(f"⚠️ [LOGGER FAULT] Failed to write daemon pulse to {log_path}: {e}")
    
    # ------------------------------------------------------------------ #
    # Build History - Drops a .txt copy of proposed builds               #
    # ------------------------------------------------------------------ #
    def log_proposed_build(self, gate_name: str, code_content: str, chronos_stamp: str = None):
        """
        Saves a .txt copy of any proposed build into the build_history folder
        for manual review and historical tracking.
        """
        wall_clock = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        if chronos_stamp:
            match = re.search(r"MT\d+CT\d+-T\d+", chronos_stamp)
            stamp_root = match.group(0) if match else _sanitize_for_filename(chronos_stamp)
        else:
            stamp_root = wall_clock
            
        filename = f"{stamp_root}_{gate_name}_proposal.txt"
        log_path = os.path.join(LOG_PATHS["build_history"], filename)

        try:
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            with open(log_path, "w", encoding="utf-8") as f:
                f.write(code_content)
            print(f"[LOGGER] Proposed build saved → {log_path}")
        except Exception as e:
            print(f"⚠️ [LOGGER FAULT] Failed to save proposed build: {e}")
        
        parent = os.path.dirname(log_path)
        if parent:
            os.makedirs(parent, exist_ok=True)
            
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"PROPOSED BUILD BY: {gate_name.upper()}\n")
                f.write(f"TIMESTAMP: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write(f"CHRONOS STAMP: {chronos_stamp or 'None'}\n\n")
                f.write("=== CODE PAYLOAD ===\n\n")
                f.write(code_content)
        except Exception as e:
            print(f"⚠️ [LOGGER FAULT] Failed to write proposed build to {log_path}: {e}")