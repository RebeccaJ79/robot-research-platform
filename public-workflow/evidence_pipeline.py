"""Deterministic local PDF cleaning, page Markdown, and citable evidence."""

from __future__ import annotations

import hashlib
import io
import json
import re
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


PageReader = Callable[[Path], list[str]]


@dataclass(frozen=True)
class EvidenceBundle:
    documents: list[dict[str, object]]
    evidence: list[dict[str, object]]

    @property
    def evidence_ids(self) -> set[str]:
        return {str(item["evidence_id"]) for item in self.evidence}

    def model_payload(self) -> list[dict[str, object]]:
        return [{"evidence_id": item["evidence_id"], "page": item["page"], "text": item["text"]} for item in self.evidence]


def build_evidence_bundle(pdf_paths: list[Path], state_dir: Path, *, native_reader: PageReader | None = None, ocr_reader: PageReader | None = None, ocr_mode: str = "auto") -> EvidenceBundle:
    """Write reproducible local Markdown/evidence artifacts for caller-owned PDFs."""
    if ocr_mode not in {"auto", "off", "force"}:
        raise ValueError("OCR_MODE_INVALID")
    markdown_dir, evidence_dir = Path(state_dir) / "markdown", Path(state_dir) / "evidence"
    markdown_dir.mkdir(parents=True, exist_ok=True)
    evidence_dir.mkdir(parents=True, exist_ok=True)
    native_reader = native_reader or _read_native_pages
    documents: list[dict[str, object]] = []
    evidence: list[dict[str, object]] = []
    for source in pdf_paths:
        source = Path(source)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        native_pages = [] if ocr_mode == "force" else native_reader(source)
        pages = [_clean_page(page) for page in native_pages]
        needs_ocr = ocr_mode == "force" or not pages or any(not _meaningful(page) for page in pages)
        if needs_ocr:
            if ocr_mode == "off":
                raise ValueError("PDF_TEXT_EXTRACTION_EMPTY")
            reader = ocr_reader or _read_ocr_pages
            ocr_pages = [_clean_page(page) for page in reader(source)]
            if pages and len(ocr_pages) != len(pages):
                raise ValueError("OCR_PAGE_COUNT_MISMATCH")
            pages = ocr_pages if ocr_mode == "force" or not pages else [native if _meaningful(native) else ocr_pages[index] for index, native in enumerate(pages)]
            if not any(_meaningful(page) for page in pages):
                raise ValueError("OCR_TEXT_EXTRACTION_EMPTY")
            method = "ocr" if ocr_mode == "force" or not any(_meaningful(page) for page in native_pages) else "mixed"
        else:
            method = "native"
        markdown = _page_markdown(pages)
        (markdown_dir / f"{digest}.md").write_text(markdown, encoding="utf-8")
        document = {"sha256": digest, "page_count": len(pages), "extraction_method": method}
        documents.append(document)
        entries = _extract_evidence(digest, pages)
        evidence.extend(entries)
        (evidence_dir / f"{digest}.json").write_text(json.dumps({"document": document, "evidence": entries}, ensure_ascii=False, indent=2), encoding="utf-8")
    return EvidenceBundle(documents=documents, evidence=evidence)


def validate_evidence_backed_updates(updates: list[dict[str, object]], evidence: dict[str, str] | set[str]) -> None:
    """Require every model operation to cite local, extracted page evidence."""
    evidence_ids = set(evidence)
    evidence_text = evidence if isinstance(evidence, dict) else {}
    for update in updates:
        operations = update.get("operations") if isinstance(update, dict) else None
        if not isinstance(operations, list):
            raise ValueError("EVIDENCE_CITATION_REQUIRED")
        for operation in operations:
            citations = operation.get("evidence") if isinstance(operation, dict) else None
            if not isinstance(citations, list) or not citations or not all(isinstance(value, dict) for value in citations):
                raise ValueError("EVIDENCE_CITATION_REQUIRED")
            if not all(isinstance(value.get("evidence_id"), str) and isinstance(value.get("quote"), str) and value["quote"].strip() and len(value["quote"].strip()) <= 180 for value in citations):
                raise ValueError("EVIDENCE_CITATION_REQUIRED")
            if not {str(value["evidence_id"]) for value in citations} <= evidence_ids:
                raise ValueError("EVIDENCE_CITATION_UNKNOWN")
            if evidence_text and any(str(value["quote"]).strip() not in evidence_text[str(value["evidence_id"])] for value in citations):
                raise ValueError("EVIDENCE_QUOTE_INVALID")


def attach_evidence_locations(updates: list[dict[str, object]], bundle: EvidenceBundle) -> list[dict[str, object]]:
    """Validate citations and retain only a short quote plus page number in output."""
    evidence = {str(item["evidence_id"]): item for item in bundle.evidence}
    validate_evidence_backed_updates(updates, {key: str(value["text"]) for key, value in evidence.items()})
    for update in updates:
        for operation in update["operations"]:  # validated above
            operation["evidence"] = [
                {
                    "evidence_id": citation["evidence_id"],
                    "page": evidence[str(citation["evidence_id"])]["page"],
                    "quote": citation["quote"].strip(),
                }
                for citation in operation["evidence"]
            ]
    return updates


def _clean_page(value: str) -> str:
    text = unicodedata.normalize("NFKC", value or "").replace("\r\n", "\n").replace("\r", "\n")
    paragraphs = []
    for block in re.split(r"\n\s*\n+", text):
        lines = [re.sub(r"[ \t]+", " ", line).strip() for line in block.split("\n")]
        lines = [line for index, line in enumerate(lines) if line and (index == 0 or line != lines[index - 1])]
        if lines:
            paragraphs.append(" ".join(lines).replace("- ", ""))
    return "\n\n".join(dict.fromkeys(paragraphs))


def _page_markdown(pages: list[str]) -> str:
    return "\n\n".join(f"# 第 {index} 页\n\n{page}" for index, page in enumerate(pages, start=1)) + "\n"


def _extract_evidence(digest: str, pages: list[str]) -> list[dict[str, object]]:
    entries: list[dict[str, object]] = []
    for page_number, page in enumerate(pages, start=1):
        for paragraph_number, paragraph in enumerate(page.split("\n\n"), start=1):
            if not _meaningful(paragraph):
                continue
            fingerprint = hashlib.sha256(f"{digest}:{page_number}:{paragraph_number}:{paragraph}".encode("utf-8")).hexdigest()[:16]
            entries.append({"evidence_id": f"ev-{fingerprint}", "document_sha256": digest, "page": page_number, "text": paragraph})
    return entries


def _meaningful(text: str) -> bool:
    return any(character.isalnum() for character in text)


def _read_native_pages(pdf_path: Path) -> list[str]:
    try:
        from pypdf import PdfReader
    except ImportError as error:
        raise RuntimeError("PYPDF_REQUIRED") from error
    return [page.extract_text() or "" for page in PdfReader(str(pdf_path)).pages]


def _read_ocr_pages(pdf_path: Path) -> list[str]:
    try:
        import fitz
        import pytesseract
        from PIL import Image
    except ImportError as error:
        raise RuntimeError("OCR_DEPENDENCIES_REQUIRED") from error
    try:
        document = fitz.open(str(pdf_path))
        return [pytesseract.image_to_string(Image.open(io.BytesIO(page.get_pixmap(matrix=fitz.Matrix(2, 2)).pil_tobytes(format="PNG"))), lang="chi_sim+eng") for page in document]
    except pytesseract.TesseractNotFoundError as error:
        raise RuntimeError("TESSERACT_REQUIRED") from error
