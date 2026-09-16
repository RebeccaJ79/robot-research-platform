"""Portable public workflow: input JSON to a safe public publication snapshot."""
from __future__ import annotations

import argparse
import json
import os
import urllib.request
from pathlib import Path
from typing import Any


def _offline_snapshot(source: dict[str, Any]) -> dict[str, Any]:
    period = str(source.get("period", ""))
    items = source.get("items", [])
    first = items[0] if isinstance(items, list) and items and isinstance(items[0], dict) else {}
    return {"schema_version": "1.0", "publications": [{"id": f"daily-{period}", "type": "daily", "period": period, "title": "每日关注", "summary": str(first.get("summary", "暂无已发布摘要。"))}], "graph": {"nodes": [], "relations": []}, "cases": [{"模型审核": "离线样例未调用模型", "程序校验": "通过", "自动修复": 0, "发布状态": "样例"}]}


def run(input_path: Path, output_path: Path, *, offline: bool) -> Path:
    source = json.loads(Path(input_path).read_text(encoding="utf-8"))
    if not offline and not os.environ.get("MODEL_API_KEY"):
        raise RuntimeError("MODEL_API_KEY_REQUIRED")
    if offline:
        snapshot = _offline_snapshot(source)
    else:
        base = os.environ.get("MODEL_BASE_URL", "").rstrip("/")
        model = os.environ.get("MODEL_NAME", "gpt-4o-mini")
        if not base: raise RuntimeError("MODEL_BASE_URL_REQUIRED")
        request_body = {"model": model, "response_format": {"type": "json_object"}, "messages": [{"role": "system", "content": "Return only a public JSON publication snapshot. Never include credentials, PDFs, paths, raw reviews, or full skills."}, {"role": "user", "content": json.dumps(source, ensure_ascii=False)}]}
        request = urllib.request.Request(f"{base}/chat/completions", data=json.dumps(request_body).encode("utf-8"), headers={"Authorization": f"Bearer {os.environ['MODEL_API_KEY']}", "Content-Type": "application/json"})
        with urllib.request.urlopen(request, timeout=60) as response:
            payload = json.loads(response.read().decode("utf-8"))
        snapshot = json.loads(payload["choices"][0]["message"]["content"])
        if snapshot.get("schema_version") != "1.0": raise RuntimeError("MODEL_OUTPUT_SCHEMA_INVALID")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True); parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(); print(run(args.input, args.output, offline=args.offline))
