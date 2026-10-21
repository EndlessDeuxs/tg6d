#Communications_Pathways
# FILENAME: Twingate_pathways_build_loop.py
"""
Communications Layer - Build Tool Loop
================================================================================
Wires the sandbox tools (list / read / propose) into Grok's function-calling so
the build model can explore the sandbox and propose changes - WITHOUT ever
touching disk itself.

Safety properties baked into the loop:
  1. Allowlist-only dispatch. Only the three SANDBOX_TOOLS functions can be
     called. Any other tool name the model emits is refused.
  2. Hard iteration cap. The loop runs at most MAX_TOOL_ITERATIONS rounds, so a
     confused model can't spin forever or run up charges.
  3. Every tool call passes through the sandbox walls (is_safe_path), which were
     tested separately. The model proposes; it never writes.
  4. propose_file_change never writes to the sandbox - it queues for the
     Architect. So even a fully cooperative model cannot self-promote code.

This file is the dispatcher + schemas only. It calls into:
  - Twingate_autocraft_sandbox (the walls + tools)
  - Twingate_pathways_xai_responses (the API call)
================================================================================
"""

import json
from typing import Dict, List, Any, Callable

# The sandbox tools (the walls). Allowlist-only: this dict IS the permission set.
from InternalRegulations.Twingate_autocraft_sandbox import (
    SANDBOX_TOOLS,
    audit_file_action,
)
from .Twingate_pathways_xai_responses import call_grok_responses, BUILD_MODEL_PRIMARY

MAX_TOOL_ITERATIONS = 15


# ── Tool schemas advertised to the model ──
# These describe the ONLY three tools the model may call. Names here must match
# keys in SANDBOX_TOOLS exactly, or dispatch refuses them.
TOOL_SCHEMAS: List[Dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "list_sandbox_files",
            "description": "List every file currently inside the sandbox. Read-only.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_sandbox_file",
            "description": "Read the contents of one file inside the sandbox. Read-only.",
            "parameters": {
                "type": "object",
                "properties": {
                    "rel_path": {
                        "type": "string",
                        "description": "Path relative to the sandbox root, e.g. 'draft.py'.",
                    }
                },
                "required": ["rel_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "propose_file_change",
            "description": (
                "Propose new content for a file. Does NOT write to the sandbox - "
                "it queues the proposal for the Architect to approve by hand. Use "
                "this for every change you want to make."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "rel_path": {
                        "type": "string",
                        "description": "Target path relative to the sandbox root.",
                    },
                    "new_content": {
                        "type": "string",
                        "description": "The full proposed file content.",
                    },
                    "rationale": {
                        "type": "string",
                        "description": "Short reason for the change (for the Architect's review).",
                    },
                },
                "required": ["rel_path", "new_content"],
            },
        },
    },
]


def dispatch_tool(tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """
    Run one tool call - ALLOWLIST ONLY. If the model names a tool that isn't one
    of the three sandbox tools, this refuses it rather than doing anything.
    """
    if tool_name not in SANDBOX_TOOLS:
        audit_file_action("TOOL_REFUSED", tool_name, "not in allowlist")
        return {
            "ok": False,
            "error": (
                f"Tool '{tool_name}' is not permitted. Allowed tools: "
                f"{', '.join(sorted(SANDBOX_TOOLS.keys()))}."
            ),
        }

    fn: Callable = SANDBOX_TOOLS[tool_name]
    try:
        # Each sandbox function validates its own paths internally.
        return fn(**arguments)
    except TypeError as e:
        # Wrong/missing arguments from the model.
        return {"ok": False, "error": f"Bad arguments for '{tool_name}': {e}"}
    except Exception as e:
        return {"ok": False, "error": f"Tool '{tool_name}' failed: {e}"}


def run_build_session(
    api_key: str,
    build_instruction: str,
    system_preamble: str = "",
    model: str = BUILD_MODEL_PRIMARY,
    max_iterations: int = MAX_TOOL_ITERATIONS,
) -> Dict[str, Any]:
    """
    Run a full build session: the model explores the sandbox via tools and queues
    proposals, looping until it stops requesting tools or hits the iteration cap.

    Returns:
        {
          "ok": bool,
          "final_content": str,       # the model's closing text
          "tool_log": [ ... ],        # every tool call + result, in order
          "iterations": int,
          "stopped_reason": str,      # "completed" | "iteration_cap" | "error"
          "error": str | None,
        }

    NOTE: This does not promote anything. Proposals land in Pending_Approval for
    the Architect. Nothing here writes to the live system or executes code.
    """
    tool_log: List[Dict[str, Any]] = []
    transcript = build_instruction
    iterations = 0

    while iterations < max_iterations:
        iterations += 1

        result = call_grok_responses(
            api_key=api_key,
            user_input=transcript,
            model=model,
            system_preamble=system_preamble or None,
            tools=TOOL_SCHEMAS,
        )

        if not result["ok"]:
            return {
                "ok": False,
                "final_content": "",
                "tool_log": tool_log,
                "iterations": iterations,
                "stopped_reason": "error",
                "error": result["error"],
            }

        tool_calls = result.get("tool_calls", [])

        # No tool calls => the model is done; return its content.
        if not tool_calls:
            return {
                "ok": True,
                "final_content": result["content"],
                "tool_log": tool_log,
                "iterations": iterations,
                "stopped_reason": "completed",
                "error": None,
            }

        # Run each requested tool through the allowlist dispatcher, collect results,
        # and feed them back into the transcript for the next round.
        feedback_parts = [f"(Continuing. Results of your tool calls in round {iterations}:)"]
        for call in tool_calls:
            name = call.get("name", "")
            args = call.get("arguments", {}) or {}
            outcome = dispatch_tool(name, args)
            tool_log.append({"iteration": iterations, "tool": name, "args": args, "result": outcome})
            feedback_parts.append(
                f"\n[TOOL RESULT: {name}]\n{json.dumps(outcome, ensure_ascii=False)[:4000]}"
            )

        # Append the original instruction context plus the tool results so the model
        # has continuity. (The Responses API is stateless per call, so we carry context.)
        transcript = (
            f"{build_instruction}\n\n"
            f"--- progress so far ---\n"
            + "\n".join(feedback_parts)
            + "\n\nContinue. Call more tools if needed, or give your final summary "
              "of what you proposed and why."
        )

    # Hit the iteration cap.
    return {
        "ok": True,
        "final_content": "[Build session hit the iteration cap before completing.]",
        "tool_log": tool_log,
        "iterations": iterations,
        "stopped_reason": "iteration_cap",
        "error": None,
    }


# ── Offline plumbing test (no network) ──
if __name__ == "__main__":
    print("Build loop - offline dispatch test (no API calls)")

    # Test the allowlist dispatcher directly against the real sandbox tools.
    print("\n  Allowlist enforcement:")
    bad = dispatch_tool("delete_everything", {"path": "/"})
    print(f"    unknown tool -> ok={bad['ok']} ({bad.get('error', '')[:60]})")

    listing = dispatch_tool("list_sandbox_files", {})
    print(f"    list_sandbox_files -> ok={listing['ok']}")

    blocked = dispatch_tool("read_sandbox_file", {"rel_path": "../../etc/passwd"})
    print(f"    read outside sandbox -> ok={blocked['ok']} ({blocked.get('error', '')[:50]})")

    proposed = dispatch_tool(
        "propose_file_change",
        {"rel_path": "hello.py", "new_content": "print('hi')", "rationale": "test"},
    )
    print(f"    propose_file_change -> ok={proposed['ok']} (queued={proposed.get('queued')})")

    print("\n  Schemas advertised:", [s["function"]["name"] for s in TOOL_SCHEMAS])
