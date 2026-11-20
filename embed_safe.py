"""Throttled, retrying wrapper around embed.embed for a low-quota project."""
import time
import embed as _e

MIN_GAP = 2.0      # seconds between calls; raise it if 429s continue
_last = [0.0]

def embed(texts, task="RETRIEVAL_DOCUMENT", location="asia-south1"):
    for attempt in range(8):
        gap = MIN_GAP - (time.time() - _last[0])
        if gap > 0:
            time.sleep(gap)
        _last[0] = time.time()
        try:
            return _e.embed(texts, task=task, location=location)
        except Exception as ex:
            if attempt == 7 or not any(k in str(ex) for k in ("429", "RESOURCE_EXHAUSTED")):
                raise
            time.sleep(min(60, 5 * 2 ** attempt))
