#InternalRegulations_Subsystem
# FILENAME: Twingate_internal_config.py
"""
Internal Regulations Config - The Daemon's Lexicon
Defines the Autocraft tags, soft-brake pulse shifts, and log destinations.
"""
import os

# --- PHYSICAL BASE DIRECTORIES ---
# P1: derived from this file's own location (<repo>/Twingate Core/InternalRegulations/) -> <repo>/Master Log File.
# Absolute on every OS. With the repo at C:\Users\<you>\Desktop\TG6D this equals the old literal exactly.
MASTER_LOG_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Master Log File"
)
AUTOCRAFT_BAY_BASE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "Autocraft_Bay"
)

# --- THE SINGLE SOURCE OF TRUTH ROUTING MAP ---
LOG_PATHS = {
    # 1. Automated Transcript & Routing Directories
    "council": os.path.join(MASTER_LOG_BASE, "Council_Transcripts"),
    "synthesiz_r": os.path.join(MASTER_LOG_BASE, "Synthesizer_Outputs"),
    "monit_or": os.path.join(MASTER_LOG_BASE, "Monitor", "Monit.or_Routing_Log.txt"),
    
    # 2. Autocraft & Build Destinations
    "autocraft_ledger": os.path.join(MASTER_LOG_BASE, "Autocraft", "autocraft_ledger.md"),
    "autocraft_emergency": os.path.join(MASTER_LOG_BASE, "Autocraft", "autocraft_emergency_blackbox.md"),
    "build_history": os.path.join(MASTER_LOG_BASE, "Autocraft", "Proposed_Builds"), # <-- NEW: For Dispatch.r .txt copies
    "pending_builds": os.path.join(AUTOCRAFT_BAY_BASE, "Pending_Approval"),         # <-- For CONTRAC_TOR actual files
    
    # 3. Memory, Handrails, and Temporal Storage
    "suitorials": os.path.join(MASTER_LOG_BASE, "Suitorials", "suitorials_handrails.json"), 
    "remind_r": os.path.join(MASTER_LOG_BASE, "Remind_r", "remind_r_logs.json"),            
    "dreamr_board": os.path.join(MASTER_LOG_BASE, "Remind_r", "dreamr_board.json"),         # <-- Opus needs this
    "core_axioms": os.path.join(MASTER_LOG_BASE, "Remind_r", "core_axioms.json"),           
    # THE council memory file. Written once per turn by log_persistent(), read by
    # read_persistent(). No other LOG_PATHS key may point at this file (DP-01).
    "council_memory": os.path.join(MASTER_LOG_BASE, "current_ct_council_logs.md"),
    # UIT2-02 shadow log (JSON lines). Written ONLY when UIT2_MODE is "shadow"; never sent to models.
    "uit2_shadow": os.path.join(MASTER_LOG_BASE, "UIT2", "uit2_shadow_log.jsonl"),
    # UIT2-03 "on" call ledger (JSON lines, one per budgeted call). Counts survive restarts.
    "uit2_on_ledger": os.path.join(MASTER_LOG_BASE, "UIT2", "uit2_on_ledger.jsonl"),

    # 4. Specialized Logic Outcomes & Ephemera
    "votr": os.path.join(MASTER_LOG_BASE, "Votr", "votr_outcomes.md"),                      
    "plus3": os.path.join(MASTER_LOG_BASE, "Plus3", "plus3_transitions.md"),                
    "ephemeral": os.path.join(MASTER_LOG_BASE, "Ephemeral", "ephemeral_notes.md"),          
    "cloud_pathways": os.path.join(MASTER_LOG_BASE, "Cloud_Storage", "cloud_storage_pathways.md")
}

# The complete toolkit of Autocraft Builder Tags
AUTOCRAFT_WRITE_TAGS = [
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
    "Autocraft_request_override"
]

# The Control Tags (Soft Brakes and Hard Stops)
AUTOCRAFT_CONTROL_TAGS = [
    "AUTOCRAFT_PULSE_SHIFT",     # Expected format: [AUTOCRAFT_PULSE_SHIFT: <0-6>]
    "AUTOCRAFT_EMERGENCY_HALT",  # Immediate WCR kill switch
    "AUTOCRAFT_QUERY_LOG"        # Expected format: [AUTOCRAFT_QUERY_LOG: <log_name>]
]

SEVERITY_LEVELS = {
    0: "[SEV-0: NOMINAL]",
    1: "[SEV-1: ADVISORY]",
    2: "[SEV-2: NOTICE]",
    3: "[SEV-3: ELEVATED]",
    4: "[SEV-4: WARNING]",
    5: "[SEV-5: CRITICAL]",
    6: "[SEV-6: ARBIT_R_REQUIRED]",
}

CIRCUIT_BREAKER_SEV_TAG = "[SEV-5: CRITICAL]"


def get_severity_tag(level: int) -> str:
    return SEVERITY_LEVELS.get(level, SEVERITY_LEVELS[0])


# --- UIT2-02: uit2 switch (read by Bridge.call at call time) ---
# "off"    : Bridge.call is byte-identical to before UIT2-02; uit2 is never imported.
# "shadow" : the outgoing request is unchanged; a uit2 form of request.context is written
#            ONLY to LOG_PATHS["uit2_shadow"]. Models never see it.
# "on"     : (UIT2-03) for UIT2_ON_PAIR only and only within the call budget below: the spec sheet is
#            appended to the system line and request.context is sent uit2-encoded. Everything else
#            behaves as "shadow". Needs the Architect's yes before it is set.
UIT2_MODE = "off"
UIT2_SHADOW_MAX_INPUT_CHARS = 400_000   # longer contexts are logged as not_encodable (bounds shadow cost)
UIT2_SHADOW_LOG_MAX_CHARS = 2_000       # encoded/rendered text kept per log line; longer is clipped (sha256 covers the full text)

# --- UIT2-03: "on" mode. ALL values below are set by the Architect BEFORE a run, never during one. ---
# Exactly one (receiving role, model gate) pair. Placeholders never match, so "on" applies to nothing.
UIT2_ON_PAIR = ("<ROLE_PLACEHOLDER>", "<GATE_PLACEHOLDER>")
# Mechanical stop. "on" is refused (off behaviour, logged) when: the id is empty, the numbers are
# inconsistent (calls > WCR x UIT2_CALLS_PER_WCR), the budget is used up (counted in LOG_PATHS
# ["uit2_on_ledger"] per id, across restarts), the ledger path is not absolute on the running OS,
# or any of these values changes during a run.
UIT2_ON_BUDGET_ID = ""          # e.g. "uit2-03-pilot-1"; a new id = a new approval
UIT2_ON_BUDGET_CALLS = 0        # approved number of "on" calls
UIT2_ON_BUDGET_WCR = 0          # approved WCR for those calls
UIT2_CALLS_PER_WCR = 25         # 1 WCR ~ 25 calls, pending the Architect's confirmation
UIT2_ON_SHEET_SHA256 = "4fd680a1dfc77d2e954a8b3c786972f4a1274ea2be446a8beeb2f740fdaf7886"  # UIT2-01 SPEC_SHEET.txt
