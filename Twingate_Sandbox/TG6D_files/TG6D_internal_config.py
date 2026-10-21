#InternalRegulations_Subsystem
# FILENAME: Twingate_internal_config.py
"""
Internal Regulations Config - The Daemon's Lexicon
Defines the Autocraft tags, soft-brake pulse shifts, and log destinations.
"""
import os

# --- PHYSICAL BASE DIRECTORIES ---
MASTER_LOG_BASE = r"C:\Users\<you>\Desktop\TG6D\Master Log File"
AUTOCRAFT_BAY_BASE = r"C:\Users\<you>\Desktop\TG6D\Autocraft_Bay"

# --- THE SINGLE SOURCE OF TRUTH ROUTING MAP ---
LOG_PATHS = {
    # 1. Automated Transcript & Routing Directories
    "current_archive_transcript": os.path.join(MASTER_LOG_BASE, "current_ct_council_logs.md"),
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
    "council_memory": os.path.join(MASTER_LOG_BASE, "current_ct_council_logs.md"),

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