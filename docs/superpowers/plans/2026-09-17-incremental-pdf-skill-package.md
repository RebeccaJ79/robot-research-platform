# Incremental PDF Skill Package Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a public local CLI that turns multiple user PDFs into one
versioned six-parent Skill ZIP and safely updates that ZIP when new PDFs arrive.

**Architecture:** `public-workflow/skill_package.py` owns the public six-parent
taxonomy, package registry operations, atomic local state, validation, and ZIP
creation. `public-workflow/skill_cli.py` parses PDFs, obtains fixture or model
updates, and delegates all persistence to the package module. The static site
links to the local workflow but never receives user content.

**Tech Stack:** Python 3.10+, standard library, `pypdf`, pytest, static HTML.

**Spec:** `docs/superpowers/specs/2026-09-17-public-pdf-skill-package-design.md`

## Global Constraints

- Keep exactly six fixed robot-industry parent IDs and names.
- Process PDFs and credentials only on the caller's machine.
- Publish one complete `skill-package.zip` per successful batch.
- Retain validated current state on a failed update.
- Do not commit PDFs, generated state, model prompts, raw responses, or credentials.

---

### Task 1: Fixed parent package and validation module

**Files:**
- Create: `public-workflow/skill_package.py`
- Create: `public-workflow/tests/test_skill_package.py`
- Modify: `public-workflow/requirements.txt`

**Interfaces:**
- Produces `initialize_state(state_dir: Path) -> Path`,
  `apply_updates(state_dir: Path, updates: list[dict]) -> Path`, and
  `validate_skill_tree(root: Path) -> None`.
- Produces six stable parent IDs and package directories.

- [ ] **Step 1: Write failing tests for a new state tree and invalid parent**

```python
def test_initialization_creates_no_parent_until_a_valid_update(tmp_path):
    from skill_package import initialize_state
    assert list((initialize_state(tmp_path) / "skills").iterdir()) == []

def test_updates_reject_an_unknown_parent(tmp_path):
    from skill_package import apply_updates, initialize_state
    initialize_state(tmp_path)
    with pytest.raises(ValueError, match="PARENT_UNKNOWN"):
        apply_updates(tmp_path, [{"parent_id": "seventh-parent", "operations": []}])
```

- [ ] **Step 2: Run the focused tests and verify they fail because the module is absent**

Run: `python -m pytest public-workflow/tests/test_skill_package.py -q`

- [ ] **Step 3: Implement the fixed taxonomy, blank state tree, parent validation, and `pypdf` dependency declaration**

```python
PARENTS = {
    "market-demand": "市场需求与应用空间",
    "technology-product": "技术路线与产品能力",
    "supply-chain": "产业链与供给能力",
    "commercialization": "商业化落地与量产进程",
    "company-fundamentals": "竞争格局与公司基本面",
    "valuation-investment": "估值与投资判断",
}

def initialize_state(state_dir: Path) -> Path:
    root = state_dir / "current"
    (root / "skills").mkdir(parents=True, exist_ok=True)
    return root
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `python -m pytest public-workflow/tests/test_skill_package.py -q`

### Task 2: Incremental registry operations and atomic versions

**Files:**
- Modify: `public-workflow/skill_package.py`
- Modify: `public-workflow/tests/test_skill_package.py`

**Interfaces:**
- Consumes an initialized state and per-parent add, replace, merge, alias, and
  deprecate operations.
- Produces a new immutable version under `versions/` and promotes it to
  `current/` only after validation.

- [ ] **Step 1: Write failing tests for retaining an unaffected parent, replacing a rule, and failed-update rollback**

```python
def test_second_batch_keeps_unaffected_parent_and_revises_existing_rule(tmp_path):
    # Apply market-demand then update only supply-chain.
    # Assert market-demand bytes and stable child ID remain unchanged.
    # Assert the named supply-chain rule is revised.

def test_invalid_second_batch_keeps_current_version(tmp_path):
    # Capture current package bytes then submit an invalid operation.
    # Assert the bytes and current version remain unchanged.
```

- [ ] **Step 2: Run the focused tests and verify they fail because operations are not implemented**

Run: `python -m pytest public-workflow/tests/test_skill_package.py -q`

- [ ] **Step 3: Implement validated registry operations and atomic candidate promotion**

```python
candidate = state_dir / "candidates" / version_id
shutil.copytree(current, candidate)
apply_operations(candidate, updates)
validate_skill_tree(candidate)
os.replace(candidate, next_version)
replace_current_pointer(state_dir, next_version)
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `python -m pytest public-workflow/tests/test_skill_package.py -q`

### Task 3: PDF batches, local deduplication, and ZIP output

**Files:**
- Create: `public-workflow/skill_cli.py`
- Modify: `public-workflow/skill_package.py`
- Modify: `public-workflow/tests/test_skill_package.py`

**Interfaces:**
- Consumes `run(pdf_paths: list[Path], state_dir: Path, output_zip: Path,
  updates: list[dict]) -> Path`.
- Produces one ZIP containing the validated `skills/` tree and no transient
  state or PDF content.

- [ ] **Step 1: Write failing tests for multi-PDF one-ZIP output and duplicate fingerprint skipping**

```python
def test_batch_of_two_pdfs_produces_one_zip_with_fixed_parent_package(tmp_path):
    # Use a deterministic text-extractor fixture and offline updates.
    # Assert exactly one ZIP and all expected package files.

def test_repeated_pdf_does_not_create_a_new_version(tmp_path):
    # Run the same PDF twice and assert the second run is marked unchanged.
```

- [ ] **Step 2: Run the focused tests and verify they fail because the CLI is absent**

Run: `python -m pytest public-workflow/tests/test_skill_package.py -q`

- [ ] **Step 3: Implement page-marked `pypdf` extraction, SHA-256 local deduplication, fixture/model update input, and ZIP packaging**

```python
with ZipFile(output_zip, "w", ZIP_DEFLATED) as archive:
    for path in skill_root.rglob("*"):
        if path.is_file():
            archive.write(path, path.relative_to(version_root))
```

- [ ] **Step 4: Run the focused tests and verify they pass**

Run: `python -m pytest public-workflow/tests/test_skill_package.py -q`

### Task 4: Public documentation and static workbench entry

**Files:**
- Modify: `public-workflow/README.md`
- Modify: `public-workflow/.env.example`
- Modify: `portfolio-prototype/index.html`
- Modify: `portfolio-prototype/README.md`
- Test: `public-workflow/tests/test_skill_package.py`

**Interfaces:**
- Documents the local command and user-owned credential configuration.
- Adds a static “研报工作台” item before “每日关注” that contains no upload form.

- [ ] **Step 1: Write a failing behavior test for the generated ZIP’s safe public contents**

```python
def test_zip_contains_no_pdf_paths_credentials_or_transient_state(tmp_path):
    # Read archive member names and contents from a real offline package.
    # Assert no member or contents includes the input path or secret literal.
```

- [ ] **Step 2: Run the focused test and verify it fails before the sanitization/documentation work**

Run: `python -m pytest public-workflow/tests/test_skill_package.py -q`

- [ ] **Step 3: Add README, environment template, safe package scan, and static workbench entry**

```text
python skill_cli.py --pdf report-a.pdf --pdf report-b.pdf --state ./local-state --output skill-package.zip --offline-updates sample-data/updates.json
```

- [ ] **Step 4: Run public-workflow and static-site verification**

Run: `python -m pytest public-workflow/tests -q && node portfolio-prototype/verify-v2.cjs`

### Task 5: Public-material boundary and release verification

**Files:**
- Modify: `README.md`
- Test: `public-workflow/tests/test_skill_package.py`

**Interfaces:**
- Documents that the public repository provides reusable code and synthetic
  fixtures, not production PDFs, Skills, or data.

- [ ] **Step 1: Write a failing repository-scan test for forbidden public artifacts**

```python
def test_public_workflow_tree_has_no_pdf_or_private_pipeline_reference():
    # Scan public-workflow and portfolio-prototype, excluding cache directories.
    # Assert no PDF, private root, or production package name appears.
```

- [ ] **Step 2: Run the focused test and verify it fails before allowlist/scan rules are implemented**

Run: `python -m pytest public-workflow/tests/test_skill_package.py -q`

- [ ] **Step 3: Implement the scan and update the root README’s reproducibility instructions**

```text
The starter runs only against caller-provided PDFs and caller-provided model credentials.
```

- [ ] **Step 4: Run the full release checks**

Run: `python -m pytest public-workflow/tests -q && node portfolio-prototype/verify-v2.cjs && git diff --check`
