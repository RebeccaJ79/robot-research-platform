# PDF → Skill：Agent 运行手册

本手册适用于 Codex、Hermes 及任何能在用户电脑上执行命令的 agent。核心接口是 `skill_cli.py`；Streamlit 仅供人工上传和下载。

## 运行边界

- 只读取用户明确指定的 PDF 和目录。
- 在用户本机运行解析、OCR、证据提取、状态保存和 ZIP 导出。
- 仅在用户已经授权模型调用且本机已设置模型密钥时，调用该用户配置的模型端点。
- 不上传 PDF 到公开网站；不把 PDF、密钥、模型回复、状态目录或本地路径提交到 GitHub。
- 完成后只返回 ZIP 路径、校验状态和必要的失败代码；不要回传 PDF 正文、证据全文或密钥。

## 安装

在仓库根目录执行：

```powershell
cd public-workflow
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest tests -q
```

扫描件使用 OCR 时，需在本机安装 Tesseract，并让 `tesseract` 位于 `PATH`。原生文本 PDF 不需要 Tesseract。

## 标准执行契约

输入为一个或多个本地 PDF、一个可持续使用的状态目录，以及一个 ZIP 输出路径：

```powershell
.\.venv\Scripts\python.exe skill_cli.py `
  --pdf "C:\research\report-a.pdf" `
  --pdf "C:\research\report-b.pdf" `
  --state "C:\research\robot-skill-state" `
  --output "C:\research\skill-package.zip"
```

## 后台任务与实时进度

需要让 agent 提交任务、持续查看进度，或让多位使用者共享同一台电脑时，使用队列入口。首次提交会自动启动两个本地 worker：不同 `--state` 目录可同时执行；同一 `--state` 目录只会有一个写入任务。

```powershell
.\.venv\Scripts\python.exe job_cli.py submit `
  --pdf "C:\research\report-a.pdf" `
  --queue-root "C:\research\job-queue" `
  --state "C:\research\robot-skill-state" `
  --output "C:\research\skill-package.zip"
```

命令输出任务 ID。agent 应轮询状态，而不是猜测 worker 是否运行：

```powershell
.\.venv\Scripts\python.exe job_cli.py status `
  --queue-root "C:\research\job-queue" `
  --job-id "任务 ID"
```

状态会包含 `status`、`stage`、`current_pdf`、`completed_files`、`progress`、`worker_id` 和 `error_code`。看到不同任务同时处于 `running`，且 `worker_id` 分别为 `worker-1`、`worker-2`，即表示本地并发 worker 正在工作；同一状态目录的后续任务保持 `queued` 是预期的写入保护。

同一个 `--state` 会保留当前有效 Skill、历史版本及 PDF 指纹。后续新 PDF 会在原有六个固定父维度内更新；重复 PDF 不会重复处理。每次成功执行都导出一个完整的 `skill-package.zip`。

需要离线演示或回归验证时，使用仓库样例更新，不调用模型：

```powershell
.\.venv\Scripts\python.exe skill_cli.py `
  --pdf "C:\research\report-a.pdf" `
  --state "C:\research\robot-skill-state" `
  --output "C:\research\skill-package.zip" `
  --offline-updates .\sample-data\skill-updates.json
```

## 模型与 OCR

真实更新会读取 `MODEL_API_KEY`，或兼容读取 `DEEPSEEK_API_KEY`。可选变量为 `MODEL_BASE_URL`、`MODEL_NAME`、`DEEPSEEK_BASE_URL` 和 `DEEPSEEK_MODEL`。agent 不应打印这些变量的值。

`--ocr auto` 为默认值：仅对原生文本为空的页面进行本机 OCR。`--ocr off` 禁止 OCR；`--ocr force` 对所有页面执行 OCR。

## 成功校验与返回格式

成功时检查 ZIP 存在，且其顶层仅为 `skills/`。ZIP 不得包含 PDF、密钥、本地绝对路径、模型回复或本地状态目录。

建议向用户返回：

```text
状态：已生成并校验
Skill ZIP：C:\research\skill-package.zip
状态目录：C:\research\robot-skill-state
```

失败时保留最后一个有效版本，不删除原有状态。常见失败代码及处理见 [README.md](README.md)。
