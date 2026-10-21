# Twingate_V2/diagnostic/v2_state_snapshot_conceptual.py
"""
The mirror. Where V2 looks at itself and tells V1 what it sees.
"""
import json
from datetime import datetime
from typing import Any, Dict, Optional


def get_conceptual_snapshot_string(
    concepts: Dict[str, Any],
    summary: Optional[str] = None
) -> str:
    """
    Returns a human-readable string snapshot of V2's current conceptual state.
    Used by V1 for diagnostics and grading V2's 'homework'.
    """
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    if summary is None:
        summary = "No summary available (store may not implement get_summary yet)."

    try:
        concepts_str = json.dumps(concepts, indent=2, default=str)
    except Exception:
        concepts_str = str(concepts)

    snapshot = (
        f"=== V2 Conceptual Snapshot @ {ts} ===\n"
        f"Summary: {summary}\n\n"
        f"Stored Concepts ({len(concepts)}):\n{concepts_str}\n"
        f"=====================================\n"
    )
    return snapshot
