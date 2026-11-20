"""Gates for the normalise and lookup steps, run on what is stored in both databases."""
from db import connect
SOP = ("Payroll","Statutory","How-To","Reports","Leave & Attendance","Integration","Billing","Access / Login","Onboarding")
for region in ("IN", "UAE"):
    with connect(region) as conn:
        q = lambda s, *a: conn.execute(s, a).fetchone()[0]
        print(region, {
          "tickets": q("SELECT count(*) FROM tickets"),
          "category not one of the 9": q("SELECT count(*) FROM tickets WHERE category IS NULL OR NOT (category = ANY(%s))", list(SOP)),
          "priority not P1-P3": q("SELECT count(*) FROM tickets WHERE priority IS NULL OR priority NOT IN ('P1','P2','P3')"),
          "no created_at": q("SELECT count(*) FROM tickets WHERE created_at IS NULL"),
          "resolved before created": q("SELECT count(*) FROM tickets WHERE resolved_at < created_at"),
          "replied before created": q("SELECT count(*) FROM tickets WHERE first_response_at < created_at"),
          "customer in wrong region": q("SELECT count(*) FROM tickets t JOIN customers c USING (customer_id) WHERE c.region <> %s", region),
          "customer not found": q("SELECT count(*) FROM tickets t LEFT JOIN customers c USING (customer_id) WHERE c.customer_id IS NULL"),
        })
