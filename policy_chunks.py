"""Build policy chunks with region and effective dates. No DB or model calls here."""
import json, os, re
from datetime import datetime

def build_chunks(dataroom):
    rules = json.load(open(os.path.join(dataroom, "integrations/statutory_rules.json"), encoding="utf-8"))["rules"]
    kb = json.load(open(os.path.join(dataroom, "data/kb_articles.json"), encoding="utf-8"))
    norm = lambda r: "UAE" if r in ("UAE", "AE") else r
    chunks = []

    # 1. Statutory rules: valid from their effective date
    for r in rules:
        chunks.append(dict(
            source_id=r["rule_id"], source_type="statutory_rule", region=norm(r["region"]), topic=r["topic"],
            title=r["title"], valid_from=r["effective_from"], valid_to=None, superseded_by=None,
            text=f"{r['title']}. Effective from {r['effective_from']}. Previous: {r['old_value']}. Now: {r['new_value']}. Source: {r['source']}."))

    # 2. KB articles: expire when a later rule changes their topic
    for a in kb:
        later = [r for r in rules if a["topic"] in r["affects_kb_topics"]
                 and r["effective_from"] > a["last_reviewed"]
                 and r["new_value"].split(";")[0].strip().lower() != "unchanged"]
        later.sort(key=lambda r: r["effective_from"])
        body = a["excerpt"] if "See full article" not in a["excerpt"] else ""
        chunks.append(dict(
            source_id=a["id"], source_type="kb_article", region=norm(a["region"]), topic=a["topic"],
            title=a["title"], valid_from=None,
            valid_to=later[0]["effective_from"] if later else None,
            superseded_by=later[0]["rule_id"] if later else None,
            text=f"{a['title']}. {body}".strip()))

    # 3. Process docs: one chunk per '## ' section
    for fn in sorted(os.listdir(os.path.join(dataroom, "process"))):
        raw = open(os.path.join(dataroom, "process", fn), encoding="utf-8").read()
        doc_title = raw.splitlines()[0].lstrip("# ").strip()
        m = re.search(r"effective for contracts signed or renewed on or after (\d{1,2} \w+ \d{4})", raw)
        vf = datetime.strptime(m.group(1), "%d %B %Y").date().isoformat() if m else None
        for i, sec in enumerate(re.split(r"\n(?=## )", raw)):
            head = sec.splitlines()[0].lstrip("# ").strip()
            text = sec.strip()
            if len(text) < 40:
                continue
            chunks.append(dict(
                source_id=f"{fn.replace('.md','')}#{i}", source_type="process_doc", region="ALL", topic=fn.replace(".md",""),
                title=f"{doc_title} > {head}" if i else doc_title, valid_from=vf, valid_to=None, superseded_by=None,
                text=text))
    return chunks

if __name__ == "__main__":
    import sys, collections
    c = build_chunks(sys.argv[1])
    print("chunks:", len(c), dict(collections.Counter(x["source_type"] for x in c)))
    print("India DB gets:", sum(x["region"] in ("IN","ALL") for x in c), "| UAE DB gets:", sum(x["region"] in ("UAE","ALL") for x in c))
    for x in c:
        if x["valid_to"]: print("expires:", x["source_id"], x["valid_to"], "->", x["superseded_by"])
