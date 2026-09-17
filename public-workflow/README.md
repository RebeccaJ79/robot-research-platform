# Public Workflow

公开仓库包含两项本地工作流：JSON 到公开展示快照，以及多份 PDF 到可增量更新的机器人行业 Skill 包。两者都在使用者的电脑上运行；本仓库不包含生产 PDF、生产 Skill、私有提示词、数据库或凭据。

## PDF → Skill 包

一次可输入任意数量的本地 PDF，输出一个完整的 `skill-package.zip`。程序会将每份 PDF 清洗为本地、带页码的 Markdown，并生成带 `evidence_id`、页码和文本片段的本地证据索引；二者均保存在 `--state` 目录，不进入 ZIP。其中的 `skills/` 只包含六个固定父维度中已有有效方法的目录：市场需求与应用空间、技术路线与产品能力、产业链与供给能力、商业化落地与量产进程、竞争格局与公司基本面、估值与投资判断。

同一个 `--state` 目录保存当前有效版本、历史版本和已处理 PDF 指纹。后续输入新 PDF 时，程序在当前版本上更新子维度、指标、规则和研究模型；重复 PDF 不重复添加。每次成功运行都会重新导出一个完整 ZIP。

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

OCR 仅在本机执行。除 Python 依赖外，请安装 [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) 并确保 `tesseract` 在 `PATH` 中；默认语言为简体中文和英文（`chi_sim+eng`）。

使用用户自己的 PDF 和离线样例更新运行：

```powershell
python skill_cli.py --pdf .\report-a.pdf --pdf .\report-b.pdf --state .\local-state --output .\skill-package.zip --offline-updates .\sample-data\skill-updates.json
```

不提供 `--offline-updates` 时，程序读取 `MODEL_API_KEY`、`MODEL_BASE_URL` 和可选的 `MODEL_NAME`，调用使用者配置的 OpenAI 兼容端点。请在当前命令行会话或操作系统环境变量中设置真实值；`.env.example` 仅为变量名模板，程序不会自动读取 `.env` 文件。模型费用由使用者承担。

PowerShell 示例：

```powershell
$env:MODEL_API_KEY = "你的密钥"
$env:MODEL_BASE_URL = "https://你的模型服务/v1"
$env:MODEL_NAME = "你的模型名称"
python skill_cli.py --pdf .\report-a.pdf --state .\local-state --output .\skill-package.zip
```

`--ocr auto` 为默认值：先提取 PDF 原生文本，空文本时在本机 OCR；`--ocr force` 始终 OCR；`--ocr off` 禁止 OCR 并在扫描件上失败。

模型只收到清洗后的带页码 evidence 片段，而非 PDF 文件。模型返回的每一项更新操作都必须引用现有 `evidence_ids`；未知、缺失或空引用会在写入 Skill 前被拒绝。

ZIP 只包含 `SKILL.md`、`contract.json` 和 `references/` 下的通用方法文件。PDF 原件、解析文本、指纹、路径、密钥、模型回复和临时状态不写入 ZIP。

## 真实端点 smoke test

先用一份不敏感、可提取文字的 PDF 运行在线命令。成功时控制台只打印 ZIP 路径，并在 `--state/markdown/` 和 `--state/evidence/` 生成本地审计产物。请先检查 evidence 的页码和片段，再使用 ZIP。

## 常见问题

| 现象 | 原因与处理 |
| --- | --- |
| `PDF_TEXT_EXTRACTION_EMPTY` | PDF 没有原生文本且使用了 `--ocr off`；改用默认 `--ocr auto`。 |
| `OCR_DEPENDENCIES_REQUIRED` | 未安装 `PyMuPDF` 或 `pytesseract`；重新执行依赖安装。 |
| `TESSERACT_REQUIRED` | 未安装 Tesseract 或未加入 `PATH`；安装后重新打开命令行。 |
| `EVIDENCE_CITATION_REQUIRED` / `EVIDENCE_CITATION_UNKNOWN` | 模型没有为每项操作提供有效 evidence ID；检查模型是否支持 JSON 输出，或更换模型/提示配置。 |
| `MODEL_*_REQUIRED` / `MODEL_OUTPUT_INVALID` | 检查当前命令行环境变量、OpenAI 兼容 `/chat/completions` 地址和模型 JSON 输出能力。 |

## JSON → 公开展示快照

```powershell
python workflow.py --input sample-data/input.json --output output/publications.json --offline
```
