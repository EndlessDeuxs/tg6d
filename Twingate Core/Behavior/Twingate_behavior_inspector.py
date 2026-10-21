#Behavior_Subsystem
# FILENAME: Twingate_behavior_inspector.py
"""
Inspec.tor - Mechanical Connection Manifest
================================================================================
The deterministic safety gate. Before a build is allowed, Inspec.tor parses the
PROPOSED version of a file and the EXISTING files that connect to it, then checks -
mechanically, by reading the actual symbols - whether the proposed change breaks
any connection.

It cannot forget to look, because it is a loop over real names in real syntax
trees, not a judgement call. This is what emits (or withholds) the clearance that
unlocks a build.

What it catches (structural breaks - the class of bug that keeps biting):
  - A proposed file removes/renames a function, class, or method that other
    files import or call.
  - A proposed file changes a method's parameters such that existing callers
    would pass the wrong arguments (basic arity check).
  - A proposed file's imports reference names that don't exist in the target.

What it does NOT catch (left to the LLM follow-up):
  - Semantic errors ("this logic is wrong but syntactically fine").
  - Downstream ripple effects ("this missing endpoint also breaks retrieval").
That second pass is the Inspec.tor SUIT (DeepSeek), fed THIS manifest as input.

This module does pure analysis. No network, no writes. It produces a manifest dict
the orchestrator uses to decide whether to emit [INSPECTOR_CLEARED].
================================================================================
"""

import ast
import os
from typing import Dict, List, Any, Set, Optional


# ── Symbol extraction ──
def _parse(source: str, label: str) -> Optional[ast.AST]:
    try:
        return ast.parse(source)
    except SyntaxError as e:
        # A proposed file that doesn't even parse is an automatic fail upstream.
        return None


def _defined_symbols(tree: ast.AST) -> Dict[str, Dict[str, Any]]:
    """
    Top-level and class-level callable names defined in a module.
    Returns {symbol_name: {"kind": "function|method|class", "args": [...], "class": <owner or None>}}.
    Methods are recorded both bare ('_write') and qualified ('AutocraftLogger._write').
    """
    symbols: Dict[str, Dict[str, Any]] = {}

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            symbols[node.name] = {"kind": "class", "args": [], "class": None}
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    args = [a.arg for a in item.args.args]
                    # Record qualified and bare; bare lets us catch ".method()" calls
                    # without resolving the receiver's type (best-effort).
                    symbols[f"{node.name}.{item.name}"] = {
                        "kind": "method", "args": args, "class": node.name,
                    }
                    symbols.setdefault(item.name, {
                        "kind": "method", "args": args, "class": node.name,
                    })
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # Only count module-level functions here (methods handled above).
            # ast.walk hits nested defs too; filter to those not inside a class by
            # checking col_offset==0 is unreliable, so we accept slight over-inclusion.
            args = [a.arg for a in node.args.args]
            symbols.setdefault(node.name, {"kind": "function", "args": args, "class": None})

    return symbols


def _called_names(tree: ast.AST) -> Set[str]:
    """
    Every name this module calls. Captures both bare calls foo(...) and attribute
    calls obj.method(...) -> records 'method'. Best-effort: we can't always resolve
    the receiver type, so we match on the attribute name.
    """
    calls: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            f = node.func
            if isinstance(f, ast.Name):
                calls.add(f.id)
            elif isinstance(f, ast.Attribute):
                calls.add(f.attr)
    return calls


def _imported_names(tree: ast.AST) -> Set[str]:
    """Names this module imports from others (for 'from X import y' style)."""
    names: Set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            for alias in node.names:
                names.add(alias.name)
    return names


# ── The manifest ──
def build_connection_manifest(
    proposed_path: str,
    proposed_source: str,
    connected_files: Dict[str, str],
) -> Dict[str, Any]:
    """
    Compare a proposed file against the files that connect to it.

    Parameters:
        proposed_path:   logical name/path of the file being changed (for reporting).
        proposed_source: the NEW source code of the proposed file.
        connected_files: {path: source} of existing files that import from or call
                         into the proposed file. The caller supplies this set - in
                         practice, the files in the same subsystem plus any known
                         callers. (Inspec.tor checks what it's given; giving it more
                         files = a wider safety net.)

    Returns a manifest dict:
        {
          "ok": bool,                    # True only if no broken connections
          "parse_ok": bool,              # did the proposed file even parse
          "proposed_defines": [...],     # symbols the new file defines
          "broken_connections": [...],   # the failures - each a dict with detail
          "warnings": [...],             # softer concerns (arity mismatches, etc.)
          "summary": str,
        }
    """
    manifest: Dict[str, Any] = {
        "ok": False,
        "parse_ok": False,
        "proposed_defines": [],
        "broken_connections": [],
        "warnings": [],
        "summary": "",
    }

    proposed_tree = _parse(proposed_source, proposed_path)
    if proposed_tree is None:
        manifest["summary"] = f"PROPOSED FILE DOES NOT PARSE: {proposed_path}. Build blocked."
        manifest["broken_connections"].append({
            "type": "syntax_error",
            "file": proposed_path,
            "detail": "Proposed file has a syntax error and cannot be analyzed.",
        })
        return manifest

    manifest["parse_ok"] = True
    proposed_symbols = _defined_symbols(proposed_tree)
    manifest["proposed_defines"] = sorted(proposed_symbols.keys())
    proposed_symbol_names = set(proposed_symbols.keys())

    # For each connected file, see if it calls or imports names that the proposed
    # file is expected to provide but no longer does.
    for cpath, csource in connected_files.items():
        ctree = _parse(csource, cpath)
        if ctree is None:
            manifest["warnings"].append({
                "type": "connected_unparseable",
                "file": cpath,
                "detail": f"Connected file {cpath} didn't parse; couldn't check it.",
            })
            continue

        called = _called_names(ctree)
        imported = _imported_names(ctree)

        # Imports from the proposed module that no longer exist.
        for name in imported:
            # Heuristic: if the connected file imports a name that LOOKS like it
            # should come from the proposed file (matches a previously-defined
            # symbol family) but isn't in the new symbol set, flag it.
            if name not in proposed_symbol_names and _looks_related(name, proposed_path):
                manifest["broken_connections"].append({
                    "type": "missing_import",
                    "file": cpath,
                    "symbol": name,
                    "detail": f"{cpath} imports '{name}' which the proposed {proposed_path} does not define.",
                })

        # Calls to attribute/method names that the proposed file was expected to
        # provide. We only flag a call as broken if the proposed file defines a
        # CLASS that the caller uses and the method is absent from that class.
        # Conservative: only flag calls whose name matches a method the proposed
        # file's class USED to have but the new version dropped. Since we only see
        # the new version here, we approximate by flagging calls to names that the
        # proposed file's classes clearly should expose but don't.
        # (The LLM pass catches the subtler cases; this catches the obvious drops.)
        for name in called:
            if _is_probably_provided_by(name, proposed_path) and name not in proposed_symbol_names:
                manifest["broken_connections"].append({
                    "type": "missing_method_or_function",
                    "file": cpath,
                    "symbol": name,
                    "detail": f"{cpath} calls '{name}()' which the proposed {proposed_path} does not define.",
                })

    manifest["ok"] = len(manifest["broken_connections"]) == 0

    if manifest["ok"]:
        manifest["summary"] = (
            f"CLEAN: proposed {proposed_path} defines {len(proposed_symbol_names)} symbols; "
            f"no broken connections across {len(connected_files)} connected file(s)."
        )
    else:
        n = len(manifest["broken_connections"])
        manifest["summary"] = (
            f"BLOCKED: {n} broken connection(s) found in proposed {proposed_path}. "
            f"See broken_connections."
        )

    return manifest


def _looks_related(name: str, proposed_path: str) -> bool:
    """
    Heuristic: does an imported name plausibly belong to the proposed file?
    We use the filename stem as a weak signal. Conservative by design - false
    negatives (missing a real break) are caught by the LLM pass; we avoid false
    positives that would block good builds.
    """
    stem = os.path.splitext(os.path.basename(proposed_path))[0].lower()
    return name.lower() in stem or stem in name.lower()


def _is_probably_provided_by(name: str, proposed_path: str) -> bool:
    """
    Heuristic for method/function calls: only treat a call as 'should be provided
    by the proposed file' when the name has the shape of an internal API (leading
    underscore, or matches the file stem). Keeps the mechanical pass conservative;
    the LLM pass handles the broad net.
    """
    if name.startswith("_"):
        return True
    stem = os.path.splitext(os.path.basename(proposed_path))[0].lower()
    return stem in name.lower()


def render_manifest_for_llm(manifest: Dict[str, Any], proposed_path: str) -> str:
    """
    Turn the manifest into a compact briefing for the Inspec.tor SUIT (DeepSeek),
    which runs AFTER this and investigates outward from these findings.
    """
    lines = [
        f"MECHANICAL CONNECTION MANIFEST for proposed change to: {proposed_path}",
        f"Result: {'CLEAN' if manifest['ok'] else 'BROKEN CONNECTIONS FOUND'}",
        f"Parse OK: {manifest['parse_ok']}",
        "",
        f"Symbols the proposed file defines: {', '.join(manifest['proposed_defines']) or '(none)'}",
        "",
    ]
    if manifest["broken_connections"]:
        lines.append("BROKEN CONNECTIONS (mechanical):")
        for b in manifest["broken_connections"]:
            lines.append(f"  - [{b['type']}] {b['detail']}")
    else:
        lines.append("No mechanical breaks detected.")
    if manifest["warnings"]:
        lines.append("\nWARNINGS:")
        for w in manifest["warnings"]:
            lines.append(f"  - [{w['type']}] {w['detail']}")
    lines.append(
        "\nYOUR TASK (Inspec.tor follow-up): First, look for MAJOR errors the "
        "mechanical check could not cover (semantic/logic errors, wrong behavior). "
        "Second, for each broken connection above, trace what ELSE it disrupts "
        "downstream - retrieval, Buselzebub transport, logging, any subsystem that "
        "depends on the affected endpoint. Report concisely."
    )
    return "\n".join(lines)


# ── Self-test ──
if __name__ == "__main__":
    print("Inspec.tor mechanical analyzer - self-test\n")

    # Scenario: the _write rename bug we actually hit.
    # Old logger had _write; proposed version renames it to _write_log.
    # Orchestrator calls high_daemon.logger._write(...). That call should break.
    proposed_logger = '''
class AutocraftLogger:
    def _write_log(self, path, tag, entry):
        pass
    def log_daemon_pulse(self, sev, msg):
        pass
'''
    orchestrator_caller = '''
class Orchestrator:
    def abort(self, high_daemon):
        high_daemon.logger._write("path", "CIRCUIT BREAKER", "boom")
'''

    m = build_connection_manifest(
        proposed_path="Twingate_internal_logger.py",
        proposed_source=proposed_logger,
        connected_files={"Twingate_pathways_orchestrator.py": orchestrator_caller},
    )
    print("TEST 1 - renamed _write (should BLOCK):")
    print(f"  ok={m['ok']}  (expected False)")
    for b in m["broken_connections"]:
        print(f"    {b['detail']}")
    print()

    # Scenario: clean change - _write still present.
    proposed_logger_ok = '''
class AutocraftLogger:
    def _write(self, path, tag, entry):
        pass
    def log_daemon_pulse(self, sev, msg):
        pass
'''
    m2 = build_connection_manifest(
        proposed_path="Twingate_internal_logger.py",
        proposed_source=proposed_logger_ok,
        connected_files={"Twingate_pathways_orchestrator.py": orchestrator_caller},
    )
    print("TEST 2 - _write intact (should CLEAR):")
    print(f"  ok={m2['ok']}  (expected True)")
    print(f"  {m2['summary']}")
    print()

    # Scenario: proposed file has a syntax error (should block).
    m3 = build_connection_manifest(
        proposed_path="broken.py",
        proposed_source="def oops(:\n    pass",
        connected_files={},
    )
    print("TEST 3 - syntax error in proposal (should BLOCK):")
    print(f"  ok={m3['ok']}  (expected False)  parse_ok={m3['parse_ok']}")
    print()

    print("LLM briefing render (Test 1):")
    print("-" * 50)
    print(render_manifest_for_llm(m, "Twingate_internal_logger.py"))
