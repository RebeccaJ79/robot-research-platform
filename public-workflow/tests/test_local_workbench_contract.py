from pathlib import Path


def test_workbench_submits_jobs_and_refreshes_live_status() -> None:
    source = (Path(__file__).parents[1] / "local_workbench.py").read_text(encoding="utf-8")

    assert "ensure_workers(" in source
    assert "store.enqueue(" in source
    assert "@st.fragment(run_every=1)" in source
    assert "当前 PDF" in source
    assert "当前页" in source
    assert "Worker" in source
