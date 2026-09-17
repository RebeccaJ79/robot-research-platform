"""Local-only browser UI for the public PDF-to-Skill workflow."""

from __future__ import annotations

import os
import uuid
from pathlib import Path

import streamlit as st

from job_queue import JobStore
from job_worker import ensure_workers


st.set_page_config(page_title="本地研报工作台", layout="wide")
st.title("本地研报工作台")
st.caption("PDF、OCR、证据、模型调用和 Skill 版本全部在这台电脑上完成。上传内容不会发送到公开网站。")

configured = bool(os.environ.get("MODEL_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"))
st.info("已检测到模型密钥。" if configured else "未检测到模型密钥。请在启动本地工作台的 PowerShell 中设置 DEEPSEEK_API_KEY 或 MODEL_API_KEY。")

state_dir = Path(st.text_input("本地 Skill 库目录", value=str(Path.cwd() / ".local-skill-workbench"))).expanduser()
uploads = st.file_uploader("上传一份或多份 PDF", type="pdf", accept_multiple_files=True)
ocr_mode = st.selectbox("扫描件处理方式", ("auto", "off", "force"), format_func={"auto": "自动：仅对空页 OCR", "off": "关闭 OCR", "force": "全部 OCR"}.get)
queue_root = state_dir.parent / "job-queue"
store = JobStore(queue_root)

if st.button("生成并校验 Skill ZIP", type="primary", disabled=not uploads or not configured):
    upload_root = queue_root / "inputs" / uuid.uuid4().hex
    upload_root.mkdir(parents=True, exist_ok=True)
    source_paths = []
    for index, upload in enumerate(uploads, start=1):
        target = upload_root / f"{index:02d}-{Path(upload.name).name}"
        target.write_bytes(upload.getvalue())
        source_paths.append(target)
    output = state_dir / "downloads" / "skill-package.zip"
    job_id = store.enqueue(source_paths, state_dir, output, ocr_mode=ocr_mode)
    ensure_workers(queue_root)
    st.session_state["active_job_id"] = job_id
    st.success(f"任务已入队：{job_id[:8]}。下方状态每秒自动刷新。")


@st.fragment(run_every=1)
def render_live_status() -> None:
    jobs = store.list_jobs()
    workers = store.workers()
    st.subheader("实时任务进度")
    st.caption("本地 worker 每秒更新；不同 Skill 库目录可并发，同一目录会顺序写入。")
    active_job_id = st.session_state.get("active_job_id")
    active = next((job for job in jobs if job["id"] == active_job_id), jobs[0] if jobs else None)
    if active:
        st.progress(int(active["progress"] * 100), text=f"{active['status']} · {active['stage']} · 当前 PDF：{active['current_pdf'] or '—'}")
        st.write({"任务": active["id"][:8], "Worker": active["worker_id"] or "等待分配", "当前 PDF": active["current_pdf"] or "—", "已完成 PDF": f"{active['completed_files']}/{active['total_files']}", "错误": active["error_code"] or "—"})
        if active["status"] == "completed" and active["output_path"].is_file():
            st.download_button("下载 skill-package.zip", data=active["output_path"].read_bytes(), file_name="skill-package.zip", mime="application/zip")
    else:
        st.info("尚无本地任务。上传 PDF 后会自动启动 worker。")
    st.dataframe([
        {"任务": job["id"][:8], "状态": job["status"], "阶段": job["stage"], "当前 PDF": job["current_pdf"] or "—", "进度": f"{job['progress'] * 100:.0f}%", "Worker": job["worker_id"] or "—"}
        for job in jobs
    ], use_container_width=True, hide_index=True)
    st.caption("Worker：" + ("； ".join(f"{worker['id']} (PID {worker['pid']})" for worker in workers) if workers else "尚未启动"))


render_live_status()

st.markdown("### 本地产物")
st.write("`markdown/` 保存清洗后的页码 Markdown；`evidence/` 保存证据索引；`current/` 保存当前有效 Skill；`versions/` 保存历史版本。任务队列与上传副本保存在本地 `job-queue/`。ZIP 不包含原始 PDF、密钥或本地路径。")
