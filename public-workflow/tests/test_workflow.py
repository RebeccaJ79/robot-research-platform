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


def test_online_mode_sends_the_user_key_to_their_configured_endpoint_only(tmp_path: Path, monkeypatch) -> None:
    from workflow import run

    source = tmp_path / "input.json"; source.write_text('{"period":"2026-09-15","items":[]}', encoding="utf-8")
    seen: dict[str, object] = {}

    class Response:
        def read(self) -> bytes:
            return b'{"choices":[{"message":{"content":"{\\\"schema_version\\\":\\\"1.0\\\",\\\"publications\\\":[],\\\"graph\\\":{\\\"nodes\\\":[],\\\"relations\\\":[]},\\\"cases\\\":[]}"}}]}'

        def __enter__(self):
            return self

        def __exit__(self, *_args: object) -> None:
            return None

    def fake_urlopen(request, timeout: int):
        seen["url"] = request.full_url
        seen["authorization"] = request.get_header("Authorization")
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setenv("MODEL_API_KEY", "user-owned-key")
    monkeypatch.setenv("MODEL_BASE_URL", "https://model.example/v1")
    monkeypatch.setattr("urllib.request.urlopen", fake_urlopen)

    target = run(source, tmp_path / "output.json", offline=False)

    assert seen == {"url": "https://model.example/v1/chat/completions", "authorization": "Bearer user-owned-key", "timeout": 60}
    assert json.loads(target.read_text(encoding="utf-8"))["schema_version"] == "1.0"
