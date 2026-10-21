# Twingate_V2/core_logic/v2_main_conceptual_entry.py
from Twingate_V2.core_logic.v2_cognitive_engine import V2Core


def start_v2_conceptual_process():
    """
    Entry point for V2. Initializes core components and returns a bundle for UI bridge compatibility.

    Returns dict with 'core' for the bridge: v2_bundle = start...(); v2_instance = v2_bundle["core"]
    Also supports direct use as the core instance in some contexts.
    """
    print("Initializing V2 Conceptual Core...")
    v2_instance = V2Core()
    # Support both legacy direct return and the UI bridge dict format
    return {"core": v2_instance, "status": "ready", "instance": v2_instance}
