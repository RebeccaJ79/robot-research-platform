# Local PDF Job Workers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Let the local PDF-to-Skill workbench queue work, run local workers automatically, and report each PDF and task in real time.

**Architecture:** `job_queue.py` owns a local SQLite queue, task events, worker heartbeats, and state-directory write exclusion. `job_worker.py` continuously claims compatible jobs, emits progress while it parses each PDF, then performs model review and ZIP export. Streamlit only enqueues uploads and polls the queue; it never performs the long-running work itself.

**Tech Stack:** Python standard library `sqlite3` and `subprocess`; existing Streamlit, PyPDF/PyMuPDF/Tesseract workflow.

**Spec:** `docs/superpowers/specs/2026-09-17-public-pdf-skill-package-design.md`

## Global Constraints

- All PDFs, queue state, logs and ZIPs remain local and must be ignored by Git.
- Different Skill state directories may execute concurrently; a single state directory has one running writer.
- Worker progress must identify the current PDF and stage without exposing PDF contents or model credentials.
- No new third-party Python dependency.

---

### Task 1: Persistent queue and progress contract

**Files:**
- Create: `public-workflow/job_queue.py`
- Create: `public-workflow/tests/test_job_queue.py`
- Modify: `.gitignore`

**Interfaces:**
- Produces `JobStore.enqueue()`, `claim_next()`, `update_progress()`, `complete()`, `fail()`, and `workers()`.
- A job stores its local input paths, state directory, output path, current PDF name, stage, percentage, worker ID and error code.

- [x] Write failing tests that enqueue a job, claim it once, block a second job for the same state directory, and expose document progress.
- [x] Implement SQLite transactions with a state-directory exclusion query and a worker heartbeat table.
- [x] Add local workbench state and queue files to `.gitignore`.
- [x] Run `pytest tests/test_job_queue.py -q`.

### Task 2: Background worker and per-PDF events

**Files:**
- Create: `public-workflow/job_worker.py`
- Modify: `public-workflow/evidence_pipeline.py`
- Modify: `public-workflow/tests/test_evidence_pipeline.py`
- Create: `public-workflow/tests/test_job_worker.py`

**Interfaces:**
- `build_evidence_bundle(..., progress_callback=...)` emits safe events before and after each PDF and after OCR fallback.
- `process_one_job(store, worker_id)` claims, processes and finalizes exactly one job.

- [x] Write failing tests for callback event order and a worker completing an offline job.
- [x] Add optional progress callback to the deterministic extraction loop.
- [x] Implement worker claiming, evidence extraction, model/update stages, ZIP export, error recording and heartbeats.
- [x] Run the focused worker and evidence tests.

### Task 3: Streamlit queue submission and live monitor

**Files:**
- Modify: `public-workflow/local_workbench.py`
- Create: `public-workflow/tests/test_local_workbench_contract.py`

**Interfaces:**
- Upload click persists inputs, calls `ensure_workers()`, enqueues a job, and stores `job_id` in session state.
- A `st.fragment(run_every=1)` monitor renders job and worker tables from `JobStore`.

- [x] Write a failing source-contract test for queue submission, auto worker launch and timed refresh.
- [x] Replace synchronous processing with persistent local job submission.
- [x] Render per-PDF stage, completion count, percentage, worker ID, elapsed time and error text; expose ZIP download only for completed jobs.
- [x] Run all public-workflow tests and a headless Streamlit HTTP smoke test.

### Task 4: Agent contract and documentation

**Files:**
- Modify: `public-workflow/AGENTS.md`
- Modify: `public-workflow/README.md`
- Modify: `README.md`

- [x] Document `job_worker.py`, worker count, queue status and how an agent waits for a job without reading private PDF content.
- [x] Document that active worker IDs and job states are the evidence of automatic concurrent execution.
- [x] Run all tests, verify no local state is tracked, then commit and push.
