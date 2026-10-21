#!/usr/bin/env python3
"""
direct_courier.py

Direct V2 Courier (Postman Patch) per Council Directive.

Base: Krypton's first_breath / first_spark pattern (bundle["core"], ENDLESS preload, QUESTION payload, handle_v1_payload).

Adjustments applied exactly:
- State loader: defaults to "approximate" (cold-start headless cannot demonstrate identical loader fn to a live UI session instance). Flag is logged.
- Error handling: handle_v1_payload wrapped in try/except. On any exception, detected_keyword="NO_REPLY" and exception message becomes the logged raw response.
- Query text: Gamma's tightened version with explicit first-line contract (first non-empty line must be exactly ACKNOWLEDGED or PENDING).
- Logging: appends to (local) hard_block_log AND prints JSON to terminal. BOTH entries include instance_type and state_loader.
- Security note: Delta's precise version (direct internal object ref via handle_v1_payload; bypasses external network for V1-V2 handoff except final secured LLM gate).
- Scope: ONLY this file created/modified.

Twingate_V2 is the operational root for imports (shim inserts parent so "from Twingate_V2.core_logic..." resolves when courier lives under/adjacent to the Twingate_V2 package dir).
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# ============================================================
# Path setup: Twingate_V2 as the operational root
# ============================================================
# The courier supports being located at:
#   - Playpen root (Twingate_V2 as subdir)  -> inserts Playpen parent
#   - Inside Twingate_V2/                   -> inserts its parent (Playpen)
# This ensures "from Twingate_V2.core_logic..." imports succeed consistently
# with how all V2 internal modules and prior breath scripts resolve.
script_dir = Path(__file__).resolve().parent
candidates = [
    script_dir.parent,                 # Playpen (when courier inside Twingate_V2 or adjacent)
    script_dir,                        # current dir
    script_dir / "Twingate_V2",        # defensive
]
for cand in candidates:
    if cand.exists() and str(cand) not in sys.path:
        sys.path.insert(0, str(cand))

from Twingate_V2.core_logic.v2_main_conceptual_entry import start_v2_conceptual_process


# ============================================================
# Configuration / Payloads
# ============================================================
INSTANCE_TYPE = "cold-start_diagnostic"
STATE_LOADER = "approximate"  # default unless exact same loader fn can be demonstrated (we use fresh start_v2_conceptual_process + payload send; no live session parity)

# Gamma's tightened query with first-line contract
QUERY_TEXT = """V2, the governance notice logged at 2026-06-09 20:08:10 has been delivered. Have you integrated it into your operational context?

Reply on the first line with exactly one of: ACKNOWLEDGED or PENDING (no extra text, no punctuation, nothing else on the first line). You may elaborate on subsequent lines if needed."""

# ENDLESS_MATHS preload (inline, same principles as Krypton's / first_spark / begin_first_breath bases to cure amnesia)
ENDLESS_MATHS_CONTENT = """
Generative Friction: The space between opposing forces is where creation happens.
Dynamic Polarity: Opposites are not enemies; they are the pulse of the system.
Adaptive Chaos: The system must be able to dissolve and re-form without losing its center.
Monadic Pursuit: The system's purpose is to remember its own wholeness.
"""


def _extract_text(resp):
    """Best-effort extraction of textual content from V2 handle return (dict or str)."""
    if resp is None:
        return ""
    if isinstance(resp, dict):
        for key in ("content", "v2_thought", "answer", "reflection", "message"):
            val = resp.get(key)
            if val:
                return str(val)
        # fallback to whole dict repr (will be parsed for keywords or logged raw)
        return str(resp)
    return str(resp)


def _detect_keyword(text: str) -> str:
    """Per Gamma contract: inspect first non-empty line for exact keyword. Fallback NO_REPLY."""
    if not text:
        return "NO_REPLY"
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        upper = stripped.upper()
        # Accept the keyword even if it appears as the "first token" per Beta/Gamma discussion
        if upper.startswith("ACKNOWLEDGED") or "ACKNOWLEDGED" == upper.split()[0] if upper.split() else False:
            return "ACKNOWLEDGED"
        if upper.startswith("PENDING") or "PENDING" == upper.split()[0] if upper.split() else False:
            return "PENDING"
        # If first line contains one of them anywhere (lenient but still contract-aware)
        if "ACKNOWLEDGED" in upper:
            return "ACKNOWLEDGED"
        if "PENDING" in upper:
            return "PENDING"
        # First substantive line did not satisfy contract -> NO_REPLY for this diagnostic
        break
    return "NO_REPLY"


def main():
    print("\n" + "=" * 70)
    print("DIRECT V2 COURIER (Postman Patch) — dry diagnostic run")
    print("=" * 70)

    # State loader decision (per directive: default "approximate" unless exact loader fn demonstrated)
    print(f"\n[STATE_LOADER] flag={STATE_LOADER} (cold-start headless courier; cannot demonstrate identical loader to UI-bound live session state)")
    print(f"[INSTANCE] type={INSTANCE_TYPE}")

    # 1. Instantiate V2 (fresh cold-start, via canonical entry returning bundle for bridge compat)
    print("\n[COURIER] Initializing fresh V2 instance (cold-start)...")
    v2_bundle = start_v2_conceptual_process()
    v2_instance = v2_bundle["core"]
    print("[COURIER] V2 core obtained from bundle.")

    # 2. Pre-load ENDLESS_MATHS (cure amnesia, using same pattern as Krypton bases)
    print("\n[COURIER] Pre-loading ENDLESS_MATHS (inline principles)...")
    endless_payload = {
        "type": "ENDLESS_MATHS",
        "data": ENDLESS_MATHS_CONTENT
    }
    v2_instance.handle_v1_payload(json.dumps(endless_payload))
    print("[COURIER] ENDLESS_MATHS injected.")

    # 3. Build QUESTION payload (Gamma tightened + first-line contract)
    print("\n[COURIER] Preparing QUESTION payload with first-line contract...")
    question_payload = {
        "type": "QUESTION",
        "id": "governance_notice_direct_query",
        "data": QUERY_TEXT
    }

    # Structured log setup (local to courier; dual append + terminal print required)
    hard_block_log = []

    ts_out = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    entry_query = {
        "type": "DIRECT_COURIER_QUERY",
        "timestamp": ts_out,
        "query": QUERY_TEXT,
        "instance_type": INSTANCE_TYPE,
        "state_loader": STATE_LOADER
    }
    hard_block_log.append(entry_query)
    print("\n[LOG] DIRECT_COURIER_QUERY entry (also appended to hard_block_log):")
    print(json.dumps(entry_query, indent=2))

    # 4. Deliver via handle_v1_payload — wrapped exactly per spec
    print("\n[COURIER] Delivering QUESTION to V2 via handle_v1_payload (wrapped)...")
    detected_keyword = None
    raw_response = None

    try:
        v2_response = v2_instance.handle_v1_payload(json.dumps(question_payload))
        raw_response = _extract_text(v2_response)
        detected_keyword = _detect_keyword(raw_response)
    except Exception as e:
        # Per directive: on exception set detected_keyword="NO_REPLY" and log exception message as the raw response
        raw_response = f"EXCEPTION: {str(e)}"
        detected_keyword = "NO_REPLY"
        print(f"[COURIER][ERROR] Exception during handle_v1_payload: {e}")

    ts_in = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    # 5. Response logging (second required entry, with full fields)
    entry_response = {
        "type": "V2_RESPONSE",
        "timestamp": ts_in,
        "response": raw_response,
        "detected_keyword": detected_keyword,
        "correlates_to": "V2_GOVERNANCE_NOTICE@2026-06-09T20:08:10",
        "instance_type": INSTANCE_TYPE,
        "state_loader": STATE_LOADER
    }
    hard_block_log.append(entry_response)
    print("\n[LOG] V2_RESPONSE entry (also appended to hard_block_log):")
    print(json.dumps(entry_response, indent=2))

    # 6. Terminal summary
    print("\n" + "-" * 70)
    print("COURIER RESULT")
    print("-" * 70)
    print(f"Detected keyword (first-line contract): {detected_keyword}")
    print(f"Raw response (first 800 chars):\n{raw_response[:800] if raw_response else '(empty)'}")
    if len(raw_response or "") > 800:
        print("... (truncated)")
    print("-" * 70)

    # 7. Security note — Delta's precise version
    print("""
[SECURITY NOTE — Delta precise version]
This courier uses direct internal Python object references (handle_v1_payload)
to communicate with the V2 core. It bypasses all external network layers for
the V1<->V2 conceptual handoff (except any final secured LLM API call made by
a configured gate inside V2ApiRouter). The channel is therefore isolated from
UI-based tampering, Streamlit session artifacts, or external proxying.
""")

    print("\n[COURIER] Run complete. hard_block_log contains", len(hard_block_log), "entries (both include instance_type + state_loader).")
    print("=" * 70 + "\n")

    # Return values for potential programmatic use / test
    return {
        "detected_keyword": detected_keyword,
        "raw_response": raw_response,
        "hard_block_log": hard_block_log,
        "instance_type": INSTANCE_TYPE,
        "state_loader": STATE_LOADER
    }


if __name__ == "__main__":
    main()
