"""Public, local-only state and validation for six-parent research Skill packages."""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any


PARENTS = {
    "market-demand": "市场需求与应用空间",
    "technology-product": "技术路线与产品能力",
    "supply-chain": "产业链与供给能力",
    "commercialization": "商业化落地与量产进程",
    "company-fundamentals": "竞争格局与公司基本面",
    "valuation-investment": "估值与投资判断",
}
REFERENCE_FILES = (
    "child-dimensions.yaml",
    "research-model.yaml",
    "indicator-catalog.yaml",
    "analysis-rules.yaml",
    "source-traceability.yaml",
)
_PRIVATE_PIPELINE_NAME = "robot_" + "evidence_pipeline"
_PRIVATE_OUTPUT_NAME = "hermes_skill_" + "output"
_FORBIDDEN_PUBLIC_TEXT = re.compile(
    r"(?i)(?:api[_-]?key|authorization\s*:|bearer\s+\S+|sk-[a-z0-9]|[a-z]:[\\/][^\s]+|"
    + re.escape(_PRIVATE_PIPELINE_NAME)
    + r")"
)


def initialize_state(state_dir: Path) -> Path:
    """Create and return a blank local package state without inventing methods."""
    root = Path(state_dir) / "current"
    (root / "skills").mkdir(parents=True, exist_ok=True)
    return root


def load_skill_context(state_dir: Path) -> list[dict[str, Any]]:
    """Return the current local method registry for an incremental model update."""
    root = initialize_state(state_dir)
    context: list[dict[str, Any]] = []
    for package in sorted((root / "skills").iterdir()):
        if package.is_dir():
            contract = _read_json(package / "contract.json")
            registry = _load_registry(package)
            context.append({"parent_id": contract["parent_id"], "children": registry["children"], "indicators": registry["indicators"], "rules": registry["rules"], "research_models": registry["research_models"]})
    return context


def apply_updates(state_dir: Path, updates: list[dict[str, Any]]) -> Path:
    """Apply validated updates to a candidate and only then promote it to current."""
    state_dir = Path(state_dir)
    root = initialize_state(state_dir)
    for update in updates:
        parent_id = update.get("parent_id") if isinstance(update, dict) else None
        if parent_id not in PARENTS:
            raise ValueError("PARENT_UNKNOWN")
        if not isinstance(update.get("operations"), list):
            raise ValueError("OPERATION_INVALID")
        _assert_public_content(update)
    if not any(update["operations"] for update in updates):
        return root

    candidate = state_dir / ".candidate"
    if candidate.exists():
        shutil.rmtree(candidate)
    shutil.copytree(root, candidate)
    try:
        for update in updates:
            _apply_parent_updates(candidate, str(update["parent_id"]), update["operations"])
        validate_skill_tree(candidate)
        _record_version(state_dir, candidate)
        backup = state_dir / ".previous-current"
        if backup.exists():
            shutil.rmtree(backup)
        os.replace(root, backup)
        os.replace(candidate, root)
        shutil.rmtree(backup)
    except Exception:
        if candidate.exists():
            shutil.rmtree(candidate)
        raise
    return root


def validate_skill_tree(root: Path) -> None:
    """Require every emitted package to be self-contained and fixed-parent based."""
    skills = Path(root) / "skills"
    if not skills.is_dir():
        raise ValueError("SKILL_TREE_INVALID")
    seen_ids: set[str] = set()
    for package in skills.iterdir():
        if not package.is_dir():
            raise ValueError("SKILL_TREE_INVALID")
        contract = _read_json(package / "contract.json")
        parent_id = contract.get("parent_id")
        if parent_id not in PARENTS or package.name != PARENTS[parent_id]:
            raise ValueError("PARENT_UNKNOWN")
        skill_id = contract.get("skill_id")
        if not isinstance(skill_id, str) or not skill_id or skill_id in seen_ids:
            raise ValueError("SKILL_TREE_INVALID")
        seen_ids.add(skill_id)
        if contract.get("references") != list(REFERENCE_FILES):
            raise ValueError("SKILL_TREE_INVALID")
        text = (package / "SKILL.md").read_text(encoding="utf-8")
        if not text.startswith("---\nname:") or "description:" not in text.split("---", 2)[1]:
            raise ValueError("SKILL_TREE_INVALID")
        for reference in REFERENCE_FILES:
            value = _read_json(package / "references" / reference)
            if not isinstance(value, dict):
                raise ValueError("SKILL_TREE_INVALID")


def _apply_parent_updates(root: Path, parent_id: str, operations: list[dict[str, Any]]) -> None:
    if not operations:
        return
    package = root / "skills" / PARENTS[parent_id]
    if not package.exists():
        _write_parent_package(package, parent_id)
    registry = _load_registry(package)
    for operation in operations:
        _apply_operation(registry, operation)
    _write_registry(package, registry)


def _write_parent_package(package: Path, parent_id: str) -> None:
    references = package / "references"
    references.mkdir(parents=True)
    display_name = PARENTS[parent_id]
    _write_json(package / "contract.json", {
        "schema_version": "2.0",
        "parent_id": parent_id,
        "skill_id": f"robot-{parent_id}",
        "package_name": display_name,
        "display_name": display_name,
        "version": "0.1.0",
        "child_dimension_ids": [],
        "indicator_ids": [],
        "decision_rule_ids": [],
        "references": list(REFERENCE_FILES),
        "shared_report_formats": [],
    })
    (package / "SKILL.md").write_text(
        f"---\nname: robot-{parent_id}\ndescription: 机器人行业{display_name}的可复用研究方法。\n---\n\n"
        f"# {display_name}\n\n使用 `references/` 中已校验的子维度、指标、规则和研究模型。\n",
        encoding="utf-8",
    )
    _write_registry(package, _empty_registry())


def _empty_registry() -> dict[str, list[dict[str, Any]]]:
    return {"children": [], "indicators": [], "rules": [], "research_models": [], "aliases": [], "deprecated": [], "fact_lineage": []}


def _load_registry(package: Path) -> dict[str, list[dict[str, Any]]]:
    references = package / "references"
    values = {
        "children": _read_json(references / "child-dimensions.yaml").get("children", []),
        "indicators": _read_json(references / "indicator-catalog.yaml").get("indicators", []),
        "rules": _read_json(references / "analysis-rules.yaml").get("analysis_rules", []),
        "research_models": _read_json(references / "research-model.yaml").get("research_models", []),
        "aliases": _read_json(references / "source-traceability.yaml").get("aliases", []),
        "deprecated": _read_json(references / "source-traceability.yaml").get("deprecated", []),
        "fact_lineage": _read_json(references / "source-traceability.yaml").get("fact_lineage", []),
    }
    if not all(isinstance(value, list) and all(isinstance(item, dict) for item in value) for value in values.values()):
        raise ValueError("SKILL_TREE_INVALID")
    return values


def _write_registry(package: Path, registry: dict[str, list[dict[str, Any]]]) -> None:
    references = package / "references"
    _write_json(references / "child-dimensions.yaml", {"children": registry["children"]})
    _write_json(references / "indicator-catalog.yaml", {"indicators": registry["indicators"]})
    _write_json(references / "analysis-rules.yaml", {"analysis_rules": registry["rules"]})
    _write_json(references / "research-model.yaml", {"research_models": registry["research_models"]})
    _write_json(references / "source-traceability.yaml", {"source_types": ["user-supplied-pdf"], "fact_lineage": registry["fact_lineage"], "aliases": registry["aliases"], "deprecated": registry["deprecated"]})
    contract_path = package / "contract.json"
    contract = _read_json(contract_path)
    contract["child_dimension_ids"] = [item["id"] for item in registry["children"]]
    contract["indicator_ids"] = [item["id"] for item in registry["indicators"]]
    contract["decision_rule_ids"] = [item["id"] for item in registry["rules"]]
    _write_json(contract_path, contract)


def _apply_operation(registry: dict[str, list[dict[str, Any]]], operation: object) -> None:
    if not isinstance(operation, dict):
        raise ValueError("OPERATION_INVALID")
    kind = operation.get("operation")
    citations = operation.get("evidence", [])
    if citations:
        registry["fact_lineage"].append({"operation": kind, "evidence": [{"evidence_id": item.get("evidence_id"), "page": item.get("page"), "quote": item.get("quote")} for item in citations if isinstance(item, dict)]})
    if kind == "add_dimension":
        dimension = operation.get("dimension")
        if not _has_id_and_name(dimension) or _find(registry["children"], dimension["id"]) is not None:
            raise ValueError("OPERATION_INVALID")
        registry["children"].append({**dimension, "status": "active"})
        for key, target in (("indicators", "indicators"), ("rules", "rules"), ("research_models", "research_models")):
            values = operation.get(key, [])
            if not isinstance(values, list) or not all(_has_id(item) for item in values):
                raise ValueError("OPERATION_INVALID")
            registry[target].extend(values)
    elif kind == "replace_dimension":
        dimension = operation.get("dimension")
        if not _has_id_and_name(dimension):
            raise ValueError("OPERATION_INVALID")
        index = _find(registry["children"], dimension["id"])
        if index is None:
            raise ValueError("OPERATION_INVALID")
        registry["children"][index] = {**dimension, "status": registry["children"][index].get("status", "active")}
    elif kind == "add_indicator":
        dimension_id, indicator = operation.get("dimension_id"), operation.get("indicator")
        if _find(registry["children"], dimension_id) is None or not _has_id(indicator) or _find(registry["indicators"], indicator["id"]) is not None:
            raise ValueError("OPERATION_INVALID")
        registry["indicators"].append(indicator)
    elif kind == "add_rule":
        rule = operation.get("rule")
        indicator_ids = rule.get("indicator_ids", []) if isinstance(rule, dict) else []
        known_indicators = {item["id"] for item in registry["indicators"]}
        if not _has_id(rule) or _find(registry["rules"], rule["id"]) is not None or _find(registry["children"], rule.get("dimension_id")) is None or not isinstance(indicator_ids, list) or not set(indicator_ids) <= known_indicators:
            raise ValueError("OPERATION_INVALID")
        registry["rules"].append(rule)
    elif kind == "add_research_model":
        model = operation.get("research_model")
        if not _has_id(model) or _find(registry["research_models"], model["id"]) is not None:
            raise ValueError("OPERATION_INVALID")
        registry["research_models"].append(model)
    elif kind in {"replace_rule", "replace_indicator", "replace_research_model"}:
        field = {"replace_rule": "rules", "replace_indicator": "indicators", "replace_research_model": "research_models"}[kind]
        item = operation.get({"replace_rule": "rule", "replace_indicator": "indicator", "replace_research_model": "research_model"}[kind])
        if not _has_id(item):
            raise ValueError("OPERATION_INVALID")
        index = _find(registry[field], item["id"])
        if index is None:
            raise ValueError("OPERATION_INVALID")
        registry[field][index] = item
    elif kind == "add_alias":
        alias, dimension_id = operation.get("alias"), operation.get("dimension_id")
        if not isinstance(alias, str) or not alias.strip() or _find(registry["children"], dimension_id) is None:
            raise ValueError("OPERATION_INVALID")
        registry["aliases"].append({"alias": alias.strip(), "dimension_id": dimension_id})
    elif kind in {"merge_dimension", "deprecate_dimension"}:
        source_id = operation.get("source_dimension_id") if kind == "merge_dimension" else operation.get("dimension_id")
        target_id = operation.get("target_dimension_id") if kind == "merge_dimension" else operation.get("replaced_by")
        source_index, target_index = _find(registry["children"], source_id), _find(registry["children"], target_id)
        if source_index is None or target_index is None or source_index == target_index:
            raise ValueError("OPERATION_INVALID")
        registry["children"][source_index]["status"] = "deprecated"
        registry["children"][source_index]["replaced_by"] = target_id
        registry["deprecated"].append({"id": source_id, "replaced_by": target_id})
        if kind == "merge_dimension":
            for rule in registry["rules"]:
                if rule.get("dimension_id") == source_id:
                    rule["dimension_id"] = target_id
    else:
        raise ValueError("OPERATION_INVALID")


def _has_id(value: object) -> bool:
    return isinstance(value, dict) and isinstance(value.get("id"), str) and bool(value["id"])


def _assert_public_content(value: object) -> None:
    if isinstance(value, str):
        if _FORBIDDEN_PUBLIC_TEXT.search(value):
            raise ValueError("PUBLIC_CONTENT_FORBIDDEN")
    elif isinstance(value, dict):
        for item in value.values():
            _assert_public_content(item)
    elif isinstance(value, list):
        for item in value:
            _assert_public_content(item)


def scan_public_materials(root: Path) -> None:
    """Reject private input and state artifacts from a publishable public tree."""
    root = Path(root)
    forbidden_names = {".pdf", ".sqlite", ".sqlite3", ".jsonl"}
    for path in root.rglob("*"):
        relative_parts = path.relative_to(root).parts
        if any(part in {".git", "__pycache__", ".pytest_cache", "job-queue", ".local-skill-workbench"} or part.startswith(".pytest-") for part in relative_parts):
            continue
        if path.is_file() and path.suffix.lower() in forbidden_names:
            raise ValueError("PUBLIC_MATERIAL_FORBIDDEN")
        if path.is_file() and path.suffix.lower() in {".py", ".md", ".json", ".yaml", ".yml", ".txt"}:
            text = path.read_text(encoding="utf-8", errors="ignore")
            if _PRIVATE_PIPELINE_NAME in text or _PRIVATE_OUTPUT_NAME in text:
                raise ValueError("PUBLIC_MATERIAL_FORBIDDEN")


def _has_id_and_name(value: object) -> bool:
    return _has_id(value) and isinstance(value.get("name"), str) and bool(value["name"])


def _find(values: list[dict[str, Any]], item_id: object) -> int | None:
    if not isinstance(item_id, str):
        return None
    for index, value in enumerate(values):
        if value.get("id") == item_id:
            return index
    return None


def _record_version(state_dir: Path, candidate: Path) -> None:
    versions = state_dir / "versions"
    versions.mkdir(exist_ok=True)
    version = f"v{len([item for item in versions.iterdir() if item.is_dir()]) + 1:04d}"
    shutil.copytree(candidate, versions / version)


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise ValueError("SKILL_TREE_INVALID") from error
    if not isinstance(value, dict):
        raise ValueError("SKILL_TREE_INVALID")
    return value


def _write_json(path: Path, value: dict[str, Any]) -> None:
    temporary = path.with_name(path.name + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")
    os.replace(temporary, path)
