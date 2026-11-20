"""Embeddings via Vertex AI (multilingual model: handles English, Hinglish and Arabic)."""
import os, subprocess
MODEL = "text-multilingual-embedding-002"
DIM = 768

def _project():
    return (os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("DEVSHELL_PROJECT_ID")
            or subprocess.check_output(["gcloud", "config", "get-value", "project"], text=True).strip())

_clients = {}
def embed(texts, task="RETRIEVAL_DOCUMENT", location="asia-south1"):
    from google import genai
    from google.genai import types
    if location not in _clients:
        _clients[location] = genai.Client(vertexai=True, project=_project(), location=location)
    out = []
    for i in range(0, len(texts), 20):
        resp = _clients[location].models.embed_content(
            model=MODEL, contents=texts[i:i+20],
            config=types.EmbedContentConfig(task_type=task, output_dimensionality=DIM))
        out += [e.values for e in resp.embeddings]
    return out
