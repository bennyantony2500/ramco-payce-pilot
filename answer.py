"""Answer from date-valid policy chunks only, with sources. Hands off when evidence is weak."""
import json, time, threading
from pydantic import BaseModel
from embed_safe import embed
from embed import _project
from db import vec
from classify import MODEL, LOCATION

MIN_SCORE = 0.55   # starting value; tune against the eval
TOP_K = 4

class Draft(BaseModel):
    answerable: bool
    answer: str
    sources: list[str]

PROMPT = """You answer an HR and payroll customer's support question for Ramco Payce using ONLY the context below.
Rules:
- If the context does not directly answer the question, set answerable=false and leave answer empty.
- Do not state any number, date, rate or deadline that is not in the context.
- List the ids of the context chunks you used in sources.
- Reply in the customer's language (code: {language}). At most 120 words.

Context:
{context}

Ticket subject: {subject}
Ticket body: {body}"""

_clients, _lock = {}, threading.Lock()
def _client(loc):
    from google import genai
    with _lock:
        if loc not in _clients:
            _clients[loc] = genai.Client(vertexai=True, project=_project(), location=loc)
        return _clients[loc]

def _generate(prompt, region):
    from google.genai import types
    c = _client(LOCATION[region])
    for attempt in range(6):
        try:
            return c.models.generate_content(model=MODEL, contents=prompt,
                config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json",
                    response_schema=Draft,
                    thinking_config=types.ThinkingConfig(thinking_level="MINIMAL")))
        except Exception as e:
            if attempt == 5 or not any(k in str(e) for k in ("429", "503", "RESOURCE_EXHAUSTED")): raise
            time.sleep(2 ** attempt)

def retrieve(conn, region, qv, as_of):
    rows = conn.execute("""
        SELECT source_id, source_type, title, text, 1 - (embedding <=> %s::vector) AS score
        FROM policy_chunks
        WHERE region IN (%s, 'ALL') AND (valid_from IS NULL OR valid_from <= %s)
          AND (valid_to IS NULL OR valid_to > %s)
        ORDER BY embedding <=> %s::vector LIMIT %s""",
        (qv, region, as_of, as_of, qv, TOP_K)).fetchall()
    return [dict(source_id=r[0], source_type=r[1], title=r[2], text=(r[3] or "")[:1500],
                 score=float(r[4])) for r in rows]

def answer(conn, region, subject, body, language, as_of):
    t0 = time.perf_counter()
    qv = vec(embed([f"{subject}. {body}"], task="RETRIEVAL_QUERY")[0])
    chunks = retrieve(conn, region, qv, as_of)
    out = {"top_score": round(chunks[0]["score"], 3) if chunks else 0.0,
           "retrieved": [c["source_id"] for c in chunks], "answer": "", "sources": [],
           "answerable": False, "reason": "", "contexts": [], "_tokens_in": 0, "_tokens_out": 0}
    use = [c for c in chunks if c["score"] >= MIN_SCORE]
    if not use:
        out["reason"] = "weak retrieval"
    else:
        ctx = "\n\n".join(f"[{c['source_id']}] {c['title']}\n{c['text']}" for c in use)
        r = _generate(PROMPT.format(language=language, context=ctx, subject=subject, body=body), region)
        d = json.loads(r.text)
        valid = [s for s in d["sources"] if s in {c["source_id"] for c in use}]
        u = r.usage_metadata
        out["_tokens_in"] = u.prompt_token_count or 0
        out["_tokens_out"] = (u.candidates_token_count or 0) + (getattr(u, "thoughts_token_count", 0) or 0)
        out["contexts"] = [c["text"] for c in use]
        if d["answerable"] and valid and d["answer"].strip():
            out.update(answerable=True, answer=d["answer"].strip(), sources=valid)
        else:
            out["reason"] = "model: context does not answer" if not d["answerable"] else "no valid citation"
    out["_latency_s"] = round(time.perf_counter() - t0, 3)
    return out
