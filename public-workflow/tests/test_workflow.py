from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parents[1]))


def test_offline_mode_creates_a_public_snapshot_without_a_key(tmp_path: Path, monkeypatch) -> None:
    from workflow import run

    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    source = tmp_path / "input.json"
    source.write_text(json.dumps({"period": "2026-09-15", "items": [{"title": "样例事件", "summary": "公开输入"}]}, ensure_ascii=False), encoding="utf-8")

    target = run(source, tmp_path / "output.json", offline=True)

    payload = json.loads(target.read_text(encoding="utf-8"))
    assert payload["schema_version"] == "1.0"
    assert payload["publications"][0]["type"] == "daily"


def test_online_mode_requires_a_user_supplied_key(tmp_path: Path, monkeypatch) -> None:
    from workflow import run

    monkeypatch.delenv("MODEL_API_KEY", raising=False)
    source = tmp_path / "input.json"; source.write_text('{"period":"2026-09-15","items":[]}', encoding="utf-8")

    try:
        run(source, tmp_path / "output.json", offline=False)
    except RuntimeError as error:
        assert str(error) == "MODEL_API_KEY_REQUIRED"
    else:
        raise AssertionError("online execution accepted no user key")
