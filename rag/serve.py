from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

INDEX_DIR = Path("rag/index")
MODEL_NAME_FALLBACK = "sentence-transformers/all-MiniLM-L6-v2"

app = FastAPI(title="Troubleshooting RAG MVP")


class AskInput(BaseModel):
    query: str
    top_k: int = 5


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def cosine_topk(query_emb: np.ndarray, embs: np.ndarray, k: int) -> list[int]:
    scores = embs @ query_emb  # embeddings normalizados => dot = cosine
    idx = np.argsort(-scores)[:k]
    return idx.tolist()


@app.on_event("startup")
def startup() -> None:
    meta_path = INDEX_DIR / "meta.json"
    model_name = MODEL_NAME_FALLBACK
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        model_name = meta.get("model") or model_name

    app.state.model = SentenceTransformer(model_name)
    app.state.records = load_jsonl(INDEX_DIR / "cases.jsonl")
    app.state.embs = np.load(INDEX_DIR / "embeddings.npy")
    print(f"OK: carregou {len(app.state.records)} casos do indice")


@app.post("/ask")
def ask(inp: AskInput) -> dict[str, Any]:
    q = inp.query.strip()
    if not q:
        return {"error": "query vazia"}

    model: SentenceTransformer = app.state.model
    embs: np.ndarray = app.state.embs
    records: list[dict[str, Any]] = app.state.records

    q_emb = model.encode([q], normalize_embeddings=True)[0].astype(np.float32)
    idxs = cosine_topk(q_emb, embs, k=max(1, min(inp.top_k, 10)))

    matches = []
    for i in idxs:
        r = records[i]
        payload = r["payload"]
        matches.append(
            {
                "id": r["id"],
                "title": r["title"],
                "origin": r.get("origin"),
                "layer": r.get("layer"),
                "owner_team": r.get("owner_team"),
                "severity": r.get("severity"),
                "problem_summary": payload.get("problem_summary"),
                "user_symptoms": payload.get("user_symptoms") or [],
                "root_causes": payload.get("root_causes") or [],
                "recommended_next": {
                    "triage_questions": payload.get("triage_questions") or [],
                    "evidence_to_collect": payload.get("evidence_to_collect") or [],
                    "resolution_steps": payload.get("resolution_steps") or [],
                },
            }
        )

    return {"query": q, "top_k": inp.top_k, "matches": matches}
