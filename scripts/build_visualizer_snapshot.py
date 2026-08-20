#!/usr/bin/env python3
"""Build the frontend snapshot from GPT-style JSON or CSV without financial calculations."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import os
import re
import tempfile
from collections import defaultdict
from pathlib import Path
from typing import Any

from structured_data import load_records, validate_records


PROJECT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = PROJECT_DIR / "structured_data/financial_records.json"
COMPANY_MANIFEST_DIR = PROJECT_DIR / "structured_data/company_manifests"
OUTPUT_PATH = PROJECT_DIR / "snapshot/visualizer_snapshot.json"
SCHEMA_VERSION = "Yunjian-VisualizerSnapshot-1"

METRIC_LABELS = {
    "administrative_expense": "管理费用",
    "aito_m5_sales": "问界 M5 销量",
    "aito_m6_sales": "问界 M6 销量",
    "aito_m7_sales": "问界 M7 销量",
    "aito_m8_sales": "问界 M8 销量",
    "aito_m9_sales": "问界 M9 销量",
    "aito_model_sales_total": "问界车型销量合计",
    "cost_of_sales": "营业成本 / 销售成本",
    "finance_expense": "财务费用",
    "gross_margin": "毛利率",
    "gross_profit": "毛利",
    "net_margin_consolidated": "净利率",
    "net_profit_attributable": "归母净利润",
    "net_profit_consolidated": "合并净利润",
    "nev_sales": "新能源汽车销量",
    "nev_sales_share": "新能源占比",
    "other_vehicle_sales": "其他车型销量",
    "rd_expense": "研发费用",
    "revenue": "营业收入",
    "selling_expense": "销售费用",
    "seres_auto_sales": "赛力斯汽车销量",
    "total_vehicle_sales": "总销量",
}
SERES_FINANCIAL_METRICS = {
    "revenue", "cost_of_sales", "gross_profit", "gross_margin",
    "net_profit_consolidated", "net_margin_consolidated", "net_profit_attributable",
    "rd_expense", "selling_expense", "administrative_expense", "finance_expense",
}
SERES_COMPANY_SALES_METRICS = {
    "total_vehicle_sales", "nev_sales", "nev_sales_share", "seres_auto_sales", "other_vehicle_sales",
}
SERES_MODEL_SALES_METRICS = {
    "aito_m5_sales", "aito_m6_sales", "aito_m7_sales", "aito_m8_sales", "aito_m9_sales",
    "aito_model_sales_total",
}
SERES_CORE_ORDER = [
    "revenue", "cost_of_sales", "gross_profit", "gross_margin", "net_profit_consolidated",
    "net_margin_consolidated", "net_profit_attributable", "rd_expense", "selling_expense",
    "administrative_expense", "finance_expense",
]
PERIOD_TYPE_LABELS = {
    "month": "月度",
    "quarter": "季度",
    "half": "半年",
    "fy": "年度",
    "point_in_time": "时点",
    "ytd6": "半年累计",
    "ytd9": "九个月累计",
}
SOURCE_TYPE_LABELS = {
    "company_disclosed": "公司披露",
    "program_calculated": "确定性计算",
    "external_research": "外部数据",
    "management_forward_looking": "管理层前瞻",
    "gpt_estimate": "GPT 估算",
    "user_material": "用户材料",
}
STATUS_LABELS = {"verified": "已核实", "needs_review": "待复核", "missing": "缺失"}


def stable_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def e(value: Any) -> str:
    return html.escape(str(value if value is not None else ""), quote=True)


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


def load_company_manifests() -> dict[str, dict[str, Any]]:
    manifests: dict[str, dict[str, Any]] = {}
    if not COMPANY_MANIFEST_DIR.exists():
        return manifests
    for path in sorted(COMPANY_MANIFEST_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8"))
        company = payload.get("company")
        if not isinstance(company, str) or not company:
            raise ValueError(f"company manifest missing company: {path.name}")
        manifests[company] = payload
    return manifests


def company_slug(company: str, manifest: dict[str, Any] | None = None) -> str:
    recommended = (manifest or {}).get("recommended_site_slug")
    if isinstance(recommended, str) and re.fullmatch(r"[a-z0-9-]+", recommended):
        return recommended
    return "company-" + sha256_bytes(company.encode("utf-8"))[:12]


def infer_period_type(period: Any) -> str:
    value = str(period or "")
    if re.fullmatch(r"\d{4}-\d{2}", value):
        return "month"
    if re.fullmatch(r"\d{4}Q[1-4]", value):
        return "quarter"
    if re.fullmatch(r"\d{4}H[12]", value):
        return "half"
    if re.fullmatch(r"(?:\d{4}FY|FY\d{4})", value):
        return "fy"
    return "unspecified"


def period_sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    end_date = str(record.get("period_end_date") or "")
    if end_date:
        return (end_date, 9, str(record.get("period") or ""))
    period = str(record.get("period") or "")
    match = re.fullmatch(r"(\d{4})-(\d{2})", period)
    if match:
        return (f"{match.group(1)}-{match.group(2)}", 1, period)
    match = re.fullmatch(r"(\d{4})Q([1-4])", period)
    if match:
        return (f"{match.group(1)}-{int(match.group(2)) * 3:02d}", 2, period)
    match = re.fullmatch(r"(\d{4})H([12])", period)
    if match:
        return (f"{match.group(1)}-{6 if match.group(2) == '1' else 12:02d}", 3, period)
    match = re.fullmatch(r"(\d{4})FY", period) or re.fullmatch(r"FY(\d{4})", period)
    if match:
        return (f"{match.group(1)}-12", 4, period)
    return (period, 0, period)


def normalized_record(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["period_type"] = result.get("period_type") or infer_period_type(result.get("period"))
    result["metric_name"] = result.get("metric_name") or METRIC_LABELS.get(str(result.get("metric"))) or result.get("metric")
    return result


def format_value(value: Any, unit: str | None) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return "—"
    if unit == "%":
        return f"{value:,.2f}"
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"


def comparison_view(value: Any, suffix: str = "%") -> str:
    if value is None:
        return '<span class="muted" title="输入未提供">—</span>'
    css_class = "positive" if value > 0 else "negative" if value < 0 else ""
    return f'<span class="{css_class}" title="由输入文件直接提供">{value:+.2f}{e(suffix)}</span>'


def base_label(record: dict[str, Any]) -> str:
    metric = str(record.get("metric_name") or record.get("metric") or "未命名指标")
    scope = str(record.get("scope") or "group")
    return metric if scope in {"group", "AITO_model"} else f"{scope} · {metric}"


def series_key(record: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(record.get(field) or "") for field in (
        "metric", "scope", "business", "geography", "product", "unit", "currency",
        "basis", "measurement_basis", "period_type",
    ))


def build_series(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[series_key(record)].append(record)
    series: list[dict[str, Any]] = []
    for identity, rows in grouped.items():
        rows.sort(key=period_sort_key)
        first = rows[-1]
        label = base_label(first)
        series.append({
            "series_id": "series_" + sha256_bytes("|".join(identity).encode("utf-8"))[:16],
            "metric": first.get("metric"),
            "base_label": label,
            "label": label,
            "unit": first.get("unit"),
            "basis": first.get("basis") or "",
            "period_type": first.get("period_type"),
            "records": [{
                "period": row.get("period"),
                "period_type": row.get("period_type"),
                "period_start_date": row.get("period_start_date"),
                "period_end_date": row.get("period_end_date"),
                "value": row.get("value"),
                "unit": row.get("unit"),
                "currency": row.get("currency"),
                "qoq": {"value": row.get("qoq"), "reason_code": "input_value" if row.get("qoq") is not None else "input_not_provided"},
                "yoy": {"value": row.get("yoy"), "reason_code": "input_value" if row.get("yoy") is not None else "input_not_provided"},
                "yoy_pp": {"value": row.get("yoy_pp"), "reason_code": "input_value" if row.get("yoy_pp") is not None else "input_not_provided"},
                "source_type": row.get("source_type"),
                "source": row.get("source"),
                "source_url": row.get("source_url"),
                "source_location": row.get("source_location"),
                "status": row.get("status"),
                "formula": row.get("formula"),
                "note": row.get("note"),
            } for row in rows],
            "definition": first.get("metric_definition"),
            "scope_note": first.get("scope_note"),
        })

    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in series:
        by_label[item["label"]].append(item)
    for label, duplicates in by_label.items():
        if len(duplicates) < 2:
            continue
        for item in duplicates:
            qualifiers = [PERIOD_TYPE_LABELS.get(str(item.get("period_type")), str(item.get("period_type") or "未注明期间"))]
            if item.get("basis"):
                qualifiers.append(str(item["basis"]))
            item["label"] = f'{label}（{" · ".join(qualifiers)}）'
    labels = [item["label"] for item in series]
    if len(labels) != len(set(labels)):
        raise ValueError("series labels remain ambiguous after period/basis qualification")
    return sorted(series, key=lambda item: item["label"])


def series_groups_for_company(company: str, records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    if company != "赛力斯":
        return {"financial": build_series(records)}
    financial = [record for record in records if record.get("metric") in SERES_FINANCIAL_METRICS]
    company_sales = [record for record in records if record.get("metric") in SERES_COMPANY_SALES_METRICS]
    model_sales = [record for record in records if record.get("metric") in SERES_MODEL_SALES_METRICS]
    if len(financial) + len(company_sales) + len(model_sales) != len(records):
        raise ValueError("赛力斯存在未归类指标")
    groups = {
        "financial": build_series(financial),
        "company_sales": build_series(company_sales),
        "model_sales": build_series(model_sales),
    }
    preferred = {
        "financial": ("revenue", "quarter"),
        "company_sales": ("total_vehicle_sales", "month"),
        "model_sales": ("aito_model_sales_total", "month"),
    }
    for group, (metric, period_type) in preferred.items():
        groups[group].sort(key=lambda item: (
            0 if item.get("metric") == metric and item.get("period_type") == period_type else 1,
            item["label"],
        ))
    return groups


def table_html(series: list[dict[str, Any]], period_label: str) -> str:
    tables = []
    for index, item in enumerate(series):
        rows = []
        for record in item["records"]:
            source = e(record.get("source") or "来源待补充")
            if record.get("source_url"):
                source = f'<a class="source-link" href="{e(record["source_url"])}" target="_blank" rel="noreferrer">{source}</a>'
            formula = f'<small>公式：{e(record["formula"])}</small>' if record.get("formula") else ""
            note = f'<small>{e(record["note"])}</small>' if record.get("note") else ""
            yoy = comparison_view(record["yoy"]["value"]) if record["yoy"]["value"] is not None else comparison_view(record["yoy_pp"]["value"], "pp")
            rows.append(
                f'<tr><td><strong>{e(record.get("period"))}</strong><small>{e(record.get("period_start_date"))}'
                f'{" → " if record.get("period_start_date") or record.get("period_end_date") else ""}{e(record.get("period_end_date"))}</small></td>'
                f'<td><span class="metric-value">{e(format_value(record.get("value"), item["unit"]))}</span></td>'
                f'<td>{e(item["unit"])}</td><td>{comparison_view(record["qoq"]["value"])}</td><td>{yoy}</td>'
                f'<td><span class="nature">{e(SOURCE_TYPE_LABELS.get(record.get("source_type"), record.get("source_type")))}</span>'
                f'<small>{e(STATUS_LABELS.get(record.get("status"), record.get("status")))}</small>{formula}</td>'
                f'<td>{source}<small>{e(record.get("source_location"))}</small>{note}</td></tr>'
            )
        definition = ""
        if item.get("definition") or item.get("scope_note"):
            definition = (
                '<div class="definition-box"><p class="eyebrow">输入定义</p><div>'
                f'<strong>{e(item["label"])}</strong><p>{e(item.get("definition") or "")}</p>'
                f'<small>{e(item.get("scope_note") or "")}</small></div></div>'
            )
        period_type = PERIOD_TYPE_LABELS.get(str(item.get("period_type")), str(item.get("period_type") or "未注明期间"))
        tables.append(
            f'<details class="metric-table" {"open" if index == 0 else ""}><summary><span>{e(item["label"])}</span>'
            f'<small>{len(item["records"])} 期 · {e(period_type)} · {e(item["unit"])}</small></summary>'
            f'<div class="table-scroll"><table><thead><tr><th>{e(period_label)}</th><th>数值</th><th>单位</th><th>环比</th>'
            f'<th>同比 / 变化</th><th>来源身份 / 状态</th><th>来源与口径</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div>{definition}</details>'
        )
    return "".join(tables)


def section_html(group: str, series: list[dict[str, Any]], title: str, eyebrow: str, description: str, period_label: str) -> str:
    if not series:
        return ""
    options = "".join(f'<option value="{e(item["series_id"])}">{e(item["label"])}</option>' for item in series)
    return (
        f'<section class="data-section" id="{e(group)}"><div class="section-heading compact"><div><p class="eyebrow">{e(eyebrow)}</p>'
        f'<h2>{e(title)}</h2></div><p>{e(description)}</p></div>'
        f'<div class="chart-shell trend-widget" data-series-group="{e(group)}"><div class="chart-toolbar"><label>趋势指标'
        f'<select class="chart-series">{options}</select></label><div class="chart-unit"></div></div>'
        f'<canvas class="trend-chart" height="300" aria-label="{e(title)}趋势图"></canvas><div class="chart-legend"></div></div>'
        f'<div class="metric-tables">{table_html(series, period_label)}</div></section>'
    )


def core_financial_html(records: list[dict[str, Any]], latest_period: str) -> str:
    latest_rows = {str(row.get("metric")): row for row in records if row.get("period") == latest_period}
    cards = []
    for metric in SERES_CORE_ORDER:
        row = latest_rows.get(metric)
        if not row:
            continue
        cards.append(
            '<div class="core-metric-card">'
            f'<small>{e(METRIC_LABELS.get(metric, metric))}</small><strong>{e(format_value(row.get("value"), row.get("unit")))}</strong>'
            f'<span>{e(row.get("unit"))}</span></div>'
        )
    if not cards:
        return ""
    return (
        '<section class="core-financial"><div class="section-heading compact"><div><p class="eyebrow">核心财务</p>'
        f'<h2>{e(latest_period)} 财务数据</h2></div><p>最新财务期间仅由财务 records 判断；不使用销量期间推断。</p></div>'
        f'<div class="core-metric-grid">{"".join(cards)}</div></section>'
    )


def notes_html(manifest: dict[str, Any] | None) -> str:
    if not manifest:
        return ""
    notes = manifest.get("comparability_notes") or []
    sections = manifest.get("dataset_sections") or {}
    section_labels = {"financial": "财务数据", "sales": "公司销量", "model_sales": "问界车型销量"}
    section_items = "".join(
        f'<li><strong>{e(section_labels.get(key, key))}</strong><span>{e(value)}</span></li>'
        for key, value in sections.items()
    )
    note_items = "".join(f'<li>{e(note)}</li>' for note in notes)
    return (
        '<section class="methodology-notes" id="methodology"><div class="section-heading compact"><div>'
        '<p class="eyebrow">来源 / 口径说明</p><h2>输入边界</h2></div><p>以下说明原样读取自 GPT / 用户审核 manifest。</p></div>'
        f'<div class="methodology-grid"><div><h3>数据分区</h3><ul>{section_items}</ul></div>'
        f'<div><h3>可比性与口径</h3><ul>{note_items}</ul></div></div></section>'
    )


def render_company(
    company: str,
    ticker: str | None,
    company_records: list[dict[str, Any]],
    groups: dict[str, list[dict[str, Any]]],
    manifest: dict[str, Any] | None,
) -> str:
    financial_records = [record for record in company_records if company != "赛力斯" or record.get("metric") in SERES_FINANCIAL_METRICS]
    latest_financial = max(financial_records, key=period_sort_key)
    latest_period = str(latest_financial.get("period") or "")
    financial_period_count = len({record.get("period") for record in financial_records})
    status = "已核实" if company_records and all(record.get("status") == "verified" for record in company_records) else "输入只读"
    subtitle = ticker or ("GPT / 用户已审核结构化输入" if status == "已核实" else "结构化输入")
    financial_description = "年度、半年度与单季度序列独立展示；同比只显示输入文件已提供的值。" if company == "赛力斯" else "同比 / 环比仅在输入明确提供时展示"
    body = (
        '<a class="back-link" href="/">← 返回公司列表</a><section class="company-hero"><div>'
        f'<p class="eyebrow">Structured financial data</p><h1>{e(company)}</h1><p>{e(subtitle)}</p></div></section>'
        '<section class="company-overview">'
        f'<span><small>最新财务期</small><strong>{e(latest_period)}</strong></span>'
        f'<span><small>财务期间</small><strong>{financial_period_count}</strong></span>'
        f'<span><small>全部记录</small><strong>{len(company_records)}</strong></span>'
        f'<span class="internal-status">{e(status)}</span></section>'
    )
    if company == "赛力斯":
        body += core_financial_html(financial_records, latest_period)
    body += section_html("financial", groups["financial"], "财务历史趋势", "财务数据", financial_description, "财务期间")
    if company == "赛力斯":
        body += section_html(
            "company_sales", groups["company_sales"], "公司销量", "上市公司产销快报",
            "赛力斯汽车销量为上市公司产销快报口径，不等于问界品牌交付量。月度与季度 / 半年 / 年度序列独立展示。", "销量期间",
        )
        body += section_html(
            "model_sales", groups["model_sales"], "问界车型销量", "乘联会车型销量",
            "M5 / M6 / M7 / M8 / M9 与合计来自外部数据；不与上市公司产销快报自动相减或补差。", "销量期间",
        )
        body += notes_html(manifest)
    return body


def build(input_path: Path) -> dict[str, Any]:
    records = [normalized_record(record) for record in load_records(input_path)]
    validation = validate_records(records)
    manifests = load_company_manifests()
    by_company: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_company[str(record["company"])].append(record)
    pages: dict[str, dict[str, Any]] = {}
    for company, company_records in sorted(by_company.items()):
        manifest = manifests.get(company)
        slug = company_slug(company, manifest)
        groups = series_groups_for_company(company, company_records)
        financial_records = [record for record in company_records if company != "赛力斯" or record.get("metric") in SERES_FINANCIAL_METRICS]
        latest = max(financial_records, key=period_sort_key)
        ticker = next((row.get("ticker") for row in company_records if row.get("ticker")), None)
        pages[slug] = {
            "company_slug": slug,
            "company": company,
            "ticker": ticker,
            "target_period": latest.get("period"),
            "financial_period_count": len({record.get("period") for record in financial_records}),
            "metric_count": sum(len(series) for series in groups.values()),
            "record_count": len(company_records),
            "verified_record_count": sum(record.get("status") == "verified" for record in company_records),
            "html": render_company(company, ticker, company_records, groups, manifest),
            "page_data": {"series_groups": groups},
        }
    input_bytes = input_path.read_bytes()
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "authoritative": False,
        "production_mutation": False,
        "input_contract": "GPT-owned JSON/CSV; display-only parser",
        "input_file": str(input_path.relative_to(PROJECT_DIR)),
        "input_sha256": sha256_bytes(input_bytes),
        "summary": {
            "company_count": validation["companies"],
            "record_count": validation["records"],
            "verified_count": validation["verified"],
            "needs_review_count": validation["needs_review"],
            "program_calculated_count": validation["program_calculated"],
        },
        "company_pages": pages,
    }
    payload["snapshot_content_sha256"] = sha256_bytes(stable_json(payload).encode("utf-8"))
    return payload


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    try:
        payload = build(args.input)
        if args.verify:
            existing = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
            if existing != payload:
                raise ValueError("visualizer snapshot is stale")
        else:
            atomic_write(OUTPUT_PATH, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print(json.dumps({"status": "PASS", **payload["summary"], "snapshot_content_sha256": payload["snapshot_content_sha256"]}, ensure_ascii=False))
        return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, ensure_ascii=False))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
