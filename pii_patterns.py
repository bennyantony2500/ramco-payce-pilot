import re
# Order matters: specific patterns first. ACCOUNT is the catch-all for any 9-18 digit run.
PATTERNS = [
    ("EMAIL",   r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"),
    ("EID",     r"\b784[-\s]?\d{4}[-\s]?\d{7}[-\s]?\d\b"),
    ("IBAN",    r"\b[A-Z]{2}\d{2}(?:[\s-]?[A-Z0-9]){11,30}\b"),
    ("AADHAAR", r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"),
    ("PAN",     r"\b[A-Z]{5}\d{4}[A-Z]\b"),
    ("IFSC",    r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
    ("PHONE",   r"(?:\+|\b00)(?:91|971)[\s-]?\d[\d\s-]{7,12}\d\b|\b[6-9]\d{4}[\s-]?\d{5}\b|\b0?5\d[\s-]?\d{3}[\s-]?\d{4}\b"),
    ("ACCOUNT", r"\b\d{9,18}\b"),
]
COMPILED = [(n, re.compile(p)) for n, p in PATTERNS]
