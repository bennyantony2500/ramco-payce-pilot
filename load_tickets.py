"""Reload customers and tickets: PII gate first, then normalise, then write each row to its region's DB."""
import json, os, sys
from psycopg.types.json import Jsonb
from pii_gate import mask_ticket
from normalise import normalise, load_customers
from db import connect

dataroom = sys.argv[1]
customers, by_name = load_customers(dataroom)
raw = json.load(open(os.path.join(dataroom, "data/tickets_export.json"), encoding="utf-8"))["tickets"]

rows, seen, dupes, unmapped = {"IN": [], "UAE": []}, set(), 0, 0
for t in raw:
    m = mask_ticket(t)                      # 1. PII gate before anything else
    n = normalise(m, customers, by_name)    # 2. normalise
    if n["ticket_id"] in seen:              # same ticket exported twice (9 identical, 5 differ only in status spelling)
        dupes += 1; continue
    seen.add(n["ticket_id"])
    if n["region"] not in rows:
        unmapped += 1; continue
    n["raw"] = Jsonb(m)                     # raw copy is the MASKED ticket
    rows[n["region"]].append(n)

for region, rs in rows.items():
    with connect(region) as conn:
        conn.execute("TRUNCATE tickets, customers")
        with conn.cursor() as cur:
            cur.executemany("""INSERT INTO customers (customer_id, name, tier, region, monthly_fee_usd, employees_paid)
                               VALUES (%(customer_id)s, %(name)s, %(tier)s, %(region)s, %(monthly_fee_usd)s, %(employees_paid)s)""",
                            [c for c in customers.values() if c["region"] == region])
            cur.executemany("""INSERT INTO tickets (ticket_id, customer_id, region, source_system, channel, subject, body, category,
                               priority, status, created_at, first_response_at, resolved_at, from_email, raw)
                               VALUES (%(ticket_id)s, %(customer_id)s, %(region)s, %(source_system)s, %(channel)s, %(subject)s, %(body)s,
                               %(category)s, %(priority)s, %(status)s, %(created_at)s, %(first_response_at)s, %(resolved_at)s,
                               %(from_email)s, %(raw)s)""", rs)
        print(region, conn.execute("SELECT (SELECT count(*) FROM tickets), (SELECT count(*) FROM customers)").fetchone(), "(tickets, customers)")
print(f"export rows: {len(raw)} | duplicates skipped: {dupes} | no customer/region: {unmapped}")
