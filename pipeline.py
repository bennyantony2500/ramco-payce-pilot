"""End-to-end pilot: PII gate -> lookup -> classify -> dedupe -> router -> answer | human hand-off.
Normalise runs at ingest (normalise.py / load_tickets.py), so rows here are already canonical.
Usage: python3 pipeline.py [n_per_region] """
import sys, json, time, os
from psycopg.types.json import Jsonb
from db import connect
from util import mask_text
from classify import classify
from router import route
from dedupe import query_vec, find_duplicate
from answer import answer

HANDOFF_DDL = """CREATE TABLE IF NOT EXISTS handoff_queue (
  id serial PRIMARY KEY, ticket_id text, region text, tier text, queue text, category text,
  priority text, reasons jsonb, summary text, suggested_sources jsonb,
  status text DEFAULT 'open', created_at timestamptz DEFAULT now())"""

def process(conn, region, row):
    T, t0 = {}, time.perf_counter()
    def lap(name, s): T[name] = round(time.perf_counter() - s, 3)

    s = time.perf_counter()                                   # 1. PII gate: always first
    subj, body = mask_text(row["subject"]), mask_text(row["body"])
    lap("pii", s)

    s = time.perf_counter()                                   # 2. lookup + residency guard
    cust = conn.execute("SELECT tier, region FROM customers WHERE customer_id = %s",
                        (row["customer_id"],)).fetchone()
    if not cust or cust[1] != region:
        raise RuntimeError(f"{row['ticket_id']}: customer not in {region} database")
    lap("lookup", s)

    s = time.perf_counter()                                   # 3. classify (masked text only)
    cls = classify(subj, body, region)
    lap("classify", s)

    s = time.perf_counter()                                   # 4. dedupe
    dup = find_duplicate(conn, query_vec(subj, body), row["customer_id"], row["created_at"], row["ticket_id"])
    lap("dedupe", s)

    s = time.perf_counter()                                   # 5. router (plain rules)
    r = route({"priority": row["priority"]}, cls)
    path, reasons = r["path"], list(r["reasons"])
    if dup["duplicate_of"]:
        reasons.append(f"duplicate of {dup['duplicate_of']}")
        if path == "answer":
            path = "duplicate"      # money, defect and edge tickets stay with a human
    lap("route", s)

    ans = None
    if path == "answer":                                      # 6. answer with source
        s = time.perf_counter()
        ans = answer(conn, region, subj, body, cls["language"], row["created_at"].date())
        lap("answer", s)
        if not ans["answerable"]:
            path = "human"; reasons.append(f"no supported answer ({ans['reason']})")

    if path == "human":                                       # 7. human hand-off (queue only; no payroll access)
        s = time.perf_counter()
        conn.execute("DELETE FROM handoff_queue WHERE ticket_id = %s", (row["ticket_id"],))
        conn.execute("""INSERT INTO handoff_queue (ticket_id, region, tier, queue, category, priority,
            reasons, summary, suggested_sources) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
            (row["ticket_id"], region, cust[0], r["queue"], cls["category"], row["priority"],
             Jsonb(reasons), f"[{cls['category']}] {subj}\n{body[:500]}",
             Jsonb(ans["retrieved"][:3] if ans else [])))
        lap("handoff", s)

    return {"ticket_id": row["ticket_id"], "region": region, "path": path, "queue": r["queue"],
            "category": cls["category"], "reasons": reasons, "language": cls["language"],
            "answer": ans["answer"] if ans else "", "sources": ans["sources"] if ans else [],
            "contexts": ans["contexts"] if ans else [], "top_score": ans["top_score"] if ans else None,
            "duplicate_of": dup["duplicate_of"], "similarity": dup["similarity"],
            "subject": subj, "body": body, "timings": T, "total_s": round(time.perf_counter() - t0, 3),
            "tokens_in": cls["_tokens_in"] + (ans["_tokens_in"] if ans else 0),
            "tokens_out": cls["_tokens_out"] + (ans["_tokens_out"] if ans else 0)}

def p(vals, q):
    v = sorted(vals); return v[max(0, int(round(q * len(v))) - 1)]

if __name__ == "__main__":
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    results = []
    for region in ("IN", "UAE"):
        with connect(region) as conn:
            conn.execute(HANDOFF_DDL)
            rows = conn.execute("""SELECT ticket_id, customer_id, subject, body, priority, created_at
                FROM tickets WHERE created_at IS NOT NULL ORDER BY md5(ticket_id) LIMIT %s""", (n,)).fetchall()
            for t in rows:
                row = dict(zip(("ticket_id", "customer_id", "subject", "body", "priority", "created_at"), t))
                try:
                    res = process(conn, region, row)
                except Exception as e:
                    print("ERROR", region, row["ticket_id"], repr(e)[:200]); continue
                results.append(res)
                print(f"{region:3} {res['ticket_id']} {res['category']:<18} {res['path']:<9} "
                      f"{res['total_s']:>5}s  {res['sources'] or res['reasons']}")
    os.makedirs("eval", exist_ok=True)
    json.dump(results, open("eval/pipeline_run.json", "w"), ensure_ascii=False, indent=1)
    if results:
        lat = [r["total_s"] for r in results]
        paths = {}
        for r in results: paths[r["path"]] = paths.get(r["path"], 0) + 1
        print("\npaths:", paths, "| tickets:", len(results))
        print(f"latency p50 {p(lat, .5)}s | p95 {p(lat, .95)}s | max {max(lat)}s")
        print("tokens in/out per ticket:", round(sum(r["tokens_in"] for r in results) / len(results)),
              round(sum(r["tokens_out"] for r in results) / len(results)))
