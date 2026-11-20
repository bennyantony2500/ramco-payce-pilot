"""Normalise the three ticket export schemas into one shape. Runs after the PII gate."""
import csv, os, re
from datetime import datetime, timezone, timedelta
IST = timezone(timedelta(hours=5, minutes=30)); GST = timezone(timedelta(hours=4))

# The triage SOP's nine categories. Keys are lower-cased with spaces, _ / - & stripped.
CATEGORY = {
  "howto": "How-To", "payroll": "Payroll", "payrollissue": "Payroll", "payrollrun": "Payroll",
  "statutory": "Statutory", "statutorycompliance": "Statutory", "compliancepfwps": "Statutory",
  "leave": "Leave & Attendance", "leaveattendance": "Leave & Attendance",
  "integration": "Integration", "integrations": "Integration", "apiintegration": "Integration", "integrationbug": "Integration",
  "onboarding": "Onboarding", "newcustomersetup": "Onboarding",
  "access": "Access / Login", "accesslogin": "Access / Login", "loginissue": "Access / Login",
  "reports": "Reports", "reportexport": "Reports",
  "billing": "Billing", "billinginvoices": "Billing",
}
PRIORITY = {"P1": "P1", "P2": "P2", "P3": "P3", "urgent": "P1", "high": "P2", "normal": "P3", "S1": "P1", "S2": "P2", "S3": "P3"}

def category(raw):
    key = re.sub(r"[\s_/\-&]+", "", (raw or "").lower())
    return CATEGORY.get(key)          # None = unknown spelling, caught by the eval

def ts(v):
    """Parse any of the export's timestamp formats to an aware datetime. Naive values are IST
    (checked against the epoch and GST-tagged fields in the same tickets)."""
    if v is None or v == "":
        return None
    if isinstance(v, (int, float)):
        return datetime.fromtimestamp(v / 1000, timezone.utc)
    m = re.fullmatch(r"(\d{2}/\d{2}/\d{4} \d{2}:\d{2}) (IST|GST)", v)
    if m:
        return datetime.strptime(m.group(1), "%d/%m/%Y %H:%M").replace(tzinfo=IST if m.group(2) == "IST" else GST)
    d = datetime.fromisoformat(v.replace("Z", "+00:00").replace(" ", "T"))
    return d if d.tzinfo else d.replace(tzinfo=IST)

def load_customers(dataroom):
    rows = list(csv.DictReader(open(os.path.join(dataroom, "data/customers.csv"), encoding="utf-8")))
    return {r["customer_id"]: r for r in rows}, {r["name"].strip().lower(): r["customer_id"] for r in rows}

def normalise(t, customers, by_name):
    if "ticket_id" in t:
        n = dict(ticket_id=t["ticket_id"], customer_id=t.get("customer_id"), source_system="email_helpdesk", channel=t.get("channel"),
                 subject=t.get("subject"), body=t.get("body"), category_raw=t.get("category"), priority=t.get("priority"),
                 status=t.get("status"), created_at=t.get("received_at"), first_response_at=t.get("first_response_at"),
                 resolved_at=t.get("resolved_at"), from_email=t.get("from_email"))
    elif "tkt" in t:
        n = dict(ticket_id=t["tkt"], customer_id=t.get("org_id"), source_system="inapp_widget", channel="widget",
                 subject=t.get("title"), body=t.get("message"), category_raw=t.get("cat"), priority=t.get("prio"),
                 status=t.get("state"), created_at=t.get("created"), first_response_at=t.get("first_reply_ts"),
                 resolved_at=t.get("closed_ts"), from_email=None)
    else:
        cid = t.get("tenant") or by_name.get((t.get("end_customer") or "").strip().lower())
        n = dict(ticket_id=t["reference"], customer_id=cid, source_system="partner_portal", channel="partner",
                 subject=t.get("summary"), body=t.get("details"), category_raw=t.get("topic"), priority=t.get("severity"),
                 status=t.get("status"), created_at=t.get("opened_on"), first_response_at=t.get("fr_at"),
                 resolved_at=t.get("closed_at"), from_email=None)
    n["category"] = category(n.pop("category_raw"))
    n["priority"] = PRIORITY.get(n["priority"])
    n["status"] = "resolved" if (n["status"] or "").lower() in ("resolved", "solved", "closed") else (n["status"] or "").lower()
    for k in ("created_at", "first_response_at", "resolved_at"):
        n[k] = ts(n[k])
    c = customers.get(n["customer_id"])
    n["region"] = c["region"] if c else None
    return n
