import html
import json
import math

import streamlit as st


def percent(value):
    try:
        return f"{float(value):+.2%}"
    except (TypeError, ValueError):
        return "—"


def comparison_rows(report, chart):
    if chart.get("type") == "grouped_bar":
        field = chart.get("metric", {}).get("field", "period_excess_return")
        rows = {}
        for item in chart.get("data", []):
            rows.setdefault(item.get("node_name", ""), []).append(item)
        result = []
        for name, values in rows.items():
            current = next((item for item in values if "本" in str(item.get("period", ""))), values[0])
            previous = next((item for item in values if item is not current), None)
            result.append((name, current.get(field), previous.get(field) if previous else None))
        return result

    trend = next((item for item in report.get("charts", []) if item.get("type") == "line"), {})
    field = trend.get("metric", {}).get("field", "node_return")
    names = [item.get("node_name", "") for item in chart.get("data", [])]
    result = []
    for name in dict.fromkeys(names):
        values = sorted(
            (item for item in trend.get("data", []) if item.get("node_name") == name),
            key=lambda item: str(item.get("trade_date", "")),
        )
        if values:
            result.append((name, values[-1].get(field), values[-2].get(field) if len(values) > 1 else None))
    return result


def comparison_svg(rows):
    values = [abs(float(value)) for _, current, previous in rows for value in (current, previous) if value is not None]
    bound = max(values, default=0.01) * 1.2
    width, left, right, row_height = 740, 230, 60, 62
    zero, scale = (width - left - right) / 2 + left, (width - left - right) / (2 * bound)
    palette = ["#5470c6", "#91cc75", "#fac858", "#ee6666", "#73c0de", "#3ba272"]
    pale = ["#b7c4e7", "#c8e6ba", "#fde4a4", "#f6b5b5", "#bfe4ef", "#b5ddcf"]
    parts = [f"<svg viewBox='0 0 {width} {len(rows) * row_height + 24}' width='100%' role='img'>"]
    parts.append(f"<line x1='{zero}' y1='5' x2='{zero}' y2='{len(rows) * row_height}' stroke='#728096' stroke-dasharray='5 4'/>")
    for index, (name, current, previous) in enumerate(rows):
        y = index * row_height + 10
        parts.append(f"<text x='5' y='{y + 15}' fill='#20221f' font-size='13'>{html.escape(str(name))}</text>")
        for value, colour, y_offset in ((current, palette[index % len(palette)], y), (previous, pale[index % len(pale)], y + 25)):
            if value is None:
                continue
            value = float(value)
            x, bar_width = (zero, value * scale) if value >= 0 else (zero + value * scale, -value * scale)
            label_x, anchor = (x + bar_width + 7, "start") if value >= 0 else (x - 7, "end")
            parts.append(f"<rect x='{x}' y='{y_offset}' width='{max(bar_width, 1)}' height='17' rx='3' fill='{colour}'/>")
            parts.append(f"<text x='{label_x}' y='{y_offset + 13}' text-anchor='{anchor}' fill='#354154' font-size='11'>{percent(value)}</text>")
    return "".join(parts) + "</svg>"


def report_page(report):
    st.caption("已发布研究成果 · stlite 浏览器验证")
    st.title(report["title"])
    st.caption(f"报告期：{report['period']}")
    st.info(report.get("summary", "暂无摘要"))
    highlights = report.get("highlights", {})
    kpis = st.columns(3)
    kpis[0].metric("重点节点", highlights.get("selected_node_count", 0))
    kpis[1].metric("观察标签", len(highlights.get("tags", [])))
    kpis[2].metric("重点公司", len(report.get("company_focus", [])))

    charts = report.get("charts", [])
    line = next((item for item in charts if item.get("type") == "line"), None)
    comparison = next((item for item in charts if item.get("type") in ("grouped_bar", "bar")), None)
    left, right = st.columns(2)
    with left:
        st.subheader(line.get("title", "关键节点趋势") if line else "关键节点趋势")
        if line:
            field = line.get("metric", {}).get("field", "node_return")
            series = {}
            for item in line.get("data", []):
                series.setdefault(item.get("node_name", ""), []).append(float(item.get(field) or 0))
            st.line_chart(series, height=300)
    with right:
        st.subheader(comparison.get("title", "关键节点收益率对比") if comparison else "关键节点收益率对比")
        if comparison:
            st.markdown(comparison_svg(comparison_rows(report, comparison)), unsafe_allow_html=True)
            st.caption("深色为本期　浅色为上一期")

    st.subheader("重点公司")
    visible_columns = ["company_name", "node_name", "current_return", "period_return", "excess_return", "amount_change", "focus_rank", "rank_change"]
    rows = [{key: item.get(key) for key in visible_columns} for item in report.get("company_focus", [])]
    st.dataframe(rows, use_container_width=True, hide_index=True)


def graph_page(graph):
    st.caption("已发布研究成果 · stlite 浏览器验证")
    st.title("产业链图谱")
    nodes, relations = graph.get("nodes", []), graph.get("relations", [])
    st.caption(f"共 {len(nodes)} 个节点 · {len(relations)} 条公开关系")
    labels = {"U": "上游", "M": "中游", "D": "下游"}
    columns = st.columns(3)
    for column, stream in zip(columns, ("U", "M", "D")):
        with column:
            st.subheader(labels[stream])
            for node in (item for item in nodes if item.get("stream") == stream):
                st.markdown(f"**{node['name']}**  \\n层级 {node.get('level', '—')}")
    st.subheader("公开关系")
    names = {item["id"]: item["name"] for item in nodes}
    st.dataframe(
        [
            {
                "起点": names.get(item.get("source_node_id"), item.get("source_node_id")),
                "终点": names.get(item.get("target_node_id"), item.get("target_node_id")),
                "关系": item.get("name") or item.get("relation_group", "关联"),
            }
            for item in relations
        ],
        use_container_width=True,
        hide_index=True,
    )


st.set_page_config(page_title="机器人产业研究台", layout="wide")
st.markdown(
    """
    <style>
    :root { --paper:#f3f1eb; --card:#fbfaf6; --ink:#20221f; --muted:#75776f; --line:#d9d6cc; --orange:#ee713b; }
    [data-testid="stAppViewContainer"] { background:var(--paper); }
    [data-testid="stHeader"] { display:none; }
    [data-testid="stMainBlockContainer"] { padding-top:.8rem; max-width:1200px; }
    [data-testid="stMetric"] { background:var(--card); border:1px solid var(--line); border-radius:18px; padding:14px; }
    </style>
    """,
    unsafe_allow_html=True,
)

with open("data/publications.json", encoding="utf-8") as source:
    snapshot = json.load(source)
daily = next(item for item in snapshot["publications"] if item["type"] == "daily")
page = st.radio("公开栏目", ["每日关注", "产业链图谱"], horizontal=True, label_visibility="collapsed")
if page == "每日关注":
    report_page(daily)
else:
    graph_page(snapshot["graph"])
