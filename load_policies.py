"""Embed policy chunks once, write each region's chunks to its own database."""
import sys
from policy_chunks import build_chunks
from embed import embed, DIM
from db import connect, vec

DDL = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS policy_chunks (
  source_id     text PRIMARY KEY,
  source_type   text NOT NULL,          -- statutory_rule | kb_article | process_doc
  region        text NOT NULL,          -- IN | UAE | ALL
  topic         text,
  title         text,
  valid_from    date,                   -- NULL = valid from the start
  valid_to      date,                   -- NULL = still valid; set when a later rule supersedes it
  superseded_by text,
  text          text NOT NULL,
  embedding     vector({DIM}) NOT NULL
);
CREATE INDEX IF NOT EXISTS policy_chunks_hnsw ON policy_chunks USING hnsw (embedding vector_cosine_ops);
"""

chunks = build_chunks(sys.argv[1])
vectors = embed([f"{c['title']}\n{c['text']}" for c in chunks])   # policy text is not customer data: embed once
for c, v in zip(chunks, vectors):
    c["embedding"] = vec(v)

for region in ("IN", "UAE"):
    rows = [c for c in chunks if c["region"] in (region, "ALL")]
    with connect(region) as conn:
        conn.execute(DDL)
        conn.execute("TRUNCATE policy_chunks")
        with conn.cursor() as cur:
            cur.executemany("""INSERT INTO policy_chunks (source_id, source_type, region, topic, title, valid_from, valid_to,
                               superseded_by, text, embedding) VALUES (%(source_id)s, %(source_type)s, %(region)s, %(topic)s,
                               %(title)s, %(valid_from)s, %(valid_to)s, %(superseded_by)s, %(text)s, %(embedding)s::vector)""", rows)
        n = conn.execute("SELECT count(*), count(valid_to) FROM policy_chunks").fetchone()
        print(f"{region}: {n[0]} chunks loaded, {n[1]} with an expiry date")
