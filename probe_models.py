"""Try each candidate model in each region with a tiny prompt. Prints what works."""
import time
from google import genai
from google.genai import types
from embed import _project
MODELS = ["gemini-3.1-flash-lite", "gemini-3.5-flash-lite", "gemini-3.5-flash", "gemini-3.8-flash", "gemini-3-flash-preview", "gemini-2.5-flash-lite"]
REGIONS = ["asia-south1", "me-central1", "me-central2"]
for loc in REGIONS:
    c = genai.Client(vertexai=True, project=_project(), location=loc)
    for m in MODELS:
        for label, cfg in (("minimal thinking", types.GenerateContentConfig(temperature=0, thinking_config=types.ThinkingConfig(thinking_level="MINIMAL"))),
                           ("default", types.GenerateContentConfig(temperature=0))):
            t0 = time.perf_counter()
            try:
                r = c.models.generate_content(model=m, contents="Reply with the single word OK.", config=cfg)
                print(f"OK    {loc:12} {m:24} {label:17} {time.perf_counter()-t0:.2f}s  -> {r.text.strip()[:10]}")
                break
            except Exception as e:
                msg = str(e).split("{")[0].strip()[:40]
                print(f"FAIL  {loc:12} {m:24} {label:17} {msg}")
