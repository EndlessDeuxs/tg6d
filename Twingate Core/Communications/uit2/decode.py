"""uit2 decoder: one-line uit2 string -> canonical field dict. Strict: rejects malformed AND
non-canonical input (decode then re-encode must reproduce the input byte for byte)."""
import re
from .spec import (CODE_TO_UNKNOWN, INTENTS, GROUPS, GROUP_OF, NAME_RE, QTY_RE, VERSION, UIT2Error)
from .encode import encode

_PCT = re.compile(r"(0|[1-9][0-9]?|100)")
_HEAD = re.compile(r"([A-Za-z0-9_]{1,40})>([A-Za-z0-9_]{1,40}) c(0|[1-9][0-9]?|100)"
                   r"(?: \?([A-Z](?:0|[1-9][0-9]?|100)(?:,[A-Z](?:0|[1-9][0-9]?|100))*))? ([a-z]+)\Z")
_ESC = {"\\": "\\", "|": "|", "n": "\n", ".": ""}


def _split(s):
    """Split on unescaped '|'. Escapes are kept verbatim for _unesc."""
    segs, cur, i = [], [], 0
    while i < len(s):
        ch = s[i]
        if ch == "\\":
            if i + 1 >= len(s):
                raise UIT2Error("dangling backslash")
            cur.append(s[i:i + 2]); i += 2; continue
        if ch == "|":
            segs.append("".join(cur)); cur = []
        else:
            cur.append(ch)
        i += 1
    segs.append("".join(cur))
    return segs


def _unesc(t):
    out, i = [], 0
    while i < len(t):
        if t[i] == "\\":
            nxt = t[i + 1] if i + 1 < len(t) else ""
            if nxt not in _ESC:
                raise UIT2Error(f"unknown escape \\{nxt}")
            out.append(_ESC[nxt]); i += 2
        else:
            out.append(t[i]); i += 1
    s = "".join(out)
    if not s:
        raise UIT2Error("empty text")
    return s


def _pct(digits):
    if not _PCT.fullmatch(digits):
        raise UIT2Error(f"bad percent {digits!r}")
    return int(digits) / 100


def _stmt(body):
    p = []
    while body.startswith("~"):
        m = re.match(r"~([0-9]{1,3})", body)
        if not m:
            raise UIT2Error("~ must be followed by a percent 0-100")
        p.append(_pct(m.group(1))); body = body[m.end():]
    neg = body.startswith("!")
    if neg:
        body = body[1:]
    return {"neg": neg, "p": p, "text": _unesc(body)}


def _con(body):
    w = None
    if body.startswith("*"):
        m = re.match(r"\*([0-9]{1,3})", body)
        if not m:
            raise UIT2Error("* must be followed by a percent 0-100")
        w = _pct(m.group(1)); body = body[m.end():]
    neg = body.startswith("!")
    if neg:
        body = body[1:]
    q = QTY_RE.fullmatch(body)
    if q:
        return {"w": w, "neg": neg, "qty": {"var": q.group(1), "op": q.group(2), "num": q.group(3), "unit": q.group(4) or ""}}
    return {"w": w, "neg": neg, "text": _unesc(body)}


def decode(s):
    """Decode a uit2 string. Raises spec.UIT2Error if malformed or non-canonical."""
    if not isinstance(s, str) or not s:
        raise UIT2Error("input must be a non-empty string")
    if "\n" in s or "\r" in s:
        raise UIT2Error("uit2 messages are one line (use \\n inside text)")
    segs = _split(s)
    h = _HEAD.match(segs[0])
    if not h:
        raise UIT2Error("bad header: expected 'src>tgt cNN [?X00,..] intent'")
    if h.group(5) not in INTENTS:
        raise UIT2Error(f"unknown intent {h.group(5)!r}")
    unk = {}
    if h.group(4):
        for item in h.group(4).split(","):
            if item[0] not in CODE_TO_UNKNOWN:
                raise UIT2Error(f"unknown UnknownType code {item[0]!r}")
            name = CODE_TO_UNKNOWN[item[0]]
            if name in unk:
                raise UIT2Error(f"duplicate unknown {item[0]}")
            unk[name] = _pct(item[1:])
    m = {"v": VERSION, "src": h.group(1), "tgt": h.group(2), "conf": _pct(h.group(3)), "unk": unk,
         "intent": h.group(5)}
    for g in GROUPS:
        m[g] = []
    for seg in segs[1:]:
        if not seg:
            raise UIT2Error("empty segment")
        g = GROUP_OF.get(seg[0], "claims")
        body = seg if g == "claims" else seg[1:]
        if g in ("claims", "when", "unless"):
            m[g].append(_stmt(body))
        elif g == "cons":
            m[g].append(_con(body))
        else:
            m[g].append(_unesc(body))
    if encode(m) != s:          # also runs spec.validate
        raise UIT2Error("non-canonical uit2 (re-encode differs; check order, escapes, zero unknowns)")
    return m
