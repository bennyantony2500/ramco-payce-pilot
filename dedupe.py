"""Dedupe: same customer, near-identical masked text, within 7 days. Usage: python3 dedupe.py build"""
import sys
from db import connect, vec
from embed_safe import embed
from util import mask_text

THRESHOLD = 0.90   # starting value; tune it on real pairs
DDL = """CREATE TABLE IF NOT EXISTS ticket_vectors (
  ticket_id text PRIMARY KEY, customer_id text, created_at timestamptz, embedding vector(768))"""

def ticket_text(subject, body):
    return mask_text(f"{subject or ''}. {body or ''}")[:2000]

def query_vec(subject, body):
    return vec(embed([ticket_text(subject, body)], task="SEMANTIC_SIMILARITY")[0])

def find_duplicate(conn, qv, customer_id, created_at, ticket_id):
    row = conn.execute("""
        SELECT ticket_id, 1 - (embedding <=> %s::vector) AS sim FROM ticket_vectors
        WHERE customer_id = %s AND ticket_id <> %s AND created_at < %s::timestamptz
          AND created_at >= %s::timestamptz - interval '7 days'
        ORDER BY embedding <=> %s::vector LIMIT 1""",
        (qv, customer_id, ticket_id, created_at, created_at, qv)).fetchone()
    sim = round(float(row[1]), 3) if row else None
    return {"duplicate_of": row[0] if row and sim >= THRESHOLD else None, "similarity": sim}

def build(region):
    with connect(region) as conn:
        conn.execute(DDL)
        rows = conn.execute("SELECT ticket_id, customer_id, created_at, subject, body "
                            "FROM tickets WHERE created_at IS NOT NULL").fetchall()
        for i in range(0, len(rows), 16):
            b = rows[i:i + 16]
            vs = embed([ticket_text(r[3], r[4]) for r in b], task="SEMANTIC_SIMILARITY")
            with conn.cursor() as cur:
                cur.executemany("INSERT INTO ticket_vectors VALUES (%s,%s,%s,%s::vector) "
                                "ON CONFLICT (ticket_id) DO NOTHING",
                                [(r[0], r[1], r[2], vec(v)) for r, v in zip(b, vs)])
        print(region, "indexed:", conn.execute("SELECT count(*) FROM ticket_vectors").fetchone()[0])

if __name__ == "__main__":
    if sys.argv[1:2] == ["build"]:
        for r in ("IN", "UAE"): build(r)
