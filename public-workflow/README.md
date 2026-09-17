# Public Workflow

公开仓库包含两项本地工作流：JSON 到公开展示快照，以及多份 PDF 到可增量更新的机器人行业 Skill 包。两者都在使用者的电脑上运行；本仓库不包含生产 PDF、生产 Skill、私有提示词、数据库或凭据。

## PDF → Skill 包

一次可输入任意数量的本地 PDF，输出一个完整的 `skill-package.zip`。其中的 `skills/` 只包含六个固定父维度中已有有效方法的目录：市场需求与应用空间、技术路线与产品能力、产业链与供给能力、商业化落地与量产进程、竞争格局与公司基本面、估值与投资判断。

同一个 `--state` 目录保存当前有效版本、历史版本和已处理 PDF 指纹。后续输入新 PDF 时，程序在当前版本上更新子维度、指标、规则和研究模型；重复 PDF 不重复添加。每次成功运行都会重新导出一个完整 ZIP。

安装依赖：

```powershell
python -m pip install -r requirements.txt
```

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

ZIP 只包含 `SKILL.md`、`contract.json` 和 `references/` 下的通用方法文件。PDF 原件、解析文本、指纹、路径、密钥、模型回复和临时状态不写入 ZIP。

## JSON → 公开展示快照

```powershell
python workflow.py --input sample-data/input.json --output output/publications.json --offline
```
