"""Run the safe offline publication-snapshot sample."""
from __future__ import annotations
import json
from pathlib import Path

def run_sample(output_dir: Path) -> Path:
    source = Path(__file__).parent / "sample-data" / "publications.json"
    data = json.loads(source.read_text(encoding="utf-8"))
    if data.get("schema_version") != "1.0": raise ValueError("unsupported public schema")
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / "publications.json"
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return target

if __name__ == "__main__": print(run_sample(Path("output")))
