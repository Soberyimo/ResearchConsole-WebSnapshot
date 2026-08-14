#!/usr/bin/env python3
"""Build a framework-independent GitHub Pages artifact from the verified snapshot."""

from __future__ import annotations

import argparse
import html
import json
import shutil
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
SNAPSHOT_PATH = PROJECT_DIR / "snapshot/research_snapshot.json"
PUBLIC_DIR = PROJECT_DIR / "public"
DEFAULT_OUTPUT = PROJECT_DIR / "github-pages-dist"


class PagesExportError(RuntimeError):
    pass


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
  <meta name="description" content="云见财报 ResearchOS 的公开只读 Web Snapshot。">
  <title>{html.escape(title)} · Research Console</title>
  <link rel="icon" href="/favicon.svg">
  <link rel="stylesheet" href="/site-shell.css">
  <link rel="stylesheet" href="/snapshot-styles.css">
  <link rel="stylesheet" href="/snapshot-polish.css">
</head>
<body>
  <header class="topbar">
    <a class="brand" href="/"><span class="brand-mark">云见</span><span><strong>Research Console</strong><small>公开快照 · 只读</small></span></a>
    <div class="readonly-badge">Public Snapshot</div>
  </header>
  <main>{body}</main>
  <footer><span>派生快照 · ResearchOS production 仍是唯一事实源</span><span>Console v0.1.3 · 无写回能力</span></footer>
  {data_script}
  <script src="/snapshot-app.js" defer></script>
</body>
</html>
'''


def load_snapshot() -> dict[str, Any]:
    try:
        payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PagesExportError("verified snapshot is missing or invalid") from exc
    if (
        payload.get("schema_version") != "ResearchConsole-WebSnapshot-0.1"
        or payload.get("access_intent") != "public_github_pages"
        or payload.get("derived") is not True
        or payload.get("authoritative") is not False
        or payload.get("production_mutation") is not False
    ):
        raise PagesExportError("snapshot is not an authorized public derived artifact")
    pages = payload.get("company_pages")
    if not isinstance(pages, dict) or not pages:
        raise PagesExportError("snapshot has no company pages")
    for company_id, page in pages.items():
        if page.get("visibility") != "publishable" or not page.get("publication_decision_id"):
            raise PagesExportError(f"company is not formally publishable: {company_id}")
    return payload


def export(output: Path) -> dict[str, Any]:
    payload = load_snapshot()
    output = output.resolve()
    if output == PROJECT_DIR or PROJECT_DIR not in output.parents:
        raise PagesExportError("output must be a dedicated directory inside the snapshot project")
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    (output / ".nojekyll").write_text("", encoding="utf-8")
    (output / "index.html").write_text(shell("首页", payload["home_html"]), encoding="utf-8")
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
    not_found = '<section class="error-page"><span class="error-code">已安全停止显示 · 404</span><h1>尚无正式研究结果</h1><p>当前公开快照没有这家公司的正式研究结果。</p><small>不会使用暂存、试运行或其他公司的结果作为替代。</small><a class="button-link" href="/">返回公司列表</a></section>'
    (output / "404.html").write_text(shell("尚无正式研究结果", not_found), encoding="utf-8")
    manifest = {
        "schema_version": "ResearchConsole-GitHubPages-manifest-0.1",
        "snapshot_id": payload["snapshot_id"],
        "snapshot_content_sha256": payload["snapshot_content_sha256"],
        "generated_at": payload["generated_at"],
        "derived": True,
        "authoritative": False,
        "production_mutation": False,
        "access_mode": "public",
        "company_ids": sorted(payload["company_pages"]),
    }
    (output / "site-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


def verify(output: Path) -> dict[str, Any]:
    output = output.resolve()
    manifest = json.loads((output / "site-manifest.json").read_text(encoding="utf-8"))
    required = [output / "index.html", output / "404.html", output / ".nojekyll"]
    required += [output / "company" / company_id / "index.html" for company_id in manifest["company_ids"]]
    if not all(path.is_file() for path in required):
        raise PagesExportError("GitHub Pages artifact is incomplete")
    documents = [path.read_text(encoding="utf-8") for path in required if path.suffix == ".html"]
    if any("internal_only" in document or "Private Preview" in document for document in documents):
        raise PagesExportError("private visibility label leaked into public artifact")
    if any("/_next/" in document or "vinext.navigationRuntime" in document for document in documents):
        raise PagesExportError("framework runtime leaked into static artifact")
    if not all("公开快照 · 只读" in document for document in documents):
        raise PagesExportError("public read-only identity missing")
    if (output / "snapshot/research_snapshot.json").exists():
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
