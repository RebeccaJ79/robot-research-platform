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


def test_pipeline_uses_ocr_for_only_empty_pages(tmp_path: Path) -> None:
    from evidence_pipeline import build_evidence_bundle

    source = tmp_path / "mixed.pdf"
    source.write_bytes(b"fixture")
    bundle = build_evidence_bundle(
        [source], tmp_path / "state", native_reader=lambda _: ["原生第一页", ""], ocr_reader=lambda _: ["OCR 第一页", "OCR 第二页"]
    )

    assert bundle.documents[0]["extraction_method"] == "mixed"
    assert [item["text"] for item in bundle.evidence] == ["原生第一页", "OCR 第二页"]


def test_evidence_validation_rejects_uncited_or_unknown_operations() -> None:
    from evidence_pipeline import validate_evidence_backed_updates

    valid = [{"parent_id": "market-demand", "operations": [{"operation": "add_dimension", "evidence": [{"evidence_id": "ev-a", "quote": "订单增长"}]}]}]
    validate_evidence_backed_updates(valid, {"ev-a": "订单增长"})
    with pytest.raises(ValueError, match="EVIDENCE_CITATION_REQUIRED"):
        validate_evidence_backed_updates([{"parent_id": "market-demand", "operations": [{"operation": "add_dimension"}]}], {"ev-a": "订单增长"})
    with pytest.raises(ValueError, match="EVIDENCE_CITATION_UNKNOWN"):
        validate_evidence_backed_updates([{"parent_id": "market-demand", "operations": [{"operation": "add_dimension", "evidence": [{"evidence_id": "ev-missing", "quote": "订单"}]}]}], {"ev-a": "订单增长"})
    with pytest.raises(ValueError, match="EVIDENCE_QUOTE_INVALID"):
        validate_evidence_backed_updates([{"parent_id": "market-demand", "operations": [{"operation": "add_dimension", "evidence": [{"evidence_id": "ev-a", "quote": "无关结论"}]}]}], {"ev-a": "订单增长"})
    with pytest.raises(ValueError, match="EVIDENCE_CITATION_REQUIRED"):
        validate_evidence_backed_updates([{"parent_id": "market-demand", "operations": [{"operation": "add_dimension", "evidence": [{"evidence_id": "ev-a", "quote": "长" * 181}]}]}], {"ev-a": "长" * 181})


def test_model_request_accepts_only_cited_updates(tmp_path: Path, monkeypatch) -> None:
    from evidence_pipeline import build_evidence_bundle
    from skill_cli import request_updates, run

    source = tmp_path / "report.pdf"
    source.write_bytes(b"fixture")
    bundle = build_evidence_bundle([source], tmp_path / "state", native_reader=lambda _: ["订单增长"])
    evidence_id = bundle.evidence[0]["evidence_id"]

    responses = [
        '{"choices":[{"message":{"content":"{\\"updates\\":[{\\"parent_id\\":\\"market-demand\\",\\"operations\\":[{\\"operation\\":\\"add_dimension\\",\\"dimension\\":{\\"id\\":\\"order-growth\\",\\"name\\":\\"订单增长\\"},\\"indicators\\":[],\\"rules\\":[],\\"research_models\\":[],\\"evidence\\":[{\\"evidence_id\\":\\"' + evidence_id + '\\",\\"quote\\":\\"订单增长\\"}]}]}]}"}}]}',
        '{"choices":[{"message":{"content":"{\\"approved\\":[true]}"}}]}',
    ]

    class Response:
        def __init__(self, body: str) -> None:
            self.body = body
        def read(self) -> bytes:
            return self.body.encode()
        def __enter__(self): return self
        def __exit__(self, *_args): return None

    monkeypatch.setenv("MODEL_API_KEY", "user-key")
    monkeypatch.setenv("MODEL_BASE_URL", "https://model.example/v1")
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response(responses.pop(0)))
    citation = request_updates(bundle)[0]["operations"][0]["evidence"][0]
    assert citation == {"evidence_id": evidence_id, "page": 1, "quote": "订单增长"}

    updates = [{"parent_id": "market-demand", "operations": [{
        "operation": "add_dimension", "dimension": {"id": "order-growth", "name": "订单增长"},
        "indicators": [], "rules": [], "research_models": [], "evidence": [citation],
    }]}]
    target = run([source], tmp_path / "package-state", tmp_path / "skill-package.zip", updates, text_extractor=lambda _: "prepared")
    assert target.is_file()


def test_model_review_rejects_unsupported_operation(tmp_path: Path, monkeypatch) -> None:
    from evidence_pipeline import build_evidence_bundle
    from skill_cli import request_updates

    source = tmp_path / "report.pdf"
    source.write_bytes(b"fixture")
    bundle = build_evidence_bundle([source], tmp_path / "state", native_reader=lambda _: ["订单增长"])
    evidence_id = bundle.evidence[0]["evidence_id"]
    responses = [
        '{"choices":[{"message":{"content":"{\\"updates\\":[{\\"parent_id\\":\\"market-demand\\",\\"operations\\":[{\\"operation\\":\\"add_dimension\\",\\"dimension\\":{\\"id\\":\\"order-growth\\",\\"name\\":\\"订单增长\\"},\\"indicators\\":[],\\"rules\\":[],\\"research_models\\":[],\\"evidence\\":[{\\"evidence_id\\":\\"' + evidence_id + '\\",\\"quote\\":\\"订单增长\\"}]}]}]}"}}]}',
        '{"choices":[{"message":{"content":"{\\"approved\\":[false]}"}}]}',
    ]

    class Response:
        def read(self) -> bytes: return responses.pop(0).encode()
        def __enter__(self): return self
        def __exit__(self, *_args): return None

    monkeypatch.setenv("DEEPSEEK_API_KEY", "user-key")
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response())
    with pytest.raises(RuntimeError, match="MODEL_SEMANTIC_REVIEW_REJECTED"):
        request_updates(bundle)
