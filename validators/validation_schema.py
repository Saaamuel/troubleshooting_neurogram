from pathlib import Path
import yaml, json
from jsonschema import validate


def load_taxonomy(path: str) -> set:
    return set(
        yaml.safe_load(Path(path).read_text())["values"]
    )


def assert_in_taxonomy(values, allowed, field, case_id):
    for v in values:
        if v not in allowed:
            raise ValueError(
                f"[{case_id}] valor inválido em '{field}': {v}"
            )


schema = json.loads(
    Path("validators/case_schema.json").read_text()
)

origin_values = load_taxonomy("taxonomy/origin.yaml")
layer_values = load_taxonomy("taxonomy/layer.yaml")
owner_team_values = load_taxonomy("taxonomy/owner_team.yaml")

cases = Path("cases").glob("*.yaml")

for case_file in cases:
    data = yaml.safe_load(case_file.read_text())

    # Validação estrutural
    validate(instance=data, schema=schema)

    # Validação semântica
    case_id = data["id"]

    assert_in_taxonomy(data["origin"], origin_values, "origin", case_id)
    assert_in_taxonomy(data["layer"], layer_values, "layer", case_id)
    assert_in_taxonomy(data["owner_team"], owner_team_values, "owner_team", case_id)

print("OK: todos os casos são válidos")

