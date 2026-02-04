from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import yaml
from sentence_transformers import SentenceTransformer

CASES_DIR = Path("cases")
OUT_DIR = Path("rag/index")
IGNORE = {"_template.yaml"}

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


def is_case_file(p: Path) -> bool:
    return p.suffix in {".yaml", ".yml"} and p.name not in IGNORE


def load_case(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path}: YAML invalido")
    return data


def case_to_text(c: dict) -> str:
    # Texto que vai para o embedding. Campos mais relevantes para recall.
    parts: list[str] = []
    parts.append(f"id: {c.get('id','')}")
    parts.append(f"title: {c.get('title','')}")
    parts.append(f"problem_summary: {c.get('problem_summary','')}")
    symptoms = c.get("user_symptoms") or []
    if isinstance(symptoms, list) and symptoms:
        parts.append("user_symptoms: " + " | ".join([str(x) for x in symptoms]))
    steps = c.get("resolution_steps") or []
    if isinstance(steps, list) and steps:
        parts.append("resolution_steps: " + " | ".join([str(x) for x in steps]))
    causes = c.get("root_causes") or []
    if isinstance(causes, list) and causes:
        descs = []
        for rc in causes:
            if isinstance(rc, dict) and rc.get("description"):
                descs.append(str(rc["description"]))
        if descs:
            parts.append("root_causes: " + " | ".join(descs))
    origin = c.get("origin") or []
    layer = c.get("layer") or []
    parts.append("origin: " + " | ".join(origin if isinstance(origin, list) else [str(origin)]))
    parts.append("layer: " + " | ".join(layer if isinstance(layer, list) else [str(layer)]))
    return "\n".join(parts).strip()


def main() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    case_files = sorted([p for p in CASES_DIR.iterdir() if is_case_file(p)])
    cases = [load_case(p) for p in case_files]

    records = []
    texts = []
    for c in cases:
        txt = case_to_text(c)
        texts.append(txt)
        records.append(
            {
                "id": c.get("id"),
                "title": c.get("title"),
                "owner_team": c.get("owner_team"),
                "severity": c.get("severity"),
                "origin": c.get("origin"),
                "layer": c.get("layer"),
                "payload": c,
                "embedding_text": txt,
            }
        )

    model = SentenceTransformer(MODEL_NAME)
    embs = model.encode(texts, normalize_embeddings=True)

    (OUT_DIR / "cases.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n",
        encoding="utf-8",
    )
    np.save(OUT_DIR / "embeddings.npy", np.asarray(embs, dtype=np.float32))

    meta = {"model": MODEL_NAME, "count": len(records)}
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"OK: index gerado com {len(records)} casos em {OUT_DIR}")


if __name__ == "__main__":
    main()
