"""PII leak eval. A: planted fake values in synthetic tickets. B: all real tickets, checked with independent detectors."""
import json, random, re, sys
from pii_gate import mask, mask_ticket, TEXT_FIELDS
random.seed(7)

def gen():
    return {
      "email":   f"user{random.randint(10,99)}@acme{random.randint(1,9)}.example",
      "phone_in":f"+91 9{random.randint(100000000,999999999)}",
      "phone_ae":f"+971 5{random.randint(0,9)} {random.randint(100,999)} {random.randint(1000,9999)}",
      "aadhaar": f"{random.randint(2000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)}",
      "pan":     "ABCDE%04dF" % random.randint(0,9999),
      "ifsc":    "HDFC0%06d" % random.randint(0,999999),
      "eid":     f"784-{random.randint(1950,2005)}-{random.randint(1000000,9999999)}-{random.randint(0,9)}",
      "iban":    "AE%02d 0331 %04d %04d %04d %03d" % (random.randint(10,99), *[random.randint(0,9999) for _ in range(3)], random.randint(0,999)),
      "acct":    str(random.randint(10**10, 10**12)),
    }
TEMPLATES = [
 "Hi, my details are {email} and {phone_in}. Salary slip is wrong.",
 "Employee Aadhaar {aadhaar}, PAN {pan}, bank IFSC {ifsc}. Please fix PF.",
 "WPS issue for Emirates ID {eid}. IBAN {iban}. Call {phone_ae}.",
 "Forwarded from {email}: {phone_ae} {phone_in} {pan}",
 "Bank details for the employee: A/C {acct}, IFSC {ifsc}. Please correct.",
 "PF ka deduction galat hai, PAN {pan} / Aadhaar {aadhaar} attached for KYC.",
 "كيف يمكنني تحميل كشوف الرواتب؟ Salary account IBAN {iban}, Emirates ID {eid}.",
]
leaks, total = [], 0
for _ in range(50):
    vals = gen()
    for tpl in TEMPLATES:
        masked, _ = mask(tpl.format(**vals))
        for k, v in vals.items():
            if "{"+k+"}" in tpl:
                total += 1
                if v in masked or v.replace(" ", "") in masked.replace(" ", ""):
                    leaks.append((k, v, masked))
print(f"A. planted values: {total} | leaks: {len(leaks)}")
for l in leaks[:5]: print("  ", l)

RESIDUE = {
  "long digit run":      re.compile(r"\d(?:[\s-]?\d){8,}"),
  "email @":             re.compile(r"\S@\S"),
  "PAN shape":           re.compile(r"[A-Z]{5}\d{4}[A-Z]"),
  "IBAN country prefix": re.compile(r"\b(?:AE|IN)\d{2}\s?\d{4}"),
  "IFSC shape":          re.compile(r"[A-Z]{4}0\w{6}"),
}
tickets = json.load(open(sys.argv[1], encoding="utf-8"))["tickets"]
bad = []
for t in tickets:
    m = mask_ticket(t)
    for k in TEXT_FIELDS:
        for name, rx in RESIDUE.items():
            if m.get(k) and rx.search(m[k]):
                bad.append((t.get("ticket_id") or t.get("tkt") or t.get("reference"), k, name, m[k][:120]))
print(f"B. real tickets: {len(tickets)} | tickets with residue: {len({b[0] for b in bad})}")
for b in bad[:5]: print("  ", b)
