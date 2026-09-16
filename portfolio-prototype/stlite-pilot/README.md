# stlite 公开展示验证

此目录验证浏览器内运行 Streamlit 是否能承载公开研究展示。它只读取父目录的 `data/publications.json`，展示一份每日关注和产业链图谱。

访问路径：`/stlite-pilot/`。

它不包含或请求研报 PDF、生产 Skill、模型密钥、私有 API 或生产数据库。首次访问需要下载 Pyodide 和 Streamlit 浏览器运行时，因此加载时间会比普通静态页长。

本原型验证页面结构与公开数据边界；尚未替换主公开站，也未声称所有 Streamlit 第三方组件兼容。
