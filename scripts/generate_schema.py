from __future__ import annotations

import json
from pathlib import Path

from garmin_optimizer.models import DesiredConfiguration


def main() -> None:
    schema = DesiredConfiguration.model_json_schema()
    schema["$schema"] = "https://json-schema.org/draft/2020-12/schema"
    schema["$id"] = (
        "https://github.com/mickpletcher/garmin-watch-optimizer/schemas/config.schema.json"
    )
    path = Path(__file__).resolve().parents[1] / "schemas" / "config.schema.json"
    path.write_text(json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
