"""Count stored ticket rows that still contain raw identifiers, in each region's database."""
import re
from db import connect
CHECKS = {
  "email":        re.compile(r"[\w.+-]+@[\w-]+\.\w"),
  "PAN":          re.compile(r"\b[A-Z]{5}\d{4}[A-Z]\b"),
  "Aadhaar":      re.compile(r"\b\d{4} \d{4} \d{4}\b"),
  "Emirates ID":  re.compile(r"\b784-\d{4}-\d{7}-\d\b"),
  "IBAN":         re.compile(r"\bAE\d{2} \d{4}"),
  "IFSC":         re.compile(r"\b[A-Z]{4}0[A-Z0-9]{6}\b"),
  "bank account": re.compile(r"A/C \d{9,}"),
}
for region in ("IN", "UAE"):
    with connect(region) as conn:
        rows = [r[0] for r in conn.execute("SELECT row_to_json(t)::text FROM tickets t")]
    print(region, f"{len(rows)} rows |", {k: sum(bool(rx.search(r)) for r in rows) for k, rx in CHECKS.items()})
