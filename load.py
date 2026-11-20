import csv, json, os, datetime as dt, psycopg2
from psycopg2.extras import execute_values, Json

D = os.path.expanduser("~/paynest-support-discovery/data-room/data")
PW = os.environ.get("PGPASSWORD") or os.environ["DBPASS"]
PORTS = {"IN": 5433, "UAE": 5434}
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

def ms(v):
    return dt.datetime.fromtimestamp(v / 1000, dt.timezone.utc) if isinstance(v, (int, float)) else None
def created(s):
    try: return dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S").replace(tzinfo=IST)
    except Exception: return None

cust = list(csv.DictReader(open(f"{D}/customers.csv", encoding="utf-8-sig")))
region_of = {c["customer_id"]: c["region"] for c in cust}
tickets = json.load(open(f"{D}/tickets_export.json", encoding="utf-8"))["tickets"]

orphans = [t["tkt"] for t in tickets if t["org_id"] not in region_of]
print("tickets with unknown org_id (not loaded):", len(orphans), orphans[:5])

for region, port in PORTS.items():
    con = psycopg2.connect(host="127.0.0.1", port=port, user="postgres", password=PW, dbname="ramco")
    cur = con.cursor()
    crow = [(c["customer_id"], c["name"], c["tier"], c["region"],
             c["monthly_fee_usd"] or None, c["employees_paid"] or None)
            for c in cust if c["region"] == region]
    execute_values(cur, "INSERT INTO customers VALUES %s ON CONFLICT DO NOTHING", crow)
    trow = [(t["tkt"], t["source"], t["org_id"], t["user_ref"], t["title"], t["message"],
             t["cat"], t["prio"], t["state"], created(t["created"]),
             ms(t.get("first_reply_ts")), ms(t.get("closed_ts")), Json(t["history"]))
            for t in tickets if region_of.get(t["org_id"]) == region]
    execute_values(cur, "INSERT INTO tickets VALUES %s ON CONFLICT DO NOTHING", trow)
    con.commit()
    cur.execute("SELECT (SELECT count(*) FROM customers), (SELECT count(*) FROM tickets)")
    print(region, "customers/tickets in DB:", cur.fetchone(), "| attempted:", len(crow), len(trow))
    con.close()
