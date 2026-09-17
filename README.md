# robot-research-platform

机器人产业研究的公开展示平台与可复用本地工作流样例。

- 公开网站：[robot-research-platform.pages.dev](https://robot-research-platform.pages.dev/)
- 在线内容仅展示已发布的脱敏成果；不调用模型、后台 API 或 Worker。
- 本仓库不包含生产 PDF、生产 Skill、私有提示词、私有数据或任何密钥。

## 仓库内容

| 目录 | 用途 |
| --- | --- |
| [`portfolio-prototype/`](portfolio-prototype/) | 部署到 Cloudflare Pages 的纯静态公开展示站。 |
| [`public-workflow/`](public-workflow/) | 使用者在自己电脑上运行的 PDF→Skill 包命令行工作流。 |
| [`github-starter/`](github-starter/) | JSON→公开展示快照的最小可运行样例。 |

## PDF → Skill 包：当前能力

`public-workflow/` 一次可接收任意数量的本地 PDF，并输出一个 `skill-package.zip`。同一个本地 `--state` 目录会保存当前有效版本、版本历史和 PDF 指纹；后续加入新 PDF 时会在原有 Skill 基础上更新，重复 PDF 不会重复处理。

已实现的步骤：

1. 使用 `pypdf` 在本机提取**原生文本 PDF**，并以 `<!-- PAGE_START: n -->` / `<!-- PAGE_END: n -->` 保留页码边界。
2. 将页码文本发送到使用者自行配置的 OpenAI 兼容模型端点，请求六个固定父维度内的结构化更新操作。
3. 对模型更新做固定父维度、操作引用、Skill 文件结构与敏感内容校验；失败时保留上一个有效版本。
4. 导出仅含 `skills/`、`SKILL.md`、`contract.json` 和 `references/` 的 ZIP 包。

尚未实现的步骤：

- 确定性正文清洗、分段去重和规范化 Markdown 文件落盘。
- 可引用的证据提取（证据片段、页码、出处结构化保存）及基于证据的语义校验。
- OCR；扫描件或没有可提取文本的 PDF 会失败。

因此，当前版本**不能**如实称为“PDF→确定性清洗与证据提取→Skill”的完整链路。详情、安装与命令示例见 [`public-workflow/README.md`](public-workflow/README.md)。

## 本地运行

```powershell
git clone https://github.com/RebeccaJ79/robot-research-platform.git
cd robot-research-platform/public-workflow
python -m pip install -r requirements.txt
python skill_cli.py --pdf .\report-a.pdf --pdf .\report-b.pdf --state .\local-state --output .\skill-package.zip --offline-updates .\sample-data\skill-updates.json
```

去掉 `--offline-updates` 后，需在本机环境设置 `MODEL_API_KEY`、`MODEL_BASE_URL`，以及可选的 `MODEL_NAME`。密钥仅发送给使用者配置的模型端点，费用由使用者承担。

## 验证

```powershell
cd public-workflow
python -m pytest tests -q
```

测试覆盖增量更新、重复 PDF 去重、固定六父维度、无效候选版本回滚、敏感内容阻断和 ZIP 目录结构。

## 许可

[MIT License](LICENSE)
