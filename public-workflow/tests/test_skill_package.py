from __future__ import annotations

import sys
import json
from pathlib import Path
from zipfile import ZipFile

import pytest


sys.path.insert(0, str(Path(__file__).parents[1]))


def test_initialization_creates_no_parent_until_a_valid_update(tmp_path: Path) -> None:
    """A blank workspace must not invent any of the six research methods."""
    from skill_package import initialize_state

    assert list((initialize_state(tmp_path) / "skills").iterdir()) == []


def test_updates_reject_an_unknown_fixed_parent(tmp_path: Path) -> None:
    """A model response cannot introduce a seventh parent Skill."""
    from skill_package import apply_updates, initialize_state

    initialize_state(tmp_path)

    with pytest.raises(ValueError, match="PARENT_UNKNOWN"):
        apply_updates(tmp_path, [{"parent_id": "seventh-parent", "operations": []}])


def test_second_batch_keeps_unaffected_parent_and_revises_existing_rule(tmp_path: Path) -> None:
    """An incremental update must preserve other parent methods and stable IDs."""
    from skill_package import apply_updates

    apply_updates(tmp_path, [
        {"parent_id": "market-demand", "operations": [{
            "operation": "add_dimension",
            "dimension": {"id": "demand-penetration", "name": "渗透率"},
            "indicators": [],
            "rules": [{"id": "demand-rule", "dimension_id": "demand-penetration", "method": "原始方法"}],
            "research_models": [],
        }]},
        {"parent_id": "supply-chain", "operations": [{
            "operation": "add_dimension",
            "dimension": {"id": "supply-capacity", "name": "产能"},
            "indicators": [],
            "rules": [{"id": "supply-rule", "dimension_id": "supply-capacity", "method": "原始方法"}],
            "research_models": [],
        }]},
    ])
    unchanged = (tmp_path / "current" / "skills" / "市场需求与应用空间" / "references" / "child-dimensions.yaml").read_bytes()

    apply_updates(tmp_path, [{"parent_id": "supply-chain", "operations": [{
        "operation": "replace_rule",
        "rule": {"id": "supply-rule", "dimension_id": "supply-capacity", "method": "新方法"},
    }]}])

    assert (tmp_path / "current" / "skills" / "市场需求与应用空间" / "references" / "child-dimensions.yaml").read_bytes() == unchanged
    rules = json.loads((tmp_path / "current" / "skills" / "产业链与供给能力" / "references" / "analysis-rules.yaml").read_text(encoding="utf-8"))
    assert rules["analysis_rules"] == [{"id": "supply-rule", "dimension_id": "supply-capacity", "method": "新方法"}]


def test_invalid_second_batch_keeps_current_version(tmp_path: Path) -> None:
    """A broken candidate must leave the last validated package intact."""
    from skill_package import apply_updates

    apply_updates(tmp_path, [{"parent_id": "market-demand", "operations": [{
        "operation": "add_dimension",
        "dimension": {"id": "demand-space", "name": "市场空间"},
        "indicators": [], "rules": [], "research_models": [],
    }]}])
    before = (tmp_path / "current" / "skills" / "市场需求与应用空间" / "contract.json").read_bytes()

    with pytest.raises(ValueError, match="OPERATION_INVALID"):
        apply_updates(tmp_path, [{"parent_id": "market-demand", "operations": [{"operation": "replace_rule", "rule": {"id": "missing"}}]}])

    assert (tmp_path / "current" / "skills" / "市场需求与应用空间" / "contract.json").read_bytes() == before


def test_incremental_update_can_extend_and_revise_an_existing_child_dimension(tmp_path: Path) -> None:
    """A later PDF may add methods to an existing child without replacing its ID."""
    from skill_package import apply_updates

    apply_updates(tmp_path, [{"parent_id": "technology-product", "operations": [{
        "operation": "add_dimension", "dimension": {"id": "product-performance", "name": "产品性能"},
        "indicators": [], "rules": [], "research_models": [],
    }]}])
    apply_updates(tmp_path, [{"parent_id": "technology-product", "operations": [
        {"operation": "replace_dimension", "dimension": {"id": "product-performance", "name": "产品性能与成熟度"}},
        {"operation": "add_indicator", "dimension_id": "product-performance", "indicator": {"id": "validation-stage", "name": "验证阶段"}},
        {"operation": "add_rule", "rule": {"id": "maturity-rule", "dimension_id": "product-performance", "indicator_ids": ["validation-stage"], "method": "比较验证阶段。"}},
        {"operation": "add_research_model", "research_model": {"id": "maturity-model", "name": "成熟度模型"}},
    ]}])

    references = tmp_path / "current" / "skills" / "技术路线与产品能力" / "references"
    children = json.loads((references / "child-dimensions.yaml").read_text(encoding="utf-8"))["children"]
    indicators = json.loads((references / "indicator-catalog.yaml").read_text(encoding="utf-8"))["indicators"]
    rules = json.loads((references / "analysis-rules.yaml").read_text(encoding="utf-8"))["analysis_rules"]
    models = json.loads((references / "research-model.yaml").read_text(encoding="utf-8"))["research_models"]

    assert children == [{"id": "product-performance", "name": "产品性能与成熟度", "status": "active"}]
    assert indicators == [{"id": "validation-stage", "name": "验证阶段"}]
    assert rules == [{"id": "maturity-rule", "dimension_id": "product-performance", "indicator_ids": ["validation-stage"], "method": "比较验证阶段。"}]
    assert models == [{"id": "maturity-model", "name": "成熟度模型"}]


def test_batch_of_two_pdfs_produces_one_zip_with_fixed_parent_package(tmp_path: Path) -> None:
    """Two inputs belong to one versioned library download, never two ZIPs."""
    from skill_cli import run

    first, second = tmp_path / "a.pdf", tmp_path / "b.pdf"
    first.write_bytes(b"first pdf")
    second.write_bytes(b"second pdf")
    target = run(
        [first, second], tmp_path / "state", tmp_path / "skill-package.zip",
        [{"parent_id": "market-demand", "operations": [{
            "operation": "add_dimension", "dimension": {"id": "demand", "name": "需求"},
            "indicators": [], "rules": [], "research_models": [],
        }]}],
        text_extractor=lambda path: f"<!-- PAGE_START: 1 -->{path.stem}<!-- PAGE_END: 1 -->",
    )

    assert target == tmp_path / "skill-package.zip"
    with ZipFile(target) as archive:
        assert sorted(archive.namelist()) == [
            "skills/市场需求与应用空间/SKILL.md",
            "skills/市场需求与应用空间/contract.json",
            "skills/市场需求与应用空间/references/analysis-rules.yaml",
            "skills/市场需求与应用空间/references/child-dimensions.yaml",
            "skills/市场需求与应用空间/references/indicator-catalog.yaml",
            "skills/市场需求与应用空间/references/research-model.yaml",
            "skills/市场需求与应用空间/references/source-traceability.yaml",
        ]


def test_repeated_pdf_does_not_create_a_new_version(tmp_path: Path) -> None:
    """Fingerprint deduplication prevents a repeated upload from changing the library."""
    from skill_cli import run

    source = tmp_path / "report.pdf"
    source.write_bytes(b"same pdf")
    update = [{"parent_id": "market-demand", "operations": [{
        "operation": "add_dimension", "dimension": {"id": "demand", "name": "需求"},
        "indicators": [], "rules": [], "research_models": [],
    }]}]
    kwargs = {"text_extractor": lambda path: "<!-- PAGE_START: 1 -->text<!-- PAGE_END: 1 -->"}
    run([source], tmp_path / "state", tmp_path / "first.zip", update, **kwargs)
    run([source], tmp_path / "state", tmp_path / "second.zip", update, **kwargs)

    assert sorted(path.name for path in (tmp_path / "state" / "versions").iterdir()) == ["v0001"]


def test_unsafe_model_content_cannot_create_a_skill_zip(tmp_path: Path) -> None:
    """A path or credential echoed by a model must never reach a downloaded package."""
    from skill_cli import run

    source, target = tmp_path / "report.pdf", tmp_path / "skill-package.zip"
    source.write_bytes(b"report")
    unsafe = [{"parent_id": "market-demand", "operations": [{
        "operation": "add_dimension", "dimension": {"id": "demand", "name": "需求"},
        "indicators": [], "rules": [{"id": "rule", "dimension_id": "demand", "method": "API_KEY=secret"}], "research_models": [],
    }]}]

    with pytest.raises(ValueError, match="PUBLIC_CONTENT_FORBIDDEN"):
        run([source], tmp_path / "state", target, unsafe, text_extractor=lambda _: "text")

    assert not target.exists()


def test_public_workflow_tree_rejects_private_artifacts(tmp_path: Path) -> None:
    """The publishable module must fail its boundary scan before a private file ships."""
    from skill_package import scan_public_materials

    public_root = tmp_path / "public-workflow"
    public_root.mkdir()
    (public_root / "README.md").write_text("portable workflow", encoding="utf-8")
    scan_public_materials(public_root)
    scan_public_materials(Path(__file__).parents[1])
    (public_root / "private.pdf").write_bytes(b"private")

    with pytest.raises(ValueError, match="PUBLIC_MATERIAL_FORBIDDEN"):
        scan_public_materials(public_root)
