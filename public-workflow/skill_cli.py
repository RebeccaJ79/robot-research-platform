"""Batch local PDFs into one incremental public Skill package ZIP."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any
from zipfile import ZIP_DEFLATED, ZipFile

from evidence_pipeline import EvidenceBundle, build_evidence_bundle, validate_evidence_backed_updates
from skill_package import apply_updates, initialize_state, validate_skill_tree


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


def request_updates(evidence: EvidenceBundle) -> list[dict[str, Any]]:
    """Ask only the caller-selected endpoint for public registry operations."""
    key = os.environ.get("MODEL_API_KEY")
    base = os.environ.get("MODEL_BASE_URL", "").rstrip("/")
    if not key:
        raise RuntimeError("MODEL_API_KEY_REQUIRED")
    if not base:
        raise RuntimeError("MODEL_BASE_URL_REQUIRED")
    request_body = {
        "model": os.environ.get("MODEL_NAME", "gpt-4o-mini"),
        "response_format": {"type": "json_object"},
        "messages": [{
            "role": "system",
            "content": "Return JSON only: {\"updates\":[...]}. Route robot-industry methods only to six fixed parents: market-demand, technology-product, supply-chain, commercialization, company-fundamentals, valuation-investment. Every operation must include a non-empty evidence_ids array containing only supplied evidence IDs. Never return credentials, local paths, PDF quotations, raw model reasoning, or a new parent ID.",
        }, {"role": "user", "content": json.dumps({"evidence": evidence.model_payload()}, ensure_ascii=False)}],
    }
    request = urllib.request.Request(
        f"{base}/chat/completions",
        data=json.dumps(request_body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = json.loads(response.read().decode("utf-8"))
    try:
        updates = json.loads(payload["choices"][0]["message"]["content"])["updates"]
    except (KeyError, IndexError, TypeError, json.JSONDecodeError) as error:
        raise RuntimeError("MODEL_OUTPUT_INVALID") from error
    if not isinstance(updates, list) or not all(isinstance(item, dict) for item in updates):
        raise RuntimeError("MODEL_OUTPUT_INVALID")
    validate_evidence_backed_updates(updates, evidence.evidence_ids)
    return updates


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
    bundle = build_evidence_bundle(args.pdf, args.state, ocr_mode=args.ocr)
    if args.offline_updates:
        payload = json.loads(args.offline_updates.read_text(encoding="utf-8"))
        updates = payload.get("updates") if isinstance(payload, dict) else None
        if not isinstance(updates, list) or not all(isinstance(item, dict) for item in updates):
            raise RuntimeError("OFFLINE_UPDATES_INVALID")
    else:
        updates = request_updates(bundle)
    # Evidence preparation above has already validated native extraction or local OCR.
    # Avoid a second native-only extraction that would reject a successfully OCRed PDF.
    print(run(args.pdf, args.state, args.output, updates, text_extractor=lambda _path: "prepared local evidence"))


if __name__ == "__main__":
    main()
