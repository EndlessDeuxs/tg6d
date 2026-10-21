"""uit2 encoder: canonical field dict -> one-line uit2 string. Deterministic, stdlib only."""
from .spec import (QTY_RE, LEAD_RESERVED, SEP, SIGIL_OF, GROUPS, UNKNOWN_TO_CODE, _pct, validate)


def esc(t):
    """Escape a text atom so it survives the grammar unchanged (see SPEC_SHEET.txt)."""
    out = t.replace("\\", "\\\\").replace("|", "\\|").replace("\n", "\\n")
    if t[0] in LEAD_RESERVED or t[0].isdigit() or QTY_RE.match(t):
        out = "\\." + out
    return out


def _stmt(s):
    return "".join(f"~{_pct(p, 'p')}" for p in s["p"]) + ("!" if s["neg"] else "") + esc(s["text"])


def _con(c):
    head = (f"*{_pct(c['w'], 'w')}" if c["w"] is not None else "") + ("!" if c["neg"] else "")
    if "qty" in c:
        q = c["qty"]
        return head + f"{q['var']}{q['op']}{q['num']}{q['unit']}"
    return head + esc(c["text"])


def encode(m):
    """Encode a canonical uit2 field dict. Raises spec.UIT2Error if it is not canonical."""
    validate(m)
    head = [f"{m['src']}>{m['tgt']}", f"c{_pct(m['conf'], 'conf')}"]
    if m["unk"]:
        head.append("?" + ",".join(f"{UNKNOWN_TO_CODE[k]}{_pct(v, k)}" for k, v in m["unk"].items()))
    head.append(m["intent"])
    segs = [" ".join(head)]
    for g in GROUPS:
        for item in m[g]:
            if g == "claims":
                body = _stmt(item)
            elif g in ("when", "unless"):
                body = _stmt(item)
            elif g == "cons":
                body = _con(item)
            else:
                body = esc(item)
            segs.append(SIGIL_OF[g] + body)
    return SEP.join(segs)
