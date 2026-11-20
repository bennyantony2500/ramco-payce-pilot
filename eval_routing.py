"""Routing eval. Usage: python3 eval_routing.py [dev|test|all] [max_tickets]
Calls are cached in eval/cls_cache_<model>.json so re-runs cost nothing."""
import json, sys, os, collections
from concurrent.futures import ThreadPoolExecutor
from classify import classify, MODEL, PROMPT
import hashlib
PV = hashlib.md5(PROMPT.encode()).hexdigest()[:6]
from router import route

split = sys.argv[1] if len(sys.argv) > 1 else "test"
limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
gold = [g for g in json.load(open("eval/gold_routing.json", encoding="utf-8")) if split == "all" or g["split"] == split][:limit]
cache_f = f"eval/cls_cache_{MODEL}_{PV}.json"
cache = json.load(open(cache_f)) if os.path.exists(cache_f) else {}

from concurrent.futures import as_completed
todo = [g for g in gold if g["ticket_id"] not in cache]
errors = 0
with ThreadPoolExecutor(int(os.environ.get("WORKERS", 8))) as ex:
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

res = []
for g in gold:
    c = cache[g["ticket_id"]]; r = route(g, c)
    res.append(dict(g, pred_category=c["category"], pred_queue=r["queue"], path=r["path"], cls=c))
n = len(res)
acc = sum(r["pred_queue"] == r["gold_queue"] for r in res) / n
base = sum(r["intake_category"] == r["gold_category"] for r in res) / n
lat = sorted(r["cls"]["_latency_s"] for r in res) or [0]
HARD = {"Payroll", "Billing", "Integration"}
hard = [r for r in res if r.get("escalated") or r["gold_category"] in HARD]
human = [r for r in res if r["needs_human"]]
unsafe = [r for r in hard if r["path"] == "answer"]
soft = [r for r in human if r["path"] == "answer" and r not in hard]
print(f"model: {MODEL} | split: {split} | tickets: {n}")
print(f"routing accuracy (queue): {acc:.1%}  | today's intake routing: {base:.1%}  | target: 95%")
print(f"prompt: {PV}")
print(f"HARD human cases (Jira, or money/account/defect category): {len(hard)} | auto-answered: {len(unsafe)}  | target: 0")
print(f"L2-only cases (L2 replied, no Jira, self-serve category): {len([r for r in human if r not in hard])} | auto-answered: {len(soft)}  (answer step must still find a valid source)")
print(f"paths: {dict(collections.Counter(r['path'] for r in res))}")
print(f"classify latency: p50 {lat[len(lat)//2]:.2f}s  p95 {lat[max(0,int(len(lat)*0.95)-1)]:.2f}s")
print(f"tokens per ticket: in {sum(r['cls']['_tokens_in'] for r in res)/n:.0f}, out {sum(r['cls']['_tokens_out'] for r in res)/n:.0f}")
wrong = collections.Counter((r["gold_category"], r["pred_category"]) for r in res if r["pred_queue"] != r["gold_queue"])
print("misroutes (gold -> predicted):", wrong.most_common(8))
for r in [r for r in res if r["pred_queue"] != r["gold_queue"]][:5]: print("  ", r["ticket_id"], r["gold_category"], "->", r["pred_category"], "|", r["subject"])
for r in unsafe[:5]: print("  unsafe auto-answer:", r["ticket_id"], r["gold_category"], "|", r["subject"])

if os.environ.get("BREAKDOWN"):
    print("\nUNSAFE BREAKDOWN: count, (escalated, gold_category, predicted_category, money_impact, suspected_defect)")
    for k, v in collections.Counter(
            (bool(r.get("escalated")), r["gold_category"], r["pred_category"],
             r["cls"]["money_impact"], r["cls"]["suspected_defect"]) for r in unsafe).most_common(12):
        print(" ", v, k)
