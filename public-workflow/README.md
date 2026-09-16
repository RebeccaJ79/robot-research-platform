# Public Workflow

将公开 JSON 输入转换为公开展示站使用的快照。没有私有路径、PDF 处理、完整生产 Skill、凭据存储或内部审核面板。

离线演示：

```powershell
python workflow.py --input sample-data/input.json --output output/publications.json --offline
```

真实模型运行需设置 `MODEL_API_KEY`、`MODEL_BASE_URL`（不含 `/chat/completions`）和可选的 `MODEL_NAME`；使用者承担模型费用。脚本调用 OpenAI 兼容的 `/chat/completions` 接口，并只发送公开 JSON 输入。
