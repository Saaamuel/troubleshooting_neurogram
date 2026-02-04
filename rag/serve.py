from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sentence_transformers import SentenceTransformer

INDEX_DIR = Path("rag/index")
MODEL_NAME_FALLBACK = "sentence-transformers/all-MiniLM-L6-v2"

app = FastAPI(title="Troubleshooting RAG MVP")

# CORS para permitir o front local (python -m http.server 5500)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5500",
        "http://localhost:5500",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskInput(BaseModel):
    query: str = Field(..., min_length=1)
    top_k: int = Field(1, ge=1, le=10)  

def _safe_list(v: Any) -> list[Any]:
    if v is None:
        return []
    if isinstance(v, list):
        return v
    return [v]


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            items.append(json.loads(line))
    return items


def _load_index() -> tuple[list[dict[str, Any]], np.ndarray, dict[str, Any]]:
    cases_path = INDEX_DIR / "cases.jsonl"
    embs_path = INDEX_DIR / "embeddings.npy"
    meta_path = INDEX_DIR / "meta.json"

    if not cases_path.exists() or not embs_path.exists():
        raise RuntimeError(
            "Index não encontrado em rag/index. Rode: python rag/build_index.py"
        )

    records = _load_jsonl(cases_path)
    embs = np.load(embs_path)

    if embs.ndim != 2:
        raise ValueError(f"embeddings.npy inválido, ndim={embs.ndim}")

    if len(records) != embs.shape[0]:
        raise ValueError(
            f"cases.jsonl ({len(records)}) diferente de embeddings.npy ({embs.shape[0]})"
        )

    meta = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.exists() else {}
    return records, embs, meta


def cosine_topk(query_emb: np.ndarray, embs: np.ndarray, k: int) -> tuple[list[int], list[float]]:
    # embeddings normalizados => dot == cosine similarity
    scores = embs @ query_emb  # shape: (N,)
    idx = np.argsort(-scores)[:k]
    return idx.tolist(), scores[idx].astype(float).tolist()


# Carrega tudo 1 vez
records, embeddings, meta = _load_index()
model_name = meta.get("model") or MODEL_NAME_FALLBACK
model = SentenceTransformer(model_name)

print(f"OK: carregou {len(records)} casos do índice. Modelo: {model_name}")


@app.get("/health")
def health() -> dict[str, Any]:
    return {"ok": True, "cases": len(records), "model": model_name}


@app.post("/ask")
def ask(inp: AskInput) -> dict[str, Any]:
    q = inp.query.strip()
    if not q:
        return {"query": q, "top_k": inp.top_k, "matches": []}

    # embedding da query 
    q_emb = model.encode([q], normalize_embeddings=True)[0].astype(np.float32)

    k = max(1, min(int(inp.top_k), 10))
    idxs, scores = cosine_topk(q_emb, embeddings, k=k)

    # monta matches 
    matches: list[dict[str, Any]] = []
    for i, score in zip(idxs, scores):
        r = records[i]
        payload = r.get("payload") or {}

        matches.append(
            {
                "id": r.get("id"),
                "title": r.get("title"),
                "score": float(score),  # ajuda a debugar qualidade
                "origin": r.get("origin"),
                "layer": r.get("layer"),
                "owner_team": r.get("owner_team"),
                "severity": r.get("severity"),
                "problem_summary": payload.get("problem_summary"),
                "user_symptoms": _safe_list(payload.get("user_symptoms")),
                "root_causes": _safe_list(payload.get("root_causes")),
                "recommended_next": {
                    "triage_questions": _safe_list(payload.get("triage_questions")),
                    "evidence_to_collect": _safe_list(payload.get("evidence_to_collect")),
                    "resolution_steps": _safe_list(payload.get("resolution_steps")),
                },
            }
        )

    # FORÇAR sempre 1 resultado de resposta
    matches = matches[:1]

    return {"query": q, "top_k": 1, "matches": matches}
