"""Build the gold set for routing from each ticket's own history (masked text only).
gold_category = category at the final 'resolved' event. needs_human = an L2/L3 reply or a Jira escalation happened."""
import json, os, re, sys, hashlib
from pii_gate import mask_ticket
from normalise import normalise, load_customers, category

SOP_QUEUE = {"Payroll": "Payroll-Ops", "Statutory": "Statutory-Compliance", "How-To": "General-L1", "Reports": "Reports-Analytics",
             "Leave & Attendance": "Leave-Attendance", "Integration": "Integrations", "Billing": "Billing",
             "Access / Login": "Access-Support", "Onboarding": "Onboarding"}

def events(t):
    if "events" in t:  return [(e["event"].lower(), e.get("meta") or {}) for e in t["events"]]
    if "history" in t: return [(e["action"].lower(), e.get("data") or {}) for e in t["history"]]
    return [(e["evt"].lower(), e.get("info") or {}) for e in t["activity_log"]]

def subject_key(s):
    return re.sub(r"^(re|fw|fwd)\s*:\s*", "", (s or "").strip(), flags=re.I).lower()

if __name__ == "__main__":
    dataroom = sys.argv[1]
    customers, by_name = load_customers(dataroom)
    raw = json.load(open(os.path.join(dataroom, "data/tickets_export.json"), encoding="utf-8"))["tickets"]
    gold, seen = [], set()
    for t in raw:
        m = mask_ticket(t); n = normalise(m, customers, by_name)
        if n["ticket_id"] in seen: continue
        seen.add(n["ticket_id"]); ev = events(t)
        intake = category(next(md.get("category") for a, md in ev if a == "created"))
        final = category([md for a, md in ev if a == "resolved"][-1]["category"])
        key = subject_key(n["subject"])
        gold.append(dict(
            ticket_id=n["ticket_id"], region=n["region"], customer_id=n["customer_id"], created_at=n["created_at"].isoformat(),
            priority=n["priority"], subject=n["subject"], body=n["body"], subject_key=key,
            split="test" if int(hashlib.md5(key.encode()).hexdigest(), 16) % 2 else "dev",   # split by template, never by row
            intake_category=intake, gold_category=final, gold_queue=SOP_QUEUE[final],
            needs_human=any((a == "replied" and md.get("tier") in ("L2", "L3")) or a == "escalated" for a, md in ev),
            escalated=any(a == "escalated" for a, md in ev)))
    json.dump(gold, open("eval/gold_routing.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    for s in ("dev", "test"):
        g = [x for x in gold if x["split"] == s]
        print(f"{s}: {len(g)} tickets, {len({x['subject_key'] for x in g})} templates, "
              f"intake routing correct today: {sum(x['intake_category'] == x['gold_category'] for x in g)/len(g):.1%}")
