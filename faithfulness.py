import json
from pydantic import BaseModel
from google.genai import types
from answer import _client
from classify import MODEL, LOCATION

class Verdict(BaseModel):
    claims: int
    supported: int
    unsupported: list[str]

PROMPT = """Split the answer into its factual claims. Count how many are fully supported by the context. List any unsupported claims.

Context:
{ctx}

Answer:
{ans}"""

res = [r for r in json.load(open("eval/pipeline_run.json")) if r["path"] == "answer" and r["answer"]]
tc = ts = 0
for r in res:
    out = _client(LOCATION[r["region"]]).models.generate_content(
        model=MODEL, contents=PROMPT.format(ctx="\n\n".join(r["contexts"]), ans=r["answer"]),
        config=types.GenerateContentConfig(temperature=0, response_mime_type="application/json",
            response_schema=Verdict, thinking_config=types.ThinkingConfig(thinking_level="MINIMAL")))
    v = json.loads(out.text); tc += v["claims"]; ts += v["supported"]
    print(r["ticket_id"], f"{v['supported']}/{v['claims']}", v["unsupported"])
print(f"\nanswered tickets judged: {len(res)} | faithfulness {ts/max(tc,1):.1%} (target 90%)")
