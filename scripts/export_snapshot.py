#!/usr/bin/env python3
"""Export a fail-closed, non-authoritative Web Snapshot from ResearchOS production.

The exporter imports the frozen Research Console v0.1.3 reader and renderer. It
never calls a production writer and writes only inside this snapshot project.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import re
import shutil
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_DIR = Path(__file__).resolve().parents[1]
RESEARCHOS_ROOT = PROJECT_DIR.parent
CONSOLE_DIR = RESEARCHOS_ROOT / "00_系统/ResearchConsole_v0.1"
CONSOLE_ENTRY = CONSOLE_DIR / "research_console.py"
SNAPSHOT_PATH = PROJECT_DIR / "snapshot/research_snapshot.json"
PUBLIC_DIR = PROJECT_DIR / "public"

SNAPSHOT_SCHEMA = "ResearchConsole-WebSnapshot-0.1"
ALLOWED_VISIBILITIES = {"internal_only"}
MAIN_RE = re.compile(r"<main>(.*)</main><footer>", re.DOTALL)
PAGE_DATA_RE = re.compile(
    r'<script id="page-data" type="application/json">(.*?)</script>', re.DOTALL
)


class SnapshotError(RuntimeError):
    """A fail-closed snapshot export error."""


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass
        raise


def load_console_module():
    if not CONSOLE_ENTRY.is_file():
        raise SnapshotError("冻结的 Research Console v0.1.3 主程序不存在")
    spec = importlib.util.spec_from_file_location("frozen_research_console_v013", CONSOLE_ENTRY)
    if spec is None or spec.loader is None:
        raise SnapshotError("无法加载冻结的 Research Console v0.1.3")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if module.VERSION != "0.1.3":
        raise SnapshotError(f"Console 版本不是冻结的 v0.1.3：{module.VERSION}")
    return module


def extract_main(document: str) -> str:
    match = MAIN_RE.search(document)
    if not match:
        raise SnapshotError("冻结 Console 渲染结果缺少 main 区域")
    return match.group(1).replace("数据缓存更新于", "快照生成于")


def extract_page_data(document: str) -> dict[str, Any]:
    match = PAGE_DATA_RE.search(document)
    if not match:
        raise SnapshotError("公司页面缺少正式财务图表数据")
    payload = json.loads(match.group(1).replace("<\\/", "</"))
    if not isinstance(payload, dict):
        raise SnapshotError("公司页面图表数据格式无效")
    return payload


def build_snapshot() -> dict[str, Any]:
    console = load_console_module()
    loader = console.ResearchConsoleLoader(RESEARCHOS_ROOT)
    source_manifest = loader.source_manifest()
    model = loader.build_model(source_manifest=source_manifest)

    if model.get("derived") is not True:
        raise SnapshotError("Console read model 未标记为 derived")
    if any("staged" in path.casefold() or "dryrun" in path.casefold() for path in source_manifest):
        raise SnapshotError("source manifest 出现 staging / Dry Run")

    canonical_index = console.read_json(RESEARCHOS_ROOT / "05_研究结果/canonical_index.json")
    canonical_ids = {
        str(pointer.get("current_research_output_id") or "")
        for pointer in canonical_index.get("pointers", {}).values()
    }
    rendered_ids: set[str] = set()
    company_pages: dict[str, dict[str, Any]] = {}

    for company in model.get("companies", []):
        company_id = str(company.get("company_id") or "")
        for output in company.get("outputs", []):
            output_id = str(output.get("research_output_id") or "")
            rendered_ids.add(output_id)
            visibility = str(output.get("visibility") or "")
            if visibility not in ALLOWED_VISIBILITIES or output.get("publishable") is not False:
                raise SnapshotError(f"visibility 不满足 Private Preview 安全边界：{output_id}")

        if not company.get("has_canonical"):
            continue
        outputs = company.get("outputs") or []
        if not outputs:
            raise SnapshotError(f"公司标记有 canonical 但 output 为空：{company_id}")
        output = outputs[0]
        document = console.render_company(company, output)
        company_pages[company_id] = {
            "company_id": company_id,
            "company": company.get("company"),
            "ticker": company.get("ticker"),
            "research_output_id": output.get("research_output_id"),
            "revision": output.get("revision"),
            "visibility": output.get("visibility"),
            "html": extract_main(document),
            "page_data": extract_page_data(document),
        }

    if rendered_ids != canonical_ids:
        raise SnapshotError(
            "快照 output 集合与 production canonical index 不一致："
            f"rendered={sorted(rendered_ids)} canonical={sorted(canonical_ids)}"
        )

    generated_at = datetime.now().astimezone().isoformat(timespec="seconds")
    snapshot_seed = {
        "console_version": console.VERSION,
        "canonical_ids": sorted(canonical_ids),
        "source_manifest": source_manifest,
    }
    snapshot_id = "ws_" + sha256_bytes(stable_json(snapshot_seed).encode("utf-8"))[:24]
    payload: dict[str, Any] = {
        "schema_version": SNAPSHOT_SCHEMA,
        "snapshot_id": snapshot_id,
        "generated_at": generated_at,
        "derived": True,
        "authoritative": False,
        "production_mutation": False,
        "truth_source": "Local ResearchOS production remains the sole truth source and writer",
        "access_intent": "owner_only_private_preview",
        "source_console_version": console.VERSION,
        "canonical_index_updated_at": model.get("canonical_index_updated_at"),
        "source_manifest": source_manifest,
        "summary": model.get("summary"),
        "home_html": extract_main(console.render_home(model)),
        "company_pages": company_pages,
    }
    payload["snapshot_content_sha256"] = sha256_bytes(stable_json(payload).encode("utf-8"))
    return payload


def verify_snapshot(payload: dict[str, Any]) -> None:
    if payload.get("schema_version") != SNAPSHOT_SCHEMA:
        raise SnapshotError("snapshot schema 无效")
    if payload.get("derived") is not True or payload.get("authoritative") is not False:
        raise SnapshotError("snapshot 派生属性无效")
    if payload.get("production_mutation") is not False:
        raise SnapshotError("snapshot 错误标记了 production mutation")
    if payload.get("access_intent") != "owner_only_private_preview":
        raise SnapshotError("snapshot access intent 无效")
    expected = payload.get("snapshot_content_sha256")
    content = dict(payload)
    content.pop("snapshot_content_sha256", None)
    actual = sha256_bytes(stable_json(content).encode("utf-8"))
    if expected != actual:
        raise SnapshotError("snapshot content hash 不匹配")
    pages = payload.get("company_pages")
    if not isinstance(pages, dict) or not pages:
        raise SnapshotError("snapshot 没有 canonical 公司页面")
    for company_id, page in pages.items():
        if page.get("visibility") not in ALLOWED_VISIBILITIES:
            raise SnapshotError(f"snapshot visibility 无效：{company_id}")
        if not page.get("research_output_id") or not page.get("html"):
            raise SnapshotError(f"snapshot 公司页面不完整：{company_id}")


def export() -> dict[str, Any]:
    payload = build_snapshot()
    verify_snapshot(payload)
    encoded = (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
    atomic_write(SNAPSHOT_PATH, encoded)
    for source_name, target_name in (
        ("styles.css", "snapshot-styles.css"),
        ("polish.css", "snapshot-polish.css"),
        ("app.js", "snapshot-app.js"),
    ):
        source = CONSOLE_DIR / "static" / source_name
        if not source.is_file():
            raise SnapshotError(f"冻结 Console 展示资产缺失：{source_name}")
        atomic_write(PUBLIC_DIR / target_name, source.read_bytes())
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description="生成 Research Console 私密 Web Snapshot")
    parser.add_argument("--verify", action="store_true", help="验证已生成 snapshot")
    args = parser.parse_args()
    try:
        if args.verify:
            payload = json.loads(SNAPSHOT_PATH.read_text(encoding="utf-8"))
            verify_snapshot(payload)
        else:
            payload = export()
        print(
            json.dumps(
                {
                    "status": "PASS",
                    "snapshot_id": payload["snapshot_id"],
                    "company_count": len(payload["company_pages"]),
                    "canonical_output_count": payload["summary"]["canonical_output_count"],
                    "finding_count": payload["summary"]["finding_count"],
                    "production_mutation": payload["production_mutation"],
                },
                ensure_ascii=False,
            )
        )
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
