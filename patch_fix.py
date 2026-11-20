# --- patch 1: one shared Gemini client per region, created under a lock
p = "classify.py"; s = open(p).read()
s = s.replace("_clients = {}\n", "import threading\n_clients = {}\n_lock = threading.Lock()\n", 1)
s = s.replace("    if loc not in _clients:\n        _clients[loc] = genai.Client(vertexai=True, project=_project(), location=loc)\n",
              "    with _lock:\n        if loc not in _clients:\n            _clients[loc] = genai.Client(vertexai=True, project=_project(), location=loc)\n", 1)
assert "_lock = threading.Lock()" in s and "with _lock:" in s, "classify.py patch did not apply"
open(p, "w").write(s)
# --- patch 2: eval saves every 25 results and skips (then retries next run) any ticket that errors
p = "eval_routing.py"; s = open(p).read()
old = """todo = [g for g in gold if g["ticket_id"] not in cache]
with ThreadPoolExecutor(8) as ex:
    for g, c in zip(todo, ex.map(lambda g: classify(g["subject"], g["body"], g["region"]), todo)):
        cache[g["ticket_id"]] = c
json.dump(cache, open(cache_f, "w"), indent=0)
"""
new = """from concurrent.futures import as_completed
todo = [g for g in gold if g["ticket_id"] not in cache]
errors = 0
with ThreadPoolExecutor(8) as ex:
    futs = {ex.submit(classify, g["subject"], g["body"], g["region"]): g for g in todo}
    for i, f in enumerate(as_completed(futs), 1):
        try:
            cache[futs[f]["ticket_id"]] = f.result()
        except Exception as e:
            errors += 1; print("error:", futs[f]["ticket_id"], str(e)[:120])
        if i % 25 == 0:
            json.dump(cache, open(cache_f, "w"), indent=0); print(f"  {i}/{len(todo)} classified")
json.dump(cache, open(cache_f, "w"), indent=0)
if errors:
    print(f"{errors} tickets failed; run the same command again to retry them"); sys.exit(1)
"""
assert old in s, "eval_routing.py patch did not apply"
open(p, "w").write(s.replace(old, new, 1))
print("both patches applied")
