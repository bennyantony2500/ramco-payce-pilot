"""Plain-code router. The model classifies; these rules decide where the ticket goes."""
SOP_QUEUE = {"Payroll": "Payroll-Ops", "Statutory": "Statutory-Compliance", "How-To": "General-L1", "Reports": "Reports-Analytics",
             "Leave & Attendance": "Leave-Attendance", "Integration": "Integrations", "Billing": "Billing",
             "Access / Login": "Access-Support", "Onboarding": "Onboarding"}
SELF_SERVE = {"How-To", "Reports", "Access / Login", "Onboarding", "Leave & Attendance", "Statutory"}

def route(ticket, cls):
    """Return queue, path (answer | human) and the reasons. Money and edge cases always go to a human."""
    reasons = []
    if ticket.get("priority") == "P1":          reasons.append("P1")
    if cls["money_impact"]:                     reasons.append("money impact")
    if cls["suspected_defect"]:                 reasons.append("suspected defect")
    if cls["category"] not in SELF_SERVE:       reasons.append(f"{cls['category']} needs account data or approval")
    return {"queue": SOP_QUEUE[cls["category"]], "path": "human" if reasons else "answer", "reasons": reasons}
