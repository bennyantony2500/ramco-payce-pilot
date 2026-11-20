"""Shared helper: PII masking adapter. Everything calls this before any other step."""
import pii_gate

def mask_text(s):
    r = pii_gate.mask(s or "")
    return r[0] if isinstance(r, tuple) else r
