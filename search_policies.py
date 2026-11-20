"""Smoke test: top 3 policy chunks valid on a date. Usage: python3 search_policies.py IN 2026-09-10 "question" """
import sys
from embed import embed
from db import connect, vec
region, as_of, q = sys.argv[1], sys.argv[2], sys.argv[3]
qv = vec(embed([q], task="RETRIEVAL_QUERY")[0])
with connect(region) as conn:
    rows = conn.execute("""
        SELECT source_id, title, round((1 - (embedding <=> %s::vector))::numeric, 3) AS score
        FROM policy_chunks
        WHERE (valid_from IS NULL OR valid_from <= %s) AND (valid_to IS NULL OR valid_to > %s)
        ORDER BY embedding <=> %s::vector LIMIT 3""", (qv, as_of, as_of, qv)).fetchall()
for r in rows: print(r)
