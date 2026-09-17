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


def test_pipeline_reports_each_pdf_parse_progress(tmp_path: Path) -> None:
    from evidence_pipeline import build_evidence_bundle

    first, second = tmp_path / "first.pdf", tmp_path / "second.pdf"
    first.write_bytes(b"first")
    second.write_bytes(b"second")
    events: list[dict[str, object]] = []

    build_evidence_bundle(
        [first, second], tmp_path / "state",
        native_reader=lambda source: [source.stem],
        progress_callback=events.append,
    )

    assert events[0]["stage"] == "解析 PDF"
    assert events[0]["file_name"] == "first.pdf"
    assert events[-1] == {"stage": "证据完成", "file_name": "second.pdf", "completed_files": 2, "total_files": 2, "progress": 0.6}


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


def test_pipeline_requests_native_ocr_for_only_missing_pages(tmp_path: Path, monkeypatch) -> None:
    import evidence_pipeline

    source = tmp_path / "mixed.pdf"
    source.write_bytes(b"fixture")
    requested: list[int] = []

    def native_ocr(_path: Path, page_indexes: list[int] | None = None) -> dict[int, str]:
        requested.extend(page_indexes or [])
        return {1: " OCR\r\n第二页 "}

    monkeypatch.setattr(evidence_pipeline, "_read_ocr_pages", native_ocr)
    bundle = evidence_pipeline.build_evidence_bundle(
        [source], tmp_path / "state", native_reader=lambda _: ["原生第一页", ""]
    )

    assert requested == [1]
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


def test_model_request_repairs_an_invalid_evidence_quote(tmp_path: Path, monkeypatch) -> None:
    from evidence_pipeline import build_evidence_bundle
    from skill_cli import request_updates

    source = tmp_path / "report.pdf"
    source.write_bytes(b"fixture")
    bundle = build_evidence_bundle([source], tmp_path / "state", native_reader=lambda _: ["订单增长"])
    evidence_id = bundle.evidence[0]["evidence_id"]
    invalid = '{"choices":[{"message":{"content":"{\\"updates\\":[{\\"parent_id\\":\\"market-demand\\",\\"operations\\":[{\\"operation\\":\\"add_dimension\\",\\"dimension\\":{\\"id\\":\\"order-growth\\",\\"name\\":\\"订单增长\\"},\\"indicators\\":[],\\"rules\\":[],\\"research_models\\":[],\\"evidence\\":[{\\"evidence_id\\":\\"' + evidence_id + '\\",\\"quote\\":\\"不是原文\\"}]}]}]}"}}]}'
    corrected = '{"choices":[{"message":{"content":"{\\"updates\\":[{\\"parent_id\\":\\"market-demand\\",\\"operations\\":[{\\"operation\\":\\"add_dimension\\",\\"dimension\\":{\\"id\\":\\"order-growth\\",\\"name\\":\\"订单增长\\"},\\"indicators\\":[],\\"rules\\":[],\\"research_models\\":[],\\"evidence\\":[{\\"evidence_id\\":\\"' + evidence_id + '\\",\\"quote\\":\\"订单增长\\"}]}]}]}"}}]}'
    reviewed = '{"choices":[{"message":{"content":"{\\"approved\\":[true]}"}}]}'
    responses = [invalid, corrected, reviewed]

    class Response:
        def read(self) -> bytes: return responses.pop(0).encode()
        def __enter__(self): return self
        def __exit__(self, *_args): return None

    monkeypatch.setenv("MODEL_API_KEY", "user-key")
    monkeypatch.setattr("urllib.request.urlopen", lambda *_args, **_kwargs: Response())

    assert request_updates(bundle)[0]["operations"][0]["evidence"][0]["quote"] == "订单增长"
    assert responses == []


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


def test_model_request_retries_transient_transport_failures(monkeypatch) -> None:
    import skill_cli

    attempts = 0

    def flaky_request(*_args, **_kwargs):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise OSError("temporary network fault")
        return type("Response", (), {"read": lambda self: b'{"choices":[]}', "__enter__": lambda self: self, "__exit__": lambda self, *_args: None})()

    monkeypatch.setattr("urllib.request.urlopen", flaky_request)
    monkeypatch.setattr(skill_cli.time, "sleep", lambda _seconds: None)

    assert skill_cli._model_completion("https://model.example/v1", "key", {"model": "test"}) == {"choices": []}
    assert attempts == 3
