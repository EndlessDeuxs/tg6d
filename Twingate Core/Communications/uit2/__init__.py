"""uit2: Universal Intent Translator v2 shorthand (proposal UIT2-01).

Deterministic, stdlib-only encoder/decoder/renderer for a compact, auditable LLM-to-LLM intent format.
Not imported by anything in TG6D. Spec for models: SPEC_SHEET.txt. Canonical fields: spec.validate().
"""
from .spec import VERSION, UIT2Error, validate
from .encode import encode
from .decode import decode
from .render import render

__all__ = ["VERSION", "UIT2Error", "validate", "encode", "decode", "render"]
