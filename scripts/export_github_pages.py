#!/usr/bin/env python3
"""Build a framework-independent GitHub Pages artifact from the verified data snapshot."""

from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = PROJECT_DIR / "snapshot/data_platform_snapshot.json"
PUBLIC_DIR = PROJECT_DIR / "public"
DEFAULT_OUTPUT = PROJECT_DIR / "github-pages-dist"
BLOCKED_UI_TERMS = (
    "研究结论",
    "管理层表态",
    "研究缺口",
    "research_output_id",
    "finding_id",
    "statement_id",
)


class PagesExportError(RuntimeError):
    pass


def e(value: Any) -> str:
    return html.escape(str(value or ""), quote=True)


def shell(title: str, body: str, page_data: dict[str, Any] | None = None) -> str:
    data_script = ""
    if page_data is not None:
        encoded = json.dumps(page_data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        data_script = f'<script id="page-data" type="application/json">{encoded}</script>'
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="index, follow">
  <meta name="description" content="财报预报与公司财务数据浏览平台。">
  <title>{e(title)} · 云见财报</title>
  <link rel="icon" href="/favicon.svg">
  <link rel="stylesheet" href="/site-shell.css">
  <link rel="stylesheet" href="/snapshot-styles.css">
  <link rel="stylesheet" href="/snapshot-polish.css">
</head>
<body>
  <header class="topbar">
    <a class="brand" href="/"><span class="brand-mark">云见</span><span><strong>云见财报</strong><small>财报数据平台 · 只读</small></span></a>
    <nav class="primary-nav" aria-label="一级功能"><a href="/earnings/">财报预报</a><a href="/">公司 / 财报数据</a></nav>
  </header>
  <main>{body}</main>
  <footer><span>派生快照 · ResearchOS production 仍是唯一事实源</span><span>财报预报与财务数据 · 无写回能力</span></footer>
  {data_script}
  <script src="/snapshot-app.js" defer></script>
</body>
</html>
'''


def load_snapshot() -> dict[str, Any]:
    try:
        payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PagesExportError("verified data-platform snapshot is missing or invalid") from exc
    if (
        payload.get("schema_version") != "ResearchOS-DataPlatformSnapshot-0.1"
        or payload.get("access_intent") != "public_financial_data_platform"
        or payload.get("derived") is not True
        or payload.get("authoritative") is not False
        or payload.get("production_mutation") is not False
    ):
        raise PagesExportError("snapshot is not a verified public financial-data artifact")
    pages = payload.get("company_pages")
    if not isinstance(pages, dict) or not pages:
        raise PagesExportError("snapshot has no company data pages")
    if not isinstance(payload.get("earnings_calendar"), list):
        raise PagesExportError("snapshot has no earnings calendar")
    return payload


def home_body(payload: dict[str, Any]) -> str:
    cards = []
    for company in payload["company_pages"].values():
        cards.append(
            f'<a class="company-card company-card-link" href="/company/{e(company["company_id"])}/">'
            f'<div class="company-card-head"><div><p class="eyebrow">{e(company.get("market") or "公司财报数据")}</p>'
            f'<h2>{e(company.get("company"))}</h2><p>{e(company.get("ticker") or company["company_id"])}</p></div>'
            f'<span class="status-dot"></span></div><div class="card-metrics">'
            f'<div><small>最新财报期</small><strong>{e(company.get("target_period") or "—")}</strong></div>'
            f'<div><small>历史期间</small><strong>{company.get("financial_period_count", 0)}</strong></div>'
            f'<div><small>数据指标</small><strong>{company.get("metric_count", 0)}</strong></div></div>'
            '<div class="card-footer single"><span class="arrow">查看数据 →</span></div></a>'
        )
    summary = payload["summary"]
    return (
        '<section class="hero"><div><p class="eyebrow">云见财报 ResearchOS</p><h1>财报预报与公司财务数据</h1>'
        '<p>查看即将发布的财报，也可按公司浏览历史指标、同比环比与数据覆盖。</p>'
        '<div class="hero-actions"><a class="button-link" href="/earnings/">查看财报预报</a><a class="text-link" href="#companies">浏览公司数据</a></div></div></section>'
        f'<section class="summary-strip"><div><small>数据公司</small><strong>{summary["company_count"]}</strong></div>'
        f'<div><small>即将发布</small><strong>{summary["upcoming_event_count"]}</strong></div>'
        f'<div><small>已发布事件</small><strong>{summary["released_event_count"]}</strong></div>'
        '<div><small>数据模式</small><strong>只读</strong></div></section>'
        '<section class="section-heading" id="companies"><div><p class="eyebrow">公司 / 财报数据</p><h2>公司数据</h2></div>'
        '<p>选择公司后查看最新财报期及历史财务、运营数据。</p></section>'
        f'<section class="company-grid">{"".join(cards)}</section>'
    )


def format_datetime(value: Any, date_only: bool = False) -> str:
    if not value:
        return "—"
    normalized = str(value).replace("T", " ")
    return normalized[:10] if date_only else normalized[:16]


def release_display(event: dict[str, Any]) -> str:
    if event.get("actual_release_beijing"):
        return f'{format_datetime(event["actual_release_beijing"])}（北京时间）'
    if event.get("planned_release_beijing"):
        return f'{format_datetime(event["planned_release_beijing"])}（北京时间）'
    if event.get("official_appointment_date"):
        return f'{format_datetime(event["official_appointment_date"], True)}（官方日期，时间未披露）'
    if event.get("estimated_date"):
        return f'{format_datetime(event["estimated_date"], True)}（第三方预计）'
    return "待核实"


def event_table(events: list[dict[str, Any]], empty_text: str) -> str:
    if not events:
        return f'<div class="empty-state"><strong>{e(empty_text)}</strong></div>'
    rows = []
    for event in events:
        source = e(event.get("source_name") or "查看来源")
        if event.get("source_url"):
            source = f'<a class="source-link" href="{e(event["source_url"])}" target="_blank" rel="noreferrer">{source}</a>'
        call_time = f'{format_datetime(event.get("call_time_beijing"))}（北京时间）' if event.get("call_time_beijing") else "—"
        status_class = "released" if event.get("released") else "upcoming"
        rows.append(
            f'<tr><td><strong>{e(event.get("company"))}</strong><small>{e(event.get("ticker"))} · {e(event.get("market"))}</small></td>'
            f'<td><strong>{e(event.get("period"))}</strong><small>{e(event.get("report_type"))}</small></td>'
            f'<td>{e(release_display(event))}</td><td><span class="event-status {status_class}">{e(event.get("status"))}</span></td>'
            f'<td>{e(call_time)}</td><td>{source}<small>核查：{e(format_datetime(event.get("last_checked_at")))}</small></td></tr>'
        )
    return '<div class="table-scroll earnings-table"><table><thead><tr><th>公司</th><th>财报期间</th><th>发布时间</th><th>状态</th><th>电话会</th><th>来源</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table></div>"


def earnings_body(payload: dict[str, Any]) -> str:
    upcoming = [row for row in payload["earnings_calendar"] if not row.get("released")]
    released = [row for row in payload["earnings_calendar"] if row.get("released")]
    return (
        '<a class="back-link" href="/">← 返回公司数据</a><section class="section-heading forecast-heading">'
        '<div><p class="eyebrow">财报预报</p><h1>财报发布时间表</h1></div><p>精确时间仅展示官方已披露字段；只有日期时不推测具体时刻。</p></section>'
        f'<section class="calendar-section"><div class="section-heading compact"><div><p class="eyebrow">Upcoming</p><h2>即将发布</h2></div><p>{len(upcoming)} 条事件</p></div>{event_table(upcoming, "暂无已登记的即将发布事件")}</section>'
        f'<section class="calendar-section"><div class="section-heading compact"><div><p class="eyebrow">Released</p><h2>已发布</h2></div><p>{len(released)} 条事件</p></div>{event_table(released, "暂无已登记的已发布事件")}</section>'
    )


def export(output: Path) -> dict[str, Any]:
    payload = load_snapshot()
    output = output.resolve()
    if output == PROJECT_DIR or PROJECT_DIR not in output.parents:
        raise PagesExportError("output must be a dedicated directory inside the snapshot project")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / ".nojekyll").write_text("", encoding="utf-8")
    (output / "index.html").write_text(shell("公司财报数据", home_body(payload)), encoding="utf-8")
    earnings_dir = output / "earnings"
    earnings_dir.mkdir()
    (earnings_dir / "index.html").write_text(shell("财报预报", earnings_body(payload)), encoding="utf-8")
    for company_id, page in payload["company_pages"].items():
        destination = output / "company" / company_id
        destination.mkdir(parents=True)
        (destination / "index.html").write_text(
            shell(str(page.get("company") or company_id), page["html"], page["page_data"]),
            encoding="utf-8",
        )
    for name in ("favicon.svg", "snapshot-styles.css", "snapshot-polish.css", "snapshot-app.js"):
        source = PUBLIC_DIR / name
        if not source.is_file():
            raise PagesExportError(f"public asset missing: {name}")
        shutil.copy2(source, output / name)
    shutil.copy2(PROJECT_DIR / "app/globals.css", output / "site-shell.css")
    not_found = '<section class="error-page"><span class="error-code">404</span><h1>暂无这家公司的财报数据</h1><p>当前数据快照没有对应的公司页面。</p><small>不会使用其他公司的数据代替。</small><a class="button-link" href="/">返回公司列表</a></section>'
    (output / "404.html").write_text(shell("暂无公司数据", not_found), encoding="utf-8")
    manifest = {
        "schema_version": "ResearchOS-DataPlatformPages-manifest-0.1",
        "snapshot_id": payload["snapshot_id"],
        "snapshot_content_sha256": payload["snapshot_content_sha256"],
        "generated_at": payload["generated_at"],
        "derived": True,
        "authoritative": False,
        "production_mutation": False,
        "access_mode": "public",
        "company_ids": sorted(payload["company_pages"]),
        "routes": ["/", "/earnings/"] + [f"/company/{company_id}/" for company_id in sorted(payload["company_pages"])],
    }
    (output / "site-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def verify(output: Path) -> dict[str, Any]:
    output = output.resolve()
    manifest = json.loads((output / "site-manifest.json").read_text(encoding="utf-8"))
    required = [output / "index.html", output / "earnings/index.html", output / "404.html", output / ".nojekyll"]
    required += [output / "company" / company_id / "index.html" for company_id in manifest["company_ids"]]
    if not all(path.is_file() for path in required):
        raise PagesExportError("GitHub Pages artifact is incomplete")
    documents = [path.read_text(encoding="utf-8") for path in required if path.suffix == ".html"]
    if any(any(term in document for term in BLOCKED_UI_TERMS) for document in documents):
        raise PagesExportError("removed research UI leaked into static artifact")
    home = (output / "index.html").read_text(encoding="utf-8")
    if any(term in home for term in ("business / geography / product 独立保存", "readonly-badge", ">只读数据<")):
        raise PagesExportError("removed home-card or topbar labels leaked into static artifact")
    if any("/_next/" in document or "vinext.navigationRuntime" in document for document in documents):
        raise PagesExportError("framework runtime leaked into static artifact")
    if not all("财报数据平台 · 只读" in document for document in documents):
        raise PagesExportError("data-platform read-only identity missing")
    if (output / "snapshot/data_platform_snapshot.json").exists():
        raise PagesExportError("raw snapshot JSON must not be deployed")
    return {"status": "PASS", **manifest}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.output) if args.verify else export(args.output)
        if not args.verify:
            result = verify(args.output)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
