# 机研公开作品集

这是可部署到 Cloudflare Pages 的纯静态公开站。公开数据来自 `data/publications.json` 的已发布脱敏快照；页面不调用模型、后台 API 或 Worker。

## 内容边界

- 日报、周报、月报：已发布结论、全节点产业链图、图表和重点公司。
- 产业链图谱：只展示完整图谱、节点和关系说明。
- 页面不调用模型，也不包含密钥、私有 PDF、完整 Skill、审核记录或生产数据。
- “研报工作台”仅说明本地 PDF→Skill 工作流并链接公开代码；不提供上传表单，也不接收用户 PDF 或密钥。

## 本地预览

```powershell
Set-Location .\portfolio-prototype
D:\python\python.exe -m http.server 4173
```

浏览器访问 `http://127.0.0.1:4173/`。

## Cloudflare Pages

将本目录作为构建输出目录上传；无需构建命令。`index.html` 是部署入口。

- Build command：留空
- Build output directory：`portfolio-prototype`
- Functions / Workers：无

Pages 仅托管本目录中的静态资源，因此浏览不依赖本地后台、电脑或 worker 在线。
