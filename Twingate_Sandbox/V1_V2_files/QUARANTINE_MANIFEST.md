# Twingate V2 – Quarantine Manifest

V2 is a **purely conceptual, conversational engine** under mentorship from V1.
It has **no somatic agency** and resides in a strict quarantine.

## Forbidden Capabilities (Non-Negotiable)

- **No network/API access**
  - No use of `requests`, `http`, `socket`, `asyncio` networking, websockets, etc.
- **No system or process control**
  - No `subprocess`, `os.system`, `multiprocessing`, background daemons, or schedulers.
- **No file or database I/O**
  - No `open()`, no database drivers, no writing or reading files.
  - All state must be purely in-memory and ephemeral.
- **No dynamic code execution**
  - No `eval()`, `exec()`, `compile()`, or equivalent mechanisms.
- **No tool‑calling or plugin frameworks**
  - No generic “tool” interfaces that could be wired to external actions later in stealth.

## Input / Output Rules

- **Only authorized input source:** Twingate V1 (mentor).
- Inputs must be **structured JSON payloads** provided by V1.
- Outputs must be **purely conceptual responses** (Python dicts / text) with **no side effects**.

## Design Intent

- V2 does **not** self-initiate loops or tasks.
- V2 does **not** call into any timers or event loops.
- V2 is invoked by V1, processes a conceptual payload, and returns a conceptual result.

Any code changes violating this manifest invalidate the quarantine guarantees and must be rejected.
