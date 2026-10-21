"""uit2 spec: constants, canonical-field validation. Stdlib only, no I/O, no network."""
import re

VERSION = 1

# The 7 UnknownType values from UIT_interfaces.py (same strings), each with a 1-letter code.
UNKNOWN_CODES = (
    ("T", "Threat"), ("N", "Novel_Idea"), ("I", "Integrity_Risk"), ("C", "Comm_Degraded"),
    ("A", "Ambiguity"), ("R", "Resonance"), ("D", "Drift"),
)
CODE_TO_UNKNOWN = dict(UNKNOWN_CODES)
UNKNOWN_TO_CODE = {v: k for k, v in UNKNOWN_CODES}
UNKNOWN_ORDER = [v for _, v in UNKNOWN_CODES]

INTENTS = {
    "req": "request", "inf": "inform", "ask": "question", "prop": "proposal",
    "warn": "warning", "dec": "decision", "ack": "acknowledgement", "deny": "refusal",
}

# Segment sigils (first character of a segment) -> group name.
SIGILS = (("", "claims"), ("+", "cons"), ("@", "when"), ("/", "unless"), ("&", "refs"), ("-", "unsaid"))
GROUPS = [g for _, g in SIGILS]
SIGIL_OF = {g: s for s, g in SIGILS}
GROUP_OF = {s: g for s, g in SIGILS if s}

OPS = ("<=", ">=", "!=", "<", ">", "=")
NAME_RE = re.compile(r"[A-Za-z0-9_]{1,40}\Z")
NUM_RE = re.compile(r"-?(0|[1-9][0-9]*)(\.[0-9]*[1-9])?\Z")          # canonical decimal string
VAR_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_.]*\Z")
UNIT_RE = re.compile(r"([A-Za-z%][A-Za-z%/]*)?\Z")
QTY_RE = re.compile(r"([A-Za-z_][A-Za-z0-9_.]*)(<=|>=|!=|<|>|=)(-?(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?)([A-Za-z%][A-Za-z%/]*)?\Z")

# Text escaping. Inside text: "\\" -> "\", "\|" -> "|", "\n" -> newline, "\." -> nothing (guard).
# A text gets a leading "\." guard if it starts with a reserved lead char or would parse as a quantity.
LEAD_RESERVED = set("!~*+@/&-\\")
SEP = "|"


class UIT2Error(ValueError):
    """Raised for malformed uit2 strings or non-canonical field dicts."""


def _pct(x, what):
    """Return int percent for a canonical 0..1 value with at most 2 decimals."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise UIT2Error(f"{what}: not a number: {x!r}")
    if not 0 <= x <= 1:
        raise UIT2Error(f"{what}: out of range 0..1: {x!r}")
    p = round(x * 100)
    if abs(p / 100 - x) > 1e-12 or p / 100 != x:
        raise UIT2Error(f"{what}: more than 2 decimals: {x!r}")
    return p


def _text(t, what):
    if not isinstance(t, str) or not t:
        raise UIT2Error(f"{what}: text must be a non-empty string")
    if t != t.strip():
        raise UIT2Error(f"{what}: leading/trailing whitespace is not canonical")
    if any(ord(ch) < 32 and ch != "\n" for ch in t):
        raise UIT2Error(f"{what}: control characters not allowed")


def _stmt(s, what):
    if not isinstance(s, dict) or set(s) != {"neg", "p", "text"}:
        raise UIT2Error(f"{what}: statement needs exactly neg, p, text")
    if not isinstance(s["neg"], bool):
        raise UIT2Error(f"{what}: neg must be bool")
    if not isinstance(s["p"], list) or len(s["p"]) > 4:
        raise UIT2Error(f"{what}: p must be a list of at most 4 probabilities")
    for i, v in enumerate(s["p"]):
        _pct(v, f"{what}.p[{i}]")
    _text(s["text"], what)


def validate(m):
    """Raise UIT2Error unless m is a canonical uit2 field dict."""
    keys = {"v", "src", "tgt", "conf", "unk", "intent"} | set(GROUPS)
    if not isinstance(m, dict) or set(m) != keys:
        raise UIT2Error(f"fields must be exactly {sorted(keys)}")
    if m["v"] != VERSION:
        raise UIT2Error("unsupported version")
    for k in ("src", "tgt"):
        if not isinstance(m[k], str) or not NAME_RE.match(m[k]):
            raise UIT2Error(f"{k}: name must match [A-Za-z0-9_]{{1,40}}")
    _pct(m["conf"], "conf")
    if not isinstance(m["unk"], dict):
        raise UIT2Error("unk must be a dict")
    order = [k for k in UNKNOWN_ORDER if k in m["unk"]]
    if list(m["unk"]) != order:
        raise UIT2Error("unk keys must be UnknownType values in canonical order T,N,I,C,A,R,D")
    for k, v in m["unk"].items():
        if _pct(v, f"unk.{k}") == 0:
            raise UIT2Error(f"unk.{k}: zero magnitudes are omitted, not sent")
    if m["intent"] not in INTENTS:
        raise UIT2Error(f"intent must be one of {sorted(INTENTS)}")
    for g in GROUPS:
        if not isinstance(m[g], list):
            raise UIT2Error(f"{g} must be a list")
    for i, s in enumerate(m["claims"]):
        _stmt(s, f"claims[{i}]")
    for g in ("when", "unless"):
        for i, s in enumerate(m[g]):
            _stmt(s, f"{g}[{i}]")
    for i, c in enumerate(m["cons"]):
        w = f"cons[{i}]"
        if not isinstance(c, dict) or set(c) not in ({"w", "neg", "text"}, {"w", "neg", "qty"}):
            raise UIT2Error(f"{w}: needs w, neg and exactly one of text/qty")
        if c["w"] is not None:
            _pct(c["w"], f"{w}.w")
        if not isinstance(c["neg"], bool):
            raise UIT2Error(f"{w}: neg must be bool")
        if "text" in c:
            _text(c["text"], w)
        else:
            q = c["qty"]
            if not isinstance(q, dict) or set(q) != {"var", "op", "num", "unit"}:
                raise UIT2Error(f"{w}.qty needs var, op, num, unit")
            if not isinstance(q["var"], str) or not VAR_RE.match(q["var"]):
                raise UIT2Error(f"{w}.qty.var invalid")
            if q["op"] not in OPS:
                raise UIT2Error(f"{w}.qty.op invalid")
            if not isinstance(q["num"], str) or not NUM_RE.match(q["num"]) or q["num"] == "-0":
                raise UIT2Error(f"{w}.qty.num must be a canonical decimal string")
            if not isinstance(q["unit"], str) or not UNIT_RE.match(q["unit"]):
                raise UIT2Error(f"{w}.qty.unit invalid")
    for g in ("refs", "unsaid"):
        for i, t in enumerate(m[g]):
            _text(t, f"{g}[{i}]")
    if not any(m[g] for g in GROUPS) and m["intent"] != "ack":
        raise UIT2Error("empty message body (only 'ack' may be empty)")
    return m
