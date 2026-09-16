import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parents[1]))
from run_sample import run_sample

def test_sample_runs_without_model_key(tmp_path, monkeypatch):
    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    assert json.loads(run_sample(tmp_path).read_text(encoding="utf-8"))["schema_version"] == "1.0"
