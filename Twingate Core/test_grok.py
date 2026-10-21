from Communications.Twingate_pathways_xai_responses import call_grok_responses
import os

key = os.environ.get("XAI_API_KEY", "")
if not key:
    print("No XAI_API_KEY found in environment. Set it first.")
else:
    result = call_grok_responses(key, "Write a hello world function in Python.")
    print("OK:", result["ok"])
    print("CONTENT:", result["content"][:500])
    print("ERROR:", result["error"])