"""Local-only browser UI for the public PDF-to-Skill workflow."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

import streamlit as st

from evidence_pipeline import build_evidence_bundle
from skill_cli import fresh_pdf_paths, request_updates, run
from skill_package import load_skill_context


st.set_page_config(page_title="本地研报工作台", layout="wide")
st.title("本地研报工作台")
st.caption("PDF、OCR、证据、模型调用和 Skill 版本全部在这台电脑上完成。上传内容不会发送到公开网站。")

configured = bool(os.environ.get("MODEL_API_KEY") or os.environ.get("DEEPSEEK_API_KEY"))
st.info("已检测到模型密钥。" if configured else "未检测到模型密钥。请在启动本地工作台的 PowerShell 中设置 DEEPSEEK_API_KEY 或 MODEL_API_KEY。")

state_dir = Path(st.text_input("本地 Skill 库目录", value=str(Path.cwd() / ".local-skill-workbench"))).expanduser()
uploads = st.file_uploader("上传一份或多份 PDF", type="pdf", accept_multiple_files=True)
ocr_mode = st.selectbox("扫描件处理方式", ("auto", "off", "force"), format_func={"auto": "自动：仅对空页 OCR", "off": "关闭 OCR", "force": "全部 OCR"}.get)

if st.button("生成并校验 Skill ZIP", type="primary", disabled=not uploads or not configured):
    with tempfile.TemporaryDirectory(prefix="robot-skill-upload-") as temporary:
        source_paths = []
        for upload in uploads:
            target = Path(temporary) / Path(upload.name).name
            target.write_bytes(upload.getvalue())
            source_paths.append(target)
        try:
            progress = st.status("正在解析 PDF…", expanded=True)
            fresh = fresh_pdf_paths(source_paths, state_dir)
            bundle = build_evidence_bundle(fresh, state_dir, ocr_mode=ocr_mode) if fresh else None
            if bundle is None:
                updates = []
                progress.write("所有 PDF 已存在于当前 Skill 库中；正在重新导出完整 ZIP…")
            else:
                progress.write(f"已生成 {len(bundle.evidence)} 条带页码证据。正在请求模型…")
                updates = request_updates(bundle, load_skill_context(state_dir))
            progress.write("模型结果已通过证据引用校验。正在构建 Skill ZIP…")
            output = state_dir / "downloads" / "skill-package.zip"
            run(source_paths, state_dir, output, updates, text_extractor=lambda _path: "prepared local evidence")
            progress.update(label="生成完成", state="complete", expanded=False)
            st.success("Skill ZIP 已生成；可下载并在下次上传新 PDF 时继续更新同一目录。")
            st.download_button("下载 skill-package.zip", data=output.read_bytes(), file_name="skill-package.zip", mime="application/zip")
        except Exception as error:
            st.error(f"未生成 ZIP：{error}")

st.markdown("### 本地产物")
st.write("`markdown/` 保存清洗后的页码 Markdown；`evidence/` 保存证据索引；`current/` 保存当前有效 Skill；`versions/` 保存历史版本。ZIP 不包含原始 PDF、密钥或本地路径。")
