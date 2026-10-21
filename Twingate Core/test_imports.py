import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "Twingate Core"))

try:
    from InternalRegulations.Twingate_autocraft_sandbox import SANDBOX_TOOLS, is_safe_path
    print("✓ sandbox imports")
except Exception as e:
    print(f"✗ sandbox: {e}")

try:
    from Communications.Twingate_pathways_xai_responses import call_grok_responses
    print("✓ xai responses imports")
except Exception as e:
    print(f"✗ xai responses: {e}")

try:
    from Communications.Twingate_pathways_build_loop import run_build_session, TOOL_SCHEMAS
    print("✓ build loop imports")
except Exception as e:
    print(f"✗ build loop: {e}")

try:
    from Behavior.Twingate_behavior_inspector import build_connection_manifest, render_manifest_for_llm
    print("✓ inspector imports")
except Exception as e:
    print(f"✗ inspector: {e}")