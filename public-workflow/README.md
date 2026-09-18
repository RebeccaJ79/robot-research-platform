# Public Workflow

公开仓库包含两项本地工作流：JSON 到公开展示快照，以及多份 PDF 到可增量更新的机器人行业 Skill 包。两者都在使用者的电脑上运行；本仓库不包含生产 PDF、生产 Skill、私有提示词、数据库或凭据。

## PDF → Skill 包

若由 Codex、Hermes 或其他本地 agent 执行，请先阅读 [`AGENTS.md`](AGENTS.md)；其中规定了输入输出、密钥、隐私边界和成功校验。

一次可输入任意数量的本地 PDF，输出一个完整的 `skill-package.zip`。程序会将每份 PDF 清洗为本地、带页码的 Markdown，并生成带 `evidence_id`、页码和文本片段的本地证据索引；二者均保存在 `--state` 目录，不进入 ZIP。ZIP 始终包含六个固定父维度的 Skill 目录：市场需求与应用空间、技术路线与产品能力、产业链与供给能力、商业化落地与量产进程、竞争格局与公司基本面、估值与投资判断；没有被证据支持的方法保持为空，不会被编造。

同一个 `--state` 目录保存当前有效版本、历史版本和已处理 PDF 指纹。后续输入新 PDF 时，程序在当前版本上更新子维度、指标、规则和研究模型；重复 PDF 不重复添加。每次成功运行都会重新导出一个完整 ZIP。

安装依赖：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

启动本地网页工作台：

```powershell
# 已在 PowerShell 配置 DeepSeek 时无需重复设置密钥
.\.venv\Scripts\python.exe -m streamlit run local_workbench.py
```

浏览器会打开本地地址。上传的 PDF 只交给本机程序处理；本地工作台复用下方同一套命令行生成核心。

点击生成后，PDF 会进入本地队列，工作台每秒刷新任务状态。每一份 PDF 都显示“排队中、解析 PDF、OCR、证据完成”等阶段；任务会显示当前 PDF、已完成数量、百分比、worker ID 和错误代码。首次提交自动启动两个本地 worker。不同 Skill 库目录可并发处理，同一目录会按顺序写入，避免版本覆盖。

不使用网页时，Codex、Hermes 等 agent 可通过 [`job_cli.py`](AGENTS.md#后台任务与实时进度) 提交任务并查询 JSON 状态。

OCR 仅在本机执行。除 Python 依赖外，请安装 [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) 并确保 `tesseract` 在 `PATH` 中；默认语言为简体中文和英文（`chi_sim+eng`）。

使用用户自己的 PDF 和离线样例更新运行：

```powershell
.\.venv\Scripts\python.exe skill_cli.py --pdf .\report-a.pdf --pdf .\report-b.pdf --state .\local-state --output .\skill-package.zip --offline-updates .\sample-data\skill-updates.json
```

不提供 `--offline-updates` 时，程序优先读取 `MODEL_API_KEY`、`MODEL_BASE_URL` 和可选的 `MODEL_NAME`，也兼容 DeepSeek 的 `DEEPSEEK_API_KEY`、`DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`。它调用使用者配置的 OpenAI 兼容端点；`.env.example` 仅为变量名模板，程序不会自动读取 `.env` 文件。模型费用由使用者承担。

PowerShell 示例：

```powershell
$env:MODEL_API_KEY = "你的密钥"
$env:MODEL_BASE_URL = "https://你的模型服务/v1"
$env:MODEL_NAME = "你的模型名称"
.\.venv\Scripts\python.exe skill_cli.py --pdf .\report-a.pdf --state .\local-state --output .\skill-package.zip
```

已配置 DeepSeek 的 PowerShell 可直接运行网页工作台或上述命令。若只设置了密钥，默认使用 `https://api.deepseek.com/v1` 与 `deepseek-chat`：

```powershell
$env:DEEPSEEK_API_KEY = "你的 DeepSeek 密钥"
.\.venv\Scripts\python.exe -m streamlit run local_workbench.py
```

`--ocr auto` 为默认值：先提取 PDF 原生文本，空文本时在本机 OCR；`--ocr force` 始终 OCR；`--ocr off` 禁止 OCR 并在扫描件上失败。

模型只收到清洗后的带页码 evidence 片段，而非 PDF 文件。模型返回的每一项更新操作都必须引用现有 `evidence_id` 和不超过 180 字的原文短引；程序核验短引确实出现在对应页码证据中，再要求模型按同一证据逐项语义复核。任何未知、缺失、无效或未通过复核的更新都会在写入 Skill 前被拒绝。

ZIP 只包含 `SKILL.md`、`contract.json` 和 `references/` 下的通用方法文件；其中的来源追溯仅保留证据 ID、页码和短引。PDF 原件、解析文本、文档指纹、路径、密钥、模型回复和临时状态不写入 ZIP。

## 真实端点 smoke test

先用一份不敏感、可提取文字的 PDF 运行在线命令。成功时控制台只打印 ZIP 路径，并在 `--state/markdown/` 和 `--state/evidence/` 生成本地审计产物。请先检查 evidence 的页码和片段，再使用 ZIP。

## 常见问题

| 现象 | 原因与处理 |
| --- | --- |
| `PDF_TEXT_EXTRACTION_EMPTY` | PDF 没有原生文本且使用了 `--ocr off`；改用默认 `--ocr auto`。 |
| `OCR_DEPENDENCIES_REQUIRED` | 未安装 `PyMuPDF` 或 `pytesseract`；重新执行依赖安装。 |
| `TESSERACT_REQUIRED` | 未安装 Tesseract 或未加入 `PATH`；安装后重新打开命令行。 |
| `EVIDENCE_CITATION_REQUIRED` / `EVIDENCE_CITATION_UNKNOWN` / `EVIDENCE_QUOTE_INVALID` | 模型没有为每项操作提供有效 evidence ID 或逐字短引；程序会要求模型最多纠正两次，仍失败时保留原 Skill。 |
| `MODEL_SEMANTIC_REVIEW_REJECTED` | 第二次模型复核认为引文不足以支持该方法更新；保留原 Skill，换更具体的 PDF 或重新运行。 |
| `MODEL_*_REQUIRED` / `MODEL_OUTPUT_INVALID` / `MODEL_REQUEST_FAILED` | 检查当前 PowerShell 的 DeepSeek 或通用模型变量、OpenAI 兼容 `/chat/completions` 地址和模型 JSON 输出能力；临时网络故障会自动重试两次。 |

## JSON → 公开展示快照

```powershell
python workflow.py --input sample-data/input.json --output output/publications.json --offline
```
