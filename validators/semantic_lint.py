from __future__ import annotations

from pathlib import Path
import re
import sys
import yaml

CASES_DIR = Path("cases")

# Arquivos que não são casos reais
IGNORE_FILES = {"_template.yaml"}

# ---------- Regras ----------
MIN_TITLE_LEN = 8
MIN_SUMMARY_LEN = 60
MIN_SYMPTOMS = 3
MIN_STEP_LEN = 8

# Palavras vagas (heurística)
VAGUE_TITLES = {
    "problema",
    "erro",
    "bug",
    "não funciona",
    "nao funciona",
    "ajuda",
    "issue",
}

VAGUE_SUMMARY_PATTERNS = [
    r"\b(algo|alguma coisa|coisa)\b",
    r"\b(nao sei|não sei)\b",
    r"\b(acho que|talvez)\b",
]

def load_yaml(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))

def is_case_file(path: Path) -> bool:
    return path.suffix in {".yml", ".yaml"} and path.name not in IGNORE_FILES

def norm(s: str) -> str:
    return re.sub(r"\s+", " ", s.strip().lower())

def lint_case(case_path: Path, data: dict) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    case_id = data.get("id", case_path.stem)

    # ---- Hard rules (quebram CI) ----
    title = data.get("title", "")
    if not isinstance(title, str) or len(title.strip()) < MIN_TITLE_LEN:
        errors.append(f"{case_id}: title muito curto (min {MIN_TITLE_LEN})")

    summary = data.get("problem_summary", "")
    if not isinstance(summary, str) or len(summary.strip()) < MIN_SUMMARY_LEN:
        errors.append(f"{case_id}: problem_summary muito curto (min {MIN_SUMMARY_LEN})")

    symptoms = data.get("user_symptoms", [])
    if not isinstance(symptoms, list) or len(symptoms) < MIN_SYMPTOMS:
        errors.append(f"{case_id}: user_symptoms precisa ter pelo menos {MIN_SYMPTOMS} itens")

    # Se tiver resolution_steps, validar qualidade mínima
    steps = data.get("resolution_steps")
    if steps is not None:
        if not isinstance(steps, list) or len(steps) == 0:
            errors.append(f"{case_id}: resolution_steps existe mas está vazio")
        else:
            short_steps = [s for s in steps if isinstance(s, str) and len(s.strip()) < MIN_STEP_LEN]
            if short_steps:
                errors.append(f"{case_id}: resolution_steps tem passos curtos demais (min {MIN_STEP_LEN} chars)")

    # ---- Soft rules (warnings) ----
    tnorm = norm(title) if isinstance(title, str) else ""
    if any(v in tnorm for v in VAGUE_TITLES):
        warnings.append(f"{case_id}: title possivelmente vago (evite 'problema', 'erro', 'não funciona')")

    snorm = norm(summary) if isinstance(summary, str) else ""
    for pat in VAGUE_SUMMARY_PATTERNS:
        if re.search(pat, snorm):
            warnings.append(f"{case_id}: problem_summary contém linguagem vaga (ex: 'acho que', 'talvez')")

    # Sintomas duplicados (muito comum)
    if isinstance(symptoms, list):
        normalized = [norm(s) for s in symptoms if isinstance(s, str)]
        if len(set(normalized)) != len(normalized):
            warnings.append(f"{case_id}: user_symptoms contém itens duplicados ou muito parecidos")

    # Recomendar triage_questions quando severity alta
    sev = data.get("severity", {})
    if isinstance(sev, dict) and sev.get("user_impact") == "alta":
        if not data.get("triage_questions"):
            warnings.append(f"{case_id}: user_impact=alta sem triage_questions (recomendado adicionar 2-5)")

    return errors, warnings

def main() -> int:
    if not CASES_DIR.exists():
        print("Diretório 'cases/' não encontrado.")
        return 2

    case_files = sorted([p for p in CASES_DIR.iterdir() if is_case_file(p)])
    if not case_files:
        print("Nenhum caso encontrado em cases/.")
        return 2

    all_errors: list[str] = []
    all_warnings: list[str] = []

    for path in case_files:
        data = load_yaml(path)
        if not isinstance(data, dict):
            all_errors.append(f"{path.name}: YAML inválido (não é um objeto)")
            continue

        errors, warnings = lint_case(path, data)
        all_errors.extend([f"{path.name}: {e}" for e in errors])
        all_warnings.extend([f"{path.name}: {w}" for w in warnings])

    # Print warnings (não falham)
    if all_warnings:
        print("\nWARNINGS (melhorias recomendadas):")
        for w in all_warnings:
            print(f"  - {w}")

    # Print errors (falham)
    if all_errors:
        print("\nERRORS (quebram o CI):")
        for e in all_errors:
            print(f"  - {e}")
        return 1

    print("OK: semantic lint passou")
    return 0

if __name__ == "__main__":
    sys.exit(main())
