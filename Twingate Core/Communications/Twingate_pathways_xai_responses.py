#Communications_Pathways
# FILENAME: Twingate_pathways_xai_responses.py
"""
Communications Layer - xAI Responses API Handler
================================================================================
A dedicated handler for xAI's /v1/responses endpoint, which is a DIFFERENT shape
from the OpenAI-compatible /v1/chat/completions path the other gates use.

Why separate: the Responses API uses `input` + `max_output_tokens` instead of
`messages` + `max_tokens`, and is the endpoint xAI exposes for grok-build-0.1
(the agentic build model) and the Responses-API tool/function-calling flow.

This file handles ONLY the API call shape. It does not route, vote, or manage
sandbox state - those live elsewhere. Keeping it isolated means the build call
can be tested and debugged on its own, the same way every other gate is.

EXTENSIBILITY: XAI_ENDPOINTS is a small registry so additional xAI surfaces
(image, tts, etc.) can be added later WITHOUT touching the call logic. Today it
holds only what the build pipeline needs. Add rows when (and only when) a feature
actually needs them - not preemptively.
================================================================================
"""

import time
import json
import requests
from typing import Dict, List, Any, Optional, Callable

# Reuse the same timeout discipline as the main bridge.
RESPONSES_TIMEOUT = 210
SEV_TAG = "[SEV-4: CRITICAL]"

# xAI base. All xAI surfaces hang off this.
XAI_BASE = "https://api.x.ai/v1"

# Endpoint registry. ONLY the build endpoint is wired today. Image/TTS rows are
# intentionally left out until a feature needs them - adding a row here plus a
# matching small handler is all it takes later, with zero changes to build logic.
XAI_ENDPOINTS = {
    "responses": f"{XAI_BASE}/responses",   # grok-build-0.1 and Responses-API models
    # "images":   f"{XAI_BASE}/images/generations",   # add when image gen is actually needed
    # "tts":      f"{XAI_BASE}/tts",                   # add when TTS is actually needed
}

# Build-capable model registry. Primary plus cascade, all on the Responses API.
# grok-build-0.1 confirmed from the xAI console. The cascade entries are normal
# chat models used as a fallback IF the build endpoint is unavailable - note they
# would need the chat-completions path, so the fallback here is "report clearly,"
# not "silently reroute." We do not invent fallback build models we can't verify.
BUILD_MODEL_PRIMARY = "grok-build-0.1"
BUILD_MAX_OUTPUT_TOKENS = 256000


def call_grok_responses(
    api_key: str,
    user_input: str,
    model: str = BUILD_MODEL_PRIMARY,
    system_preamble: Optional[str] = None,
    max_output_tokens: int = BUILD_MAX_OUTPUT_TOKENS,
    tools: Optional[List[Dict[str, Any]]] = None,
    tool_dispatch: Optional[Callable[[str, Dict[str, Any]], Dict[str, Any]]] = None,
    timeout: int = RESPONSES_TIMEOUT,
) -> Dict[str, Any]:
    """
    Call xAI's /v1/responses endpoint (the build/agentic surface).

    Parameters:
        api_key:           xAI API key.
        user_input:        The instruction/blueprint text for the build model.
        model:             Defaults to grok-build-0.1.
        system_preamble:   Optional instructions prepended to the input. The
                           Responses API takes a single `input` string rather than
                           a messages array, so we fold any system text into it.
        max_output_tokens: Output cap (build model supports very large outputs).
        tools:             Optional function-calling tool schemas (for the sandbox
                           tools). If None, this is a plain generation call.
        tool_dispatch:     Optional callback(tool_name, args) -> result dict. Called
                           when the model requests a tool. THIS is where the sandbox
                           tools (list/read/propose) get wired in next step. Left
                           None for now so the bare call can be tested first.
        timeout:           Request timeout in seconds.

    Returns a dict:
        {ok: bool, content: str, raw: <full json>, error: str|None,
         tool_calls: [...], latency: float}

    On failure, ok=False and error contains the status plus the response body
    (the body is where xAI says exactly what it didn't like - we never throw it away).
    """
    endpoint = XAI_ENDPOINTS["responses"]

    # Fold system preamble into the single input string (Responses API has no
    # separate system field in the basic shape).
    full_input = user_input
    if system_preamble:
        full_input = f"{system_preamble}\n\n---\n\n{user_input}"

    payload: Dict[str, Any] = {
        "model": model,
        "max_output_tokens": max_output_tokens,
        "stream": False,                 # we want the whole response, not a stream
        "input": full_input,
    }
    if tools:
        payload["tools"] = tools

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    start = time.time()
    try:
        resp = requests.post(endpoint, headers=headers, json=payload, timeout=timeout)
        resp.raise_for_status()
        latency = time.time() - start
        data = resp.json()

        content = _extract_responses_text(data)
        tool_calls = _extract_tool_calls(data)

        # If the model asked for tools and we have a dispatcher, this is where the
        # tool-call loop would run. Kept inert until tool_dispatch is provided so
        # the plain call path is testable on its own first.
        if tool_calls and tool_dispatch:
            # Placeholder for the tool loop - implemented in the next step once the
            # bare call is confirmed working. For now we surface the requested calls.
            pass

        return {
            "ok": True,
            "content": content,
            "tool_calls": tool_calls,
            "raw": data,
            "error": None,
            "latency": latency,
        }

    except (requests.Timeout, requests.ConnectionError, requests.HTTPError) as exc:
        latency = time.time() - start
        # Capture the response body - xAI's 4xx bodies say exactly what was wrong.
        detail = ""
        try:
            if 'resp' in locals():
                detail = resp.text
            elif hasattr(exc, "response") and exc.response is not None:
                detail = exc.response.text
        except Exception:
            pass
        full_error = f"{SEV_TAG} xAI Responses failure: {exc}"
        if detail:
            full_error += f" | Response: {detail}"
        return {
            "ok": False,
            "content": "",
            "tool_calls": [],
            "raw": None,
            "error": full_error,
            "latency": latency,
        }
    except Exception as exc:
        latency = time.time() - start
        return {
            "ok": False,
            "content": "",
            "tool_calls": [],
            "raw": None,
            "error": f"{SEV_TAG} xAI Responses unexpected error: {exc}",
            "latency": latency,
        }


def _extract_responses_text(data: Dict[str, Any]) -> str:
    """
    Pull the text out of a Responses-API result. The Responses API can return
    output in a few shapes depending on version; we try the known ones in order
    and fall back to a best-effort string rather than crashing.
    """
    if not isinstance(data, dict):
        return ""

    # Shape 1: top-level "output_text" convenience field (some versions provide it).
    if isinstance(data.get("output_text"), str):
        return data["output_text"]

    # Shape 2: "output" list of items, each with "content" blocks holding "text".
    output = data.get("output")
    if isinstance(output, list):
        chunks: List[str] = []
        for item in output:
            if not isinstance(item, dict):
                continue
            content = item.get("content")
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and isinstance(block.get("text"), str):
                        chunks.append(block["text"])
            elif isinstance(content, str):
                chunks.append(content)
        if chunks:
            return "\n".join(chunks)

    # Shape 3: OpenAI-style choices fallback (in case the account routes that way).
    choices = data.get("choices")
    if isinstance(choices, list) and choices:
        msg = choices[0].get("message", {})
        if isinstance(msg.get("content"), str):
            return msg["content"]

    return ""


def _extract_tool_calls(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Pull any tool/function-call requests out of a Responses-API result. Returns a
    list of {name, arguments} dicts. Empty list if the model didn't request tools.
    Used by the sandbox tool loop (next step).
    """
    calls: List[Dict[str, Any]] = []
    if not isinstance(data, dict):
        return calls

    output = data.get("output")
    if isinstance(output, list):
        for item in output:
            if not isinstance(item, dict):
                continue
            # Responses API marks tool requests by type; tolerate naming variants.
            itype = item.get("type", "")
            if "tool" in str(itype).lower() or "function" in str(itype).lower():
                name = item.get("name") or item.get("tool_name") or ""
                raw_args = item.get("arguments") or item.get("input") or {}
                if isinstance(raw_args, str):
                    try:
                        raw_args = json.loads(raw_args)
                    except Exception:
                        raw_args = {"_raw": raw_args}
                calls.append({"name": name, "arguments": raw_args})

    return calls


# ── Self-test (no network) ──
if __name__ == "__main__":
    print("xAI Responses handler - offline structure test")
    print(f"  Endpoint: {XAI_ENDPOINTS['responses']}")
    print(f"  Primary build model: {BUILD_MODEL_PRIMARY}")

    # Test the text extractor against the three shapes without any network call.
    samples = [
        {"output_text": "hello via output_text"},
        {"output": [{"content": [{"text": "hello via output blocks"}]}]},
        {"choices": [{"message": {"content": "hello via choices"}}]},
    ]
    print("\n  Text extraction:")
    for i, s in enumerate(samples, 1):
        print(f"    shape {i}: {_extract_responses_text(s)!r}")

    tool_sample = {"output": [{"type": "tool_call", "name": "read_sandbox_file",
                               "arguments": '{"rel_path": "draft.py"}'}]}
    print(f"\n  Tool-call extraction: {_extract_tool_calls(tool_sample)}")
