"""Batch local PDFs into one incremental public Skill package ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from evidence_pipeline import EvidenceBundle, attach_evidence_locations, build_evidence_bundle, validate_evidence_backed_updates
from skill_package import apply_updates, initialize_state, load_skill_context, validate_skill_tree


def run(
    pdf_paths: list[Path],
    state_dir: Path,
    output_zip: Path,
    updates: list[dict[str, Any]],
    *,
    text_extractor: Callable[[Path], str] | None = None,
) -> Path:
    """Apply one batch and export the complete current Skill library as one ZIP."""
    if not pdf_paths:
        raise ValueError("PDF_REQUIRED")
    state_dir = Path(state_dir)
    output_zip = Path(output_zip)
    root = initialize_state(state_dir)
    processed_path = state_dir / "processed.json"
    processed = _read_processed(processed_path)
    fresh = [Path(path) for path in pdf_paths if _fingerprint(Path(path)) not in processed]
    if fresh:
        extractor = text_extractor or extract_pdf_text
        texts = [extractor(path) for path in fresh]
        if not all(text.strip() for text in texts):
            raise ValueError("PDF_TEXT_EXTRACTION_EMPTY")
        root = apply_updates(state_dir, updates)
        processed.update(_fingerprint(path) for path in fresh)
        _write_json(processed_path, {"pdf_sha256": sorted(processed)})
    validate_skill_tree(root)
    _write_zip(root, output_zip)
    return output_zip


def fresh_pdf_paths(pdf_paths: list[Path], state_dir: Path) -> list[Path]:
    """Avoid a model request when every supplied PDF is already incorporated."""
    processed = _read_processed(Path(state_dir) / "processed.json")
    return [Path(path) for path in pdf_paths if _fingerprint(Path(path)) not in processed]


def extract_pdf_text(pdf_path: Path) -> str:
    """Extract meaningful native text without uploading a caller's PDF."""
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("PYPDF_REQUIRED") from error
    reader = PdfReader(str(pdf_path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(
        f"<!-- PAGE_START: {index} -->\n{page.strip()}\n<!-- PAGE_END: {index} -->"
        for index, page in enumerate(pages, start=1)
    )
    if not any(character.isalnum() for character in text):
        raise ValueError("PDF_TEXT_EXTRACTION_EMPTY")
    return text


def request_updates(evidence: EvidenceBundle, current_context: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """Ask only the caller-selected endpoint for public registry operations."""
    key = os.environ.get("MODEL_API_KEY") or os.environ.get("DEEPSEEK_API_KEY")
    base = (os.environ.get("MODEL_BASE_URL") or os.environ.get("DEEPSEEK_BASE_URL") or "https://api.deepseek.com/v1").rstrip("/")
    if not key:
        raise RuntimeError("MODEL_API_KEY_REQUIRED")
    if not base:
        raise RuntimeError("MODEL_BASE_URL_REQUIRED")
    correction = ""
    for attempt in range(3):
        request_body = {
            "model": os.environ.get("MODEL_NAME") or os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat",
            "response_format": {"type": "json_object"},
            "messages": [{
                "role": "system",
                "content": "Return JSON only: {\"updates\":[...]}. Route robot-industry methods only to six fixed parents: market-demand, technology-product, supply-chain, commercialization, company-fundamentals, valuation-investment. Each update is {parent_id, operations}. operation MUST be exactly one of add_dimension, replace_dimension, add_indicator, add_rule, replace_rule, add_research_model, replace_indicator, replace_research_model, add_alias, merge_dimension, deprecate_dimension. For a new method use add_dimension with dimension:{id,name}, indicators:[], rules:[], research_models:[]; for a later addition use add_indicator with dimension_id and indicator:{id,name}. Do not invent operation names, wrapper fields, parent IDs, IDs not present in current_skill_context, or existing children. Every operation must include a non-empty evidence array of {evidence_id, quote}; quote must be an exact short substring of that evidence (max 180 characters). Never return credentials, local paths, long PDF quotations, raw model reasoning, or a new parent ID.",
            }, {"role": "user", "content": json.dumps({"evidence": evidence.model_payload(), "current_skill_context": current_context or [], "correction": correction}, ensure_ascii=False)}],
        }
        payload = _model_completion(base, key, request_body)
        try:
            updates = json.loads(payload["choices"][0]["message"]["content"])["updates"]
        except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
            raise RuntimeError("MODEL_OUTPUT_INVALID") from error
        if not isinstance(updates, list) or not all(isinstance(item, dict) for item in updates):
            raise RuntimeError("MODEL_OUTPUT_INVALID")
        try:
            validated = attach_evidence_locations(updates, evidence)
        except ValueError as error:
            if str(error) not in {"EVIDENCE_CITATION_REQUIRED", "EVIDENCE_CITATION_UNKNOWN", "EVIDENCE_QUOTE_INVALID"} or attempt == 2:
                raise
            correction = f"Previous output was rejected with {error}. Return a complete replacement JSON. Each quote must be copied exactly from the cited evidence text."
            continue
        review_updates(validated, evidence, base=base, key=key)
        return validated
    raise RuntimeError("MODEL_OUTPUT_INVALID")


def review_updates(updates: list[dict[str, Any]], evidence: EvidenceBundle, *, base: str, key: str) -> None:
    """Reject model changes that a second evidence-focused review cannot support."""
    operations = [operation for update in updates for operation in update["operations"]]
    review_body = {
        "model": os.environ.get("MODEL_NAME") or os.environ.get("DEEPSEEK_MODEL") or "deepseek-chat",
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "system",
            "content": "You are a strict evidence reviewer. Return JSON only: {\"approved\":[true,...]}. There must be exactly one boolean per supplied operation. Approve only if its short cited quote directly supports the proposed method update; reject speculation, a quote that does not support the operation, or a change outside the six fixed robot-industry parents.",
        }, {
            "role": "user",
            "content": json.dumps({"operations": operations, "evidence": evidence.model_payload()}, ensure_ascii=False),
        }],
    }
    payload = _model_completion(base, key, review_body)
    try:
        approved = json.loads(payload["choices"][0]["message"]["content"])["approved"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("MODEL_REVIEW_INVALID") from error
    if not isinstance(approved, list) or len(approved) != len(operations) or not all(isinstance(value, bool) for value in approved):
        raise RuntimeError("MODEL_REVIEW_INVALID")
    if not all(approved):
        raise RuntimeError("MODEL_SEMANTIC_REVIEW_REJECTED")


def _model_completion(base: str, key: str, body: dict[str, Any], *, attempts: int = 3) -> dict[str, Any]:
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    for attempt in range(attempts):
        try:
            with urllib.request.urlopen(request, timeout=60) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except (OSError, json.JSONDecodeError) as error:
            if attempt == attempts - 1:
                raise RuntimeError("MODEL_REQUEST_FAILED") from error
            time.sleep(2**attempt)
            continue
        if not isinstance(payload, dict):
            raise RuntimeError("MODEL_OUTPUT_INVALID")
        return payload
    raise RuntimeError("MODEL_REQUEST_FAILED")


def _fingerprint(path: Path) -> str:
    if not path.is_file():
        raise ValueError(f"PDF_MISSING: {path.name}")
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_processed(path: Path) -> set[str]:
    if not path.exists():
        return set()
    try:
        values = json.loads(path.read_text(encoding="utf-8")).get("pdf_sha256", [])
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("STATE_INVALID") from error
    if not isinstance(values, list) or not all(isinstance(value, str) for value in values):
        raise ValueError("STATE_INVALID")
    return set(values)


def _write_zip(root: Path, output_zip: Path) -> None:
    output_zip.parent.mkdir(parents=True, exist_ok=True)
    temporary = output_zip.with_name(output_zip.name + ".tmp")
    with ZipFile(temporary, "w", ZIP_DEFLATED) as archive:
        for path in sorted((root / "skills").rglob("*")):
            if path.is_file():
                archive.write(path, path.relative_to(root))
    os.replace(temporary, output_zip)


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)


def main() -> None:
    parser = argparse.ArgumentParser(description="Build one incremental public Skill package from local PDFs.")
    parser.add_argument("--pdf", action="append", required=True, type=Path)
    parser.add_argument("--state", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--offline-updates", type=Path)
    parser.add_argument("--ocr", choices=("auto", "off", "force"), default="auto")
    args = parser.parse_args()
    fresh = fresh_pdf_paths(args.pdf, args.state)
    bundle = build_evidence_bundle(fresh, args.state, ocr_mode=args.ocr) if fresh else EvidenceBundle(documents=[], evidence=[])
    if args.offline_updates:
        payload = json.loads(args.offline_updates.read_text(encoding="utf-8"))
        updates = payload.get("updates") if isinstance(payload, dict) else None
        if not isinstance(updates, list) or not all(isinstance(item, dict) for item in updates):
            raise RuntimeError("OFFLINE_UPDATES_INVALID")
    else:
        updates = request_updates(bundle, load_skill_context(args.state)) if fresh else []
    # Evidence preparation above has already validated native extraction or local OCR.
    # Avoid a second native-only extraction that would reject a successfully OCRed PDF.
    print(run(args.pdf, args.state, args.output, updates, text_extractor=lambda _path: "prepared local evidence"))


if __name__ == "__main__":
    main()
