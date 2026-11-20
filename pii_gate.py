from pii_patterns import COMPILED

def mask(text):
    """Return (masked_text, list of (type, original_value)). Runs before every other step."""
    found = []
    out = text or ""
    for name, rx in COMPILED:
        def repl(m, name=name):
            found.append((name, m.group()))
            return f"[{name}]"
        out = rx.sub(repl, out)
    return out, found

TEXT_FIELDS = ("subject", "body", "title", "message", "summary", "details", "from_email")

def mask_ticket(t):
    """Mask every free-text field of a ticket, in all three export schemas."""
    t = dict(t)
    for k in TEXT_FIELDS:
        if t.get(k):
            t[k], _ = mask(t[k])
    return t
