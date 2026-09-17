from __future__ import annotations

import sys
from pathlib import Path

import pytest


sys.path.insert(0, str(Path(__file__).parents[1]))


def test_pipeline_writes_normalized_page_markdown_and_evidence(tmp_path: Path) -> None:
    from evidence_pipeline import build_evidence_bundle

    source = tmp_path / "report.pdf"
    source.write_bytes(b"fixture")
    bundle = build_evidence_bundle(
        [source], tmp_path / "state", native_reader=lambda _: ["  机器人\r\n市场\u3000需求  ", "订单增长。订单增长。"]
    )

    markdown = (tmp_path / "state" / "markdown" / f"{bundle.documents[0]['sha256']}.md").read_text(encoding="utf-8")
    assert "# 第 1 页" in markdown and "机器人 市场 需求" in markdown
    assert "\r" not in markdown
    assert bundle.evidence[0]["page"] == 1
    assert bundle.evidence[0]["evidence_id"].startswith("ev-")
    assert {item["page"] for item in bundle.evidence} == {1, 2}


def test_pipeline_uses_local_ocr_when_native_text_is_empty(tmp_path: Path) -> None:
    from evidence_pipeline import build_evidence_bundle

    source = tmp_path / "scanned.pdf"
    source.write_bytes(b"fixture")
    bundle = build_evidence_bundle(
        [source], tmp_path / "state", native_reader=lambda _: [""], ocr_reader=lambda _: ["扫描件文字"], ocr_mode="auto"
    )

    assert bundle.documents[0]["extraction_method"] == "ocr"
    assert bundle.evidence[0]["text"] == "扫描件文字"


def test_evidence_validation_rejects_uncited_or_unknown_operations() -> None:
    from evidence_pipeline import validate_evidence_backed_updates

    valid = [{"parent_id": "market-demand", "operations": [{"operation": "add_dimension", "evidence_ids": ["ev-a"]}]}]
    validate_evidence_backed_updates(valid, {"ev-a"})
    with pytest.raises(ValueError, match="EVIDENCE_CITATION_REQUIRED"):
        validate_evidence_backed_updates([{"parent_id": "market-demand", "operations": [{"operation": "add_dimension"}]}], {"ev-a"})
    with pytest.raises(ValueError, match="EVIDENCE_CITATION_UNKNOWN"):
        validate_evidence_backed_updates([{"parent_id": "market-demand", "operations": [{"operation": "add_dimension", "evidence_ids": ["ev-missing"]}]}], {"ev-a"})


def test_model_request_accepts_only_cited_updates(tmp_path: Path, monkeypatch) -> None:
    from evidence_pipeline import build_evidence_bundle
    from skill_cli import request_updates

    source = tmp_path / "report.pdf"
    source.write_bytes(b"fixture")
    bundle = build_evidence_bundle([source], tmp_path / "state", native_reader=lambda _: ["订单增长"])
    evidence_id = bundle.evidence[0]["evidence_id"]

    class Response:
        def read(self) -> bytes:
            return ('{"choices":[{"message":{"content":"{\\"updates\\":[{\\"parent_id\\":\\"market-demand\\",\\"operations\\":[{\\"operation\\":\\"add_dimension\\",\\"evidence_ids\\":[\\"' + evidence_id + '\\"]}]}]}"}}]}').encode()
        def __enter__(self): return self
        def __exit__(self, *_args): return None

    monkeypatch.setenv("MODEL_API_KEY", "user-key")
    monkeypatch.setenv("MODEL_BASE_URL", "https://model.example/v1")
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response())
    assert request_updates(bundle)[0]["operations"][0]["evidence_ids"] == [evidence_id]
