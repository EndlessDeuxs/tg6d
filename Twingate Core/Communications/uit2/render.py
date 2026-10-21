"""uit2 renderer: canonical field dict -> deterministic plain English, for human audit."""
from .spec import INTENTS, validate

_OPS = {"<=": "at most", ">=": "at least", "!=": "not equal to", "<": "less than", ">": "more than", "=": "exactly"}


def _p(x):
    return f"{x:.2f}"


def _stmt(s):
    body = ("NOT: " if s["neg"] else "") + s["text"]
    for p in reversed(s["p"]):          # stacked: outer probability first
        body = f"[probability {_p(p)} that] {body}"
    return body


def _con(c):
    w = f" (weight {_p(c['w'])})" if c["w"] is not None else ""
    if "qty" in c:
        q = c["qty"]
        body = f"{q['var']} {_OPS[q['op']]} {q['num']}" + (f" {q['unit']}" if q["unit"] else "")
    else:
        body = c["text"]
    return ("must NOT: " if c["neg"] else "must: ") + body + w


def render(m):
    """Deterministic English rendering of a canonical uit2 field dict (one fact per line)."""
    validate(m)
    out = [f"From {m['src']} to {m['tgt']}: {INTENTS[m['intent']]}, sender confidence {_p(m['conf'])}."]
    if m["unk"]:
        out.append("Unknowns: " + ", ".join(f"{k.replace('_', ' ').lower()} {_p(v)}" for k, v in m["unk"].items()) + ".")
    out += [f"Claim: {_stmt(s)}" for s in m["claims"]]
    out += [f"Constraint: {_con(c)}" for c in m["cons"]]
    out += [f"Only if: {_stmt(s)}" for s in m["when"]]
    out += [f"Unless: {_stmt(s)}" for s in m["unless"]]
    out += [f"Reference: {r}" for r in m["refs"]]
    out += [f"Deliberately left unsaid: {u}" for u in m["unsaid"]]
    return "\n".join(out) + "\n"
