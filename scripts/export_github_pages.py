#!/usr/bin/env python3
"""Build a framework-independent GitHub Pages artifact from static structured data."""

from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = PROJECT_DIR / "snapshot/visualizer_snapshot.json"
PUBLIC_DIR = PROJECT_DIR / "public"
DEFAULT_OUTPUT = PROJECT_DIR / "github-pages-dist"
BLOCKED_TERMS = (
    "ResearchOS",
    "canonical",
    "production",
    "财报预报",
    "研究结论",
    "管理层表态",
    "research_output_id",
    "record_id",
    "evidence_id",
    "material_id",
    "observation_key",
    "business=",
    "geography=",
    "product=consolidated",
    "AI抽取待复核",
    "自动校验通过",
    "唯一事实源",
    "structured records",
    "Structured financial data",
)


class PagesExportError(RuntimeError):
    pass


def e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


def shell(
    title: str,
    body: str,
    page_data: dict[str, Any] | None = None,
    asset_version: str | None = None,
) -> str:
    data_script = ""
    if page_data is not None:
        encoded = json.dumps(page_data, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
        data_script = f'<script id="page-data" type="application/json">{encoded}</script>'
    version = f"?v={e(asset_version[:16])}" if asset_version else ""
    return f'''<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="robots" content="index, follow">
  <meta name="description" content="看懂公司的收入、盈利、经营与销量变化。">
  <title>{e(title)} · 云见财报</title>
  <link rel="icon" href="/favicon.svg">
  <link rel="stylesheet" href="/site-shell.css{version}">
  <link rel="stylesheet" href="/snapshot-styles.css{version}">
  <link rel="stylesheet" href="/snapshot-polish.css{version}">
</head>
<body>
  <header class="topbar"><a class="brand" href="/"><span class="brand-mark">云见</span><span><strong>云见财报</strong><small>公司财务与经营数据</small></span></a></header>
  <main>{body}</main>
  <footer><span>云见财报</span><span>数据来源与口径可在公司页展开查看</span></footer>
  {data_script}
  <script src="/snapshot-app.js{version}" defer></script>
</body>
</html>
'''


def load_snapshot() -> dict[str, Any]:
    try:
        payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PagesExportError("visualizer snapshot is missing or invalid") from exc
    if (
        payload.get("schema_version") != "Yunjian-VisualizerSnapshot-1"
        or payload.get("authoritative") is not False
        or payload.get("production_mutation") is not False
        or not isinstance(payload.get("company_pages"), dict)
    ):
        raise PagesExportError("snapshot is not a valid display-only artifact")
    return payload


def home_body(payload: dict[str, Any]) -> str:
    grouped: dict[str, list[str]] = {}
    for company in payload["company_pages"].values():
        metrics = "".join(
            f'<div><small>{e(metric["label"])}</small><strong>{e(metric["value"])}</strong>'
            f'<span>{e(metric["unit"])} · {e(metric["period"])}</span></div>'
            for metric in company.get("featured_metrics", [])
        )
        card = (
            f'<a class="company-card company-card-link" href="/company/{e(company["company_slug"])}/">'
            f'<div class="company-card-head"><div><p class="eyebrow">{e(company["industry"])}</p>'
            f'<h2>{e(company["display_name"])}</h2><p>{e(company.get("ticker") or "A股口径")}</p></div>'
            f'<span class="latest-period"><small>最新财务期</small><strong>{e(company.get("target_period") or "—")}</strong></span></div>'
            f'<div class="card-reader-metrics">{metrics}</div>'
            '<div class="card-footer single"><span class="arrow">进入公司页 →</span></div></a>'
        )
        grouped.setdefault(str(company["industry"]), []).append(card)
    industries = "".join(
        f'<section class="industry-group"><div class="industry-heading"><h3>{e(industry)}</h3><span>{len(cards)} 家公司</span></div>'
        f'<div class="company-grid">{"".join(cards)}</div></section>'
        for industry, cards in grouped.items()
    )
    return (
        '<section class="hero reader-home-hero"><div><p class="eyebrow">云见财报</p><h1>看懂公司的收入、盈利、经营与销量变化</h1>'
        '<p>从核心指标开始，沿着趋势图进入历史明细；需要时再展开来源、公式与口径。</p>'
        '<div class="hero-actions"><a class="button-link" href="#companies">选择一家公司</a></div></div></section>'
        '<section class="section-heading home-company-heading" id="companies"><div><p class="eyebrow">公司速览</p><h2>从你关心的公司开始</h2></div>'
        '<p>卡片展示各公司现有数据中的最新财务期与少量核心指标。</p></section>'
        + industries
    )


def export(output: Path) -> dict[str, Any]:
    payload = load_snapshot()
    output = output.resolve()
    if output == PROJECT_DIR or PROJECT_DIR not in output.parents:
        raise PagesExportError("output must be a dedicated directory inside the project")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / ".nojekyll").write_text("", encoding="utf-8")
    asset_version = str(payload["snapshot_content_sha256"])
    (output / "index.html").write_text(
        shell("财报数据可视化", home_body(payload), asset_version=asset_version),
        encoding="utf-8",
    )
    for company_slug, page in payload["company_pages"].items():
        destination = output / "company" / company_slug
        destination.mkdir(parents=True)
        (destination / "index.html").write_text(
            shell(
                str(page.get("company") or company_slug),
                page["html"],
                page["page_data"],
                asset_version=asset_version,
            ),
            encoding="utf-8",
        )
    for name in ("favicon.svg", "snapshot-styles.css", "snapshot-polish.css", "snapshot-app.js"):
        source = PUBLIC_DIR / name
        if not source.is_file():
            raise PagesExportError(f"public asset missing: {name}")
        shutil.copy2(source, output / name)
    shutil.copy2(PROJECT_DIR / "app/globals.css", output / "site-shell.css")
    not_found = '<section class="error-page"><span class="error-code">404</span><h1>暂无这家公司的财报数据</h1><p>当前结构化输入没有对应的公司页面。</p><a class="button-link" href="/">返回公司列表</a></section>'
    (output / "404.html").write_text(shell("暂无公司数据", not_found), encoding="utf-8")
    manifest = {
        "schema_version": "Yunjian-VisualizerPages-1",
        "snapshot_content_sha256": payload["snapshot_content_sha256"],
        "input_sha256": payload["input_sha256"],
        "authoritative": False,
        "production_mutation": False,
        "company_slugs": sorted(payload["company_pages"]),
        "routes": ["/"] + [f"/company/{slug}/" for slug in sorted(payload["company_pages"])],
    }
    (output / "site-manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return verify(output)


def verify(output: Path) -> dict[str, Any]:
    manifest = json.loads((output / "site-manifest.json").read_text(encoding="utf-8"))
    required = [output / "index.html", output / "404.html", output / ".nojekyll"]
    required += [output / "company" / slug / "index.html" for slug in manifest["company_slugs"]]
    if not all(path.is_file() for path in required):
        raise PagesExportError("GitHub Pages artifact is incomplete")
    documents = [path.read_text(encoding="utf-8") for path in required if path.suffix == ".html"]
    versioned_documents = [(output / "index.html").read_text(encoding="utf-8")]
    versioned_documents += [
        (output / "company" / slug / "index.html").read_text(encoding="utf-8")
        for slug in manifest["company_slugs"]
    ]
    if any(any(term in document for term in BLOCKED_TERMS) for document in documents):
        raise PagesExportError("legacy infrastructure or research terms leaked into Pages")
    if any("/_next/" in document or "vinext.navigationRuntime" in document for document in documents):
        raise PagesExportError("framework runtime leaked into static artifact")
    if any("snapshot-app.js?v=" not in document for document in versioned_documents):
        raise PagesExportError("versioned static assets are required to prevent stale charts")
    if (output / "structured_data").exists() or (output / "snapshot").exists():
        raise PagesExportError("raw structured data must not be deployed")
    return {"status": "PASS", **manifest}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        result = verify(args.output) if args.verify else export(args.output)
        print(json.dumps(result, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
