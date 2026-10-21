#InternalRegulations_Subsystem
# FILENAME: Twingate_autocraft_sandbox.py
"""
Autocraft Bay - Sandbox Core
================================================================================
The walls. Grok (or any model) has NO filesystem access of its own - this module
is the only thing that touches disk on its behalf, and it refuses to touch
anything outside the sandbox.

Exposed model-facing tools (the entire surface area the model can reach):
    - list_sandbox_files()              read-only, executes immediately
    - read_sandbox_file(rel_path)       read-only, executes immediately
    - propose_file_change(rel_path, content)  does NOT write; queues for approval

No delete. No execute. No unrestricted write. Every write-type action becomes a
proposal that waits for the Architect (you) to approve by hand.

Safety model: the model proposes through these functions; it cannot reach the
disk any other way. Path validation forces every operation to resolve to a
location physically inside SANDBOX_DIR. Anything that resolves outside - via
absolute path, .. traversal, or symlink - is rejected before any I/O happens.
================================================================================
"""

import os
import json
import time
from typing import Dict, Any, List

# ── Locations ──
# Sandbox lives next to the Twingate Core tree. Adjust if you want it elsewhere,
# but keep it OUTSIDE Twingate Core so a sandbox write can never land on a live file.
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
# InternalRegulations is inside "Twingate Core"; go up two levels to the project root.
_PROJECT_ROOT = os.path.realpath(os.path.join(_THIS_DIR, "..", ".."))

SANDBOX_DIR = os.path.realpath(os.path.join(_PROJECT_ROOT, "Twingate_Sandbox"))
PENDING_DIR = os.path.realpath(os.path.join(_PROJECT_ROOT, "Autocraft_Bay", "Pending_Approval"))
AUDIT_LOG = os.path.join(_PROJECT_ROOT, "Autocraft_Bay", "sandbox_audit.md")
EMERGENCY_LOG = os.path.join(_PROJECT_ROOT, "Autocraft_Bay", "emergency_invocations.md")


def _ensure_dirs():
    for d in (SANDBOX_DIR, PENDING_DIR, os.path.dirname(AUDIT_LOG)):
        os.makedirs(d, exist_ok=True)


# ── The wall ──
def is_safe_path(rel_path: str) -> bool:
    """
    True only if rel_path resolves to a location physically inside SANDBOX_DIR.

    Rejects absolute paths, parent-directory traversal (..), Windows drive letters,
    and symlinks that would escape the sandbox. Backslashes are normalized to
    forward slashes first so the check behaves identically on Windows and POSIX -
    we do not trust the host OS to interpret separators for us.
    """
    if not rel_path or not isinstance(rel_path, str):
        return False

    # Normalize separators so a Windows-style backslash path is evaluated the same
    # way on any platform. Without this, '..\\x' looks like a plain filename on Linux.
    normalized = rel_path.replace("\\", "/")

    # Reject Windows drive letters (e.g. 'C:/...') explicitly - os.path.isabs misses
    # these on non-Windows hosts.
    if len(normalized) >= 2 and normalized[1] == ":":
        return False

    # Reject absolute paths and any explicit parent traversal.
    if normalized.startswith("/") or os.path.isabs(normalized):
        return False
    if ".." in normalized.split("/"):
        return False

    candidate = os.path.realpath(os.path.join(SANDBOX_DIR, normalized))
    try:
        return os.path.commonpath([candidate, SANDBOX_DIR]) == SANDBOX_DIR
    except ValueError:
        return False


def audit_file_action(action: str, rel_path: str, detail: str = "") -> None:
    """Append a timestamped line to the sandbox audit log. Never raises."""
    try:
        _ensure_dirs()
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{ts}] {action:<18} | {rel_path} {('| ' + detail) if detail else ''}\n"
        with open(AUDIT_LOG, "a", encoding="utf-8") as f:
            f.write(line)
    except Exception as e:
        print(f"[SANDBOX AUDIT FAULT] {e}")


# ── Model-facing tools (the only surface the model can reach) ──
def list_sandbox_files() -> Dict[str, Any]:
    """Read-only. Lists every file inside the sandbox (recursively, relative paths)."""
    _ensure_dirs()
    files: List[str] = []
    for root, _dirs, names in os.walk(SANDBOX_DIR):
        for name in names:
            full = os.path.join(root, name)
            rel = os.path.relpath(full, SANDBOX_DIR)
            files.append(rel.replace("\\", "/"))
    audit_file_action("LIST", ".", f"{len(files)} files")
    return {"ok": True, "files": sorted(files)}


def read_sandbox_file(rel_path: str) -> Dict[str, Any]:
    """Read-only. Returns the contents of a file, only if it's inside the sandbox."""
    if not is_safe_path(rel_path):
        audit_file_action("READ_BLOCKED", rel_path, "path outside sandbox")
        return {"ok": False, "error": f"Path '{rel_path}' is outside the sandbox. Blocked."}
    full = os.path.realpath(os.path.join(SANDBOX_DIR, rel_path))
    if not os.path.exists(full):
        audit_file_action("READ_MISSING", rel_path)
        return {"ok": False, "error": f"File '{rel_path}' not found in sandbox."}
    try:
        with open(full, "r", encoding="utf-8") as f:
            content = f.read()
        audit_file_action("READ", rel_path, f"{len(content)} chars")
        return {"ok": True, "path": rel_path, "content": content}
    except Exception as e:
        audit_file_action("READ_FAULT", rel_path, str(e))
        return {"ok": False, "error": f"Could not read '{rel_path}': {e}"}


def propose_file_change(rel_path: str, new_content: str, rationale: str = "") -> Dict[str, Any]:
    """
    Does NOT write to the sandbox. Creates a proposal in Pending_Approval/ that
    waits for the Architect to approve by hand. This is the write-gate: the model
    can propose, but only a human promotes a proposal into the sandbox.
    """
    if not is_safe_path(rel_path):
        audit_file_action("PROPOSE_BLOCKED", rel_path, "path outside sandbox")
        return {"ok": False, "error": f"Path '{rel_path}' is outside the sandbox. Blocked."}

    _ensure_dirs()
    # Proposal filename encodes the target so you can see what it's for at a glance.
    safe_name = rel_path.replace("/", "__").replace("\\", "__")
    stamp = time.strftime("%Y%m%d_%H%M%S")
    proposal_path = os.path.join(PENDING_DIR, f"{stamp}__{safe_name}.proposal.md")

    body = (
        f"# Proposed change\n\n"
        f"- Target (relative to sandbox): `{rel_path}`\n"
        f"- Proposed at: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"- Rationale: {rationale or '(none given)'}\n\n"
        f"## To approve\n"
        f"Review the content below. To promote it, write this content to "
        f"`Twingate_Sandbox/{rel_path}` yourself (manual gate). Then delete this proposal.\n\n"
        f"## Proposed content\n\n"
        f"```\n{new_content}\n```\n"
    )
    try:
        with open(proposal_path, "w", encoding="utf-8") as f:
            f.write(body)
        audit_file_action("PROPOSE", rel_path, f"queued -> {os.path.basename(proposal_path)}")
        return {
            "ok": True,
            "queued": True,
            "proposal_file": os.path.basename(proposal_path),
            "message": (
                f"Change to '{rel_path}' queued for Architect approval. "
                f"NOT written to the sandbox. Awaiting manual promotion."
            ),
        }
    except Exception as e:
        audit_file_action("PROPOSE_FAULT", rel_path, str(e))
        return {"ok": False, "error": f"Could not queue proposal for '{rel_path}': {e}"}


# ── Emergency routing (soft bypass) ──
def log_emergency_invocation(suit: str, reason: str) -> None:
    """
    Records an emergency-tag use. Emergency does NOT skip the human - it skips the
    staged gates and goes straight to the Architect's desk, flagged. Every use is
    logged here so over-use (the 'drama queen' problem) is visible at a glance.
    """
    try:
        _ensure_dirs()
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        with open(EMERGENCY_LOG, "a", encoding="utf-8") as f:
            f.write(f"[{ts}] SUIT={suit} | REASON: {reason}\n")
    except Exception as e:
        print(f"[EMERGENCY LOG FAULT] {e}")


# ── Tool registry for model function-calling ──
# This is the exact, complete set of tools the model may call. The bridge handler
# (built next session, once we see the live bridge) maps Grok's function-call
# requests to these three functions and nothing else.
SANDBOX_TOOLS = {
    "list_sandbox_files": list_sandbox_files,
    "read_sandbox_file": read_sandbox_file,
    "propose_file_change": propose_file_change,
}


# ── Self-test ──
if __name__ == "__main__":
    print("Sandbox self-test")
    print(f"  SANDBOX_DIR = {SANDBOX_DIR}")
    print(f"  PENDING_DIR = {PENDING_DIR}")
    _ensure_dirs()

    # Wall tests: these must all be rejected.
    bad_paths = ["../secret.py", "/etc/passwd", "..\\..\\Twingate Core\\live.py", "C:\\Windows\\x"]
    print("\n  Wall (these must all be BLOCKED):")
    for p in bad_paths:
        print(f"    {p:<40} -> {'BLOCKED' if not is_safe_path(p) else 'LEAKED (BUG!)'}")

    # Safe paths: these must be allowed.
    good_paths = ["draft.py", "sub/dir/file.md"]
    print("\n  Allowed (these must all be OK):")
    for p in good_paths:
        print(f"    {p:<40} -> {'OK' if is_safe_path(p) else 'WRONGLY BLOCKED (BUG!)'}")

    # Proposal test (writes a proposal, not a sandbox file).
    r = propose_file_change("draft.py", "print('hello from proposal')", "self-test")
    print(f"\n  propose_file_change -> {r.get('message', r)}")
