import re
RULES = [
    ("statutory",        r"statut|complian"),
    ("integration",      r"integrat"),
    ("access_login",     r"access|login"),
    ("leave_attendance", r"leave"),
    ("billing",          r"billing"),
    ("reports",          r"report"),
    ("onboarding",       r"onboard|new customer"),
    ("payroll",          r"payroll"),
    ("how_to",           r"how[\s_-]*to"),
]
def canon(label):
    s = (label or "").lower()
    for name, pat in RULES:
        if re.search(pat, s):
            return name
    return "other"
