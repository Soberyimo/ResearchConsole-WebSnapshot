#!/usr/bin/env python3
"""Build a reader-facing static company visualizer without calculating financial facts."""

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
    "administrative_expense": "管理费用", "aito_m5_sales": "问界 M5 销量",
    "aito_m6_sales": "问界 M6 销量", "aito_m7_sales": "问界 M7 销量",
    "aito_m8_sales": "问界 M8 销量", "aito_m9_sales": "问界 M9 销量",
    "aito_model_sales_total": "问界车型销量合计", "cash_and_equivalents": "现金及现金等价物",
    "cost_of_sales": "营业成本 / 销售成本", "finance_expense": "财务费用",
    "gross_margin": "毛利率", "gross_profit": "毛利", "inventory": "存货",
    "net_income": "净利润", "net_margin_consolidated": "净利率",
    "net_profit_attributable": "归母净利润", "net_profit_consolidated": "合并净利润",
    "nev_sales": "新能源汽车销量", "nev_sales_share": "新能源占比",
    "operating_cash_flow": "经营活动现金流", "operating_income": "营业利润",
    "operating_margin": "营业利润率", "other_vehicle_sales": "其他车型销量",
    "rd_expense": "研发费用", "rnd_expense": "研发费用", "revenue": "营业收入",
    "revenue_share_of_group": "业务收入占比", "selling_expense": "销售费用",
    "seres_auto_sales": "赛力斯汽车销量", "sga_expense": "销售及管理费用",
    "total_vehicle_sales": "总销量", "vehicle_deliveries": "整车交付量",
}
UNIT_LABELS = {"CNY million": "百万元", "USD million": "百万美元", "vehicles": "辆"}
BUSINESS_LABELS = {
    "Automotive": "汽车业务", "Data Center": "数据中心", "QCT": "QCT",
    "Services and others": "服务及其他", "Vehicle sales": "整车销售",
}
PERIOD_TYPE_LABELS = {
    "month": "月度", "quarter": "季度", "half": "半年", "fy": "年度",
    "point_in_time": "时点", "ytd6": "半年累计", "ytd9": "九个月累计",
    "ytd_6m": "半年累计", "ytd_9m": "九个月累计", "unspecified": "其他",
}
SOURCE_TYPE_LABELS = {
    "company_disclosed": "公司披露", "program_calculated": "确定性计算",
    "external_research": "外部数据", "management_forward_looking": "管理层信息",
    "gpt_estimate": "估算输入", "user_material": "用户材料",
}
SERES_FINANCIAL_METRICS = {
    "revenue", "cost_of_sales", "gross_profit", "gross_margin", "net_profit_consolidated",
    "net_margin_consolidated", "net_profit_attributable", "rd_expense", "selling_expense",
    "administrative_expense", "finance_expense",
}
SERES_COMPANY_SALES_METRICS = {
    "total_vehicle_sales", "nev_sales", "nev_sales_share", "seres_auto_sales", "other_vehicle_sales",
}
SERES_MODEL_SALES_METRICS = {
    "aito_m5_sales", "aito_m6_sales", "aito_m7_sales", "aito_m8_sales", "aito_m9_sales",
    "aito_model_sales_total",
}
SALES_METRICS = SERES_COMPANY_SALES_METRICS | SERES_MODEL_SALES_METRICS | {"vehicle_deliveries"}
PROFITABILITY_METRICS = {
    "cost_of_sales", "gross_profit", "gross_margin", "net_income", "net_margin_consolidated",
    "net_profit_attributable", "net_profit_consolidated", "operating_income", "operating_margin",
}
OPERATIONS_METRICS = {
    "cash_and_equivalents", "inventory", "operating_cash_flow", "rd_expense", "rnd_expense",
    "selling_expense", "administrative_expense", "finance_expense", "sga_expense",
}
COMPANY_PRESENTATION = {
    "吉利汽车控股有限公司": {"display_name": "吉利汽车", "industry": "整车", "featured": ["revenue", "net_income", "vehicle_deliveries"]},
    "宁德时代": {"display_name": "宁德时代", "industry": "动力电池", "featured": ["revenue", "net_income", "operating_cash_flow"]},
    "小鹏汽车": {"display_name": "小鹏汽车", "industry": "整车", "featured": ["revenue", "gross_margin", "vehicle_deliveries"]},
    "理想汽车": {"display_name": "理想汽车", "industry": "整车", "featured": ["revenue", "gross_margin", "vehicle_deliveries"]},
    "英伟达": {"display_name": "英伟达", "industry": "半导体", "featured": ["revenue", "gross_margin", "net_income"]},
    "高通": {"display_name": "高通", "industry": "半导体", "featured": ["revenue", "operating_income", "net_income"]},
    "赛力斯": {"display_name": "赛力斯", "industry": "整车", "featured": ["revenue", "gross_margin", "net_profit_attributable"]},
}
SECTION_META = {
    "scale": ("规模与收入", "公司规模", "收入及业务规模的历史变化。"),
    "profitability": ("盈利与成本", "利润表现", "利润、成本与利润率按各自频率展示。"),
    "operations": ("经营与投入", "经营指标", "现金流、存货与费用投入等经营数据。"),
    "sales": ("销量与结构", "经营规模", "整车交付与销量数据，与财务序列分开展示。"),
    "company_sales": ("公司销量", "上市公司产销快报", "赛力斯汽车销量为上市公司产销快报口径，不等于问界品牌交付量。"),
    "model_sales": ("问界车型销量", "乘联会车型销量", "M5 / M6 / M7 / M8 / M9 与合计为外部数据，不与公司产销快报自动相减或补差。"),
}
GROUP_ORDER = ["scale", "profitability", "operations", "sales", "company_sales", "model_sales"]
PREFERRED_SERIES = {
    "scale": ("revenue", "quarter"), "profitability": ("gross_margin", "quarter"),
    "operations": ("operating_cash_flow", "quarter"), "sales": ("vehicle_deliveries", "quarter"),
    "company_sales": ("total_vehicle_sales", "month"), "model_sales": ("aito_model_sales_total", "month"),
}

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
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
    except Exception:
        try: os.unlink(temporary)
        except FileNotFoundError: pass
        raise

def load_company_manifests() -> dict[str, dict[str, Any]]:
    manifests: dict[str, dict[str, Any]] = {}
    if not COMPANY_MANIFEST_DIR.exists(): return manifests
    for path in sorted(COMPANY_MANIFEST_DIR.glob("*.json")):
        payload = json.loads(path.read_text(encoding="utf-8")); company = payload.get("company")
        if not isinstance(company, str) or not company: raise ValueError(f"company manifest missing company: {path.name}")
        manifests[company] = payload
    return manifests

def company_slug(company: str, manifest: dict[str, Any] | None = None) -> str:
    recommended = (manifest or {}).get("recommended_site_slug")
    if isinstance(recommended, str) and re.fullmatch(r"[a-z0-9-]+", recommended): return recommended
    return "company-" + sha256_bytes(company.encode("utf-8"))[:12]

def infer_period_type(period: Any) -> str:
    value = str(period or "")
    if re.fullmatch(r"\d{4}-\d{2}", value): return "month"
    if re.fullmatch(r"\d{4}Q[1-4]", value): return "quarter"
    if re.fullmatch(r"\d{4}H[12]", value): return "half"
    if re.fullmatch(r"(?:\d{4}FY|FY\d{4})", value): return "fy"
    return "unspecified"

def period_sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    end_date = str(record.get("period_end_date") or "")
    if end_date: return (end_date, 9, str(record.get("period") or ""))
    period = str(record.get("period") or "")
    match = re.fullmatch(r"(\d{4})-(\d{2})", period)
    if match: return (f"{match.group(1)}-{match.group(2)}", 1, period)
    match = re.fullmatch(r"(\d{4})Q([1-4])", period)
    if match: return (f"{match.group(1)}-{int(match.group(2)) * 3:02d}", 2, period)
    match = re.fullmatch(r"(\d{4})H([12])", period)
    if match: return (f"{match.group(1)}-{6 if match.group(2) == '1' else 12:02d}", 3, period)
    match = re.fullmatch(r"(\d{4})FY", period) or re.fullmatch(r"FY(\d{4})", period)
    if match: return (f"{match.group(1)}-12", 4, period)
    return (period, 0, period)

def normalized_record(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["period_type"] = result.get("period_type") or infer_period_type(result.get("period"))
    result["metric_name"] = result.get("metric_name") or METRIC_LABELS.get(str(result.get("metric"))) or result.get("metric")
    return result

def display_unit(unit: Any) -> str:
    return UNIT_LABELS.get(str(unit), str(unit or ""))

def format_value(value: Any, unit: str | None) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool): return "—"
    if unit == "%": return f"{value:,.2f}"
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"

def comparison_view(value: Any, suffix: str = "%") -> str:
    if value is None: return '<span class="muted">—</span>'
    css_class = "positive" if value > 0 else "negative" if value < 0 else ""
    return f'<span class="{css_class}">{value:+.2f}{e(suffix)}</span>'

def base_label(record: dict[str, Any]) -> str:
    metric = str(record.get("metric_name") or METRIC_LABELS.get(str(record.get("metric"))) or "未命名指标")
    business = record.get("business"); scope = str(record.get("scope") or "group")
    if not business and scope.startswith("business="): business = scope.split("=", 1)[1]
    if business: return f'{BUSINESS_LABELS.get(str(business), str(business))} · {metric}'
    return metric

def series_key(record: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(record.get(field) or "") for field in ("metric", "scope", "business", "geography", "product", "unit", "currency", "basis", "measurement_basis", "period_type"))

def build_series(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records: grouped[series_key(record)].append(record)
    series: list[dict[str, Any]] = []
    for identity, rows in grouped.items():
        rows.sort(key=period_sort_key); first = rows[-1]; label = base_label(first)
        series.append({
            "series_id": "series_" + sha256_bytes("|".join(identity).encode("utf-8"))[:16],
            "metric": first.get("metric"), "label": label, "unit": first.get("unit"),
            "display_unit": display_unit(first.get("unit")), "basis": first.get("basis") or "",
            "period_type": first.get("period_type"), "records": [{
                "period": row.get("period"), "period_type": row.get("period_type"),
                "period_start_date": row.get("period_start_date"), "period_end_date": row.get("period_end_date"),
                "value": row.get("value"), "unit": row.get("unit"), "currency": row.get("currency"),
                "qoq": row.get("qoq"), "yoy": row.get("yoy"), "yoy_pp": row.get("yoy_pp"),
                "source_type": row.get("source_type"), "source": row.get("source"),
                "source_url": row.get("source_url"), "source_location": row.get("source_location"),
                "formula": row.get("formula"), "note": row.get("note"),
            } for row in rows],
        })
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in series: by_label[item["label"]].append(item)
    for label, duplicates in by_label.items():
        if len(duplicates) < 2: continue
        for item in duplicates:
            qualifiers = [PERIOD_TYPE_LABELS.get(str(item.get("period_type")), "其他")]
            if item.get("basis") and item["basis"] not in {"reported_currency", "company_operating_metric"}:
                qualifiers.append(str(item["basis"]).replace("_attributable_to_parent", ""))
            item["label"] = f'{label}（{" · ".join(qualifiers)}）'
    labels = [item["label"] for item in series]
    if len(labels) != len(set(labels)): raise ValueError("series labels remain ambiguous")
    return sorted(series, key=lambda item: item["label"])

def metric_group(metric: str) -> str:
    if metric in SALES_METRICS: return "sales"
    if metric in PROFITABILITY_METRICS: return "profitability"
    if metric in OPERATIONS_METRICS: return "operations"
    return "scale"

def series_groups_for_company(company: str, records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    buckets: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        metric = str(record.get("metric"))
        if company == "赛力斯" and metric in SERES_COMPANY_SALES_METRICS: group = "company_sales"
        elif company == "赛力斯" and metric in SERES_MODEL_SALES_METRICS: group = "model_sales"
        else: group = metric_group(metric)
        buckets[group].append(record)
    groups = {group: build_series(rows) for group, rows in buckets.items() if rows}
    for group, items in groups.items():
        metric, period_type = PREFERRED_SERIES[group]
        items.sort(key=lambda item: (0 if item.get("metric") == metric and item.get("period_type") == period_type else 1, item["label"]))
    return dict(sorted(groups.items(), key=lambda pair: GROUP_ORDER.index(pair[0])))

def latest_comparison(record: dict[str, Any]) -> tuple[Any, str]:
    if record.get("yoy") is not None: return record.get("yoy"), "%"
    if record.get("yoy_pp") is not None: return record.get("yoy_pp"), "pp"
    return None, "%"

def summary_rows_html(item: dict[str, Any], limit: int = 6) -> str:
    rows = []
    for record in list(reversed(item["records"]))[:limit]:
        comparison, suffix = latest_comparison(record)
        rows.append(f'<tr><td>{e(record.get("period"))}</td><td><strong>{e(format_value(record.get("value"), item.get("unit")))}</strong> <small>{e(item.get("display_unit"))}</small></td><td>{comparison_view(comparison, suffix)}</td></tr>')
    return "".join(rows)

def source_details(record: dict[str, Any]) -> str:
    source = e(record.get("source") or "来源说明未提供")
    if record.get("source_url"): source = f'<a class="source-link" href="{e(record["source_url"])}" target="_blank" rel="noreferrer">{source}</a>'
    parts = [f'<span class="source-badge">{e(SOURCE_TYPE_LABELS.get(record.get("source_type"), "来源"))}</span>', f'<p>{source}</p>']
    blocked = re.compile(r"ResearchOS|canonical|production|record_id|evidence_id|material_id|observation_key|business=|geography=|product=consolidated", re.I)
    source_location = record.get("source_location")
    formula = record.get("formula")
    note = record.get("note")
    if source_location and not blocked.search(str(source_location)): parts.append(f'<small>位置：{e(source_location)}</small>')
    if formula and not blocked.search(str(formula)): parts.append(f'<small>公式：{e(formula)}</small>')
    if note and not blocked.search(str(note)): parts.append(f'<small>说明：{e(note)}</small>')
    return "".join(parts)

def all_data_html(series: list[dict[str, Any]], period_label: str) -> str:
    metrics = []
    for item in series:
        rows = []
        for record in reversed(item["records"]):
            comparison, suffix = latest_comparison(record)
            rows.append(f'<tr><td><strong>{e(record.get("period"))}</strong></td><td>{e(format_value(record.get("value"), item.get("unit")))} <small>{e(item.get("display_unit"))}</small></td><td>{comparison_view(record.get("qoq"))}</td><td>{comparison_view(comparison, suffix)}</td><td><details class="row-source"><summary>查看</summary><div>{source_details(record)}</div></details></td></tr>')
        metrics.append(f'<details class="metric-table"><summary><span>{e(item["label"])}</span><small>{e(PERIOD_TYPE_LABELS.get(str(item.get("period_type")), "其他"))}</small></summary><div class="table-scroll"><table><thead><tr><th>{e(period_label)}</th><th>数值</th><th>环比</th><th>同比 / 变化</th><th>来源与口径</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></details>')
    return '<details class="all-data-details"><summary>查看全部数据与来源</summary><div class="metric-tables">' + "".join(metrics) + "</div></details>"

def option_html(series: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in series: grouped[PERIOD_TYPE_LABELS.get(str(item.get("period_type")), "其他")].append(item)
    ordered = ["月度", "季度", "半年", "半年累计", "九个月累计", "年度", "时点", "其他"]
    return "".join(f'<optgroup label="{e(label)}">' + "".join(f'<option value="{e(item["series_id"])}">{e(item["label"])}</option>' for item in grouped[label]) + '</optgroup>' for label in ordered if grouped.get(label))

def section_html(group: str, series: list[dict[str, Any]]) -> str:
    title, eyebrow, description = SECTION_META[group]; first = series[0]
    period_label = "销量期间" if group in {"sales", "company_sales", "model_sales"} else "财务期间"
    return f'<section class="data-section" id="{e(group)}"><div class="section-heading compact"><div><p class="eyebrow">{e(eyebrow)}</p><h2>{e(title)}</h2></div><p>{e(description)}</p></div><div class="reader-data-layout"><div class="chart-shell trend-widget" data-series-group="{e(group)}"><div class="chart-toolbar"><label><span>选择指标与频率</span><select class="chart-series">{option_html(series)}</select></label><div class="chart-unit"></div></div><canvas class="trend-chart" height="300" aria-label="{e(title)}趋势图"></canvas><div class="chart-legend"></div></div><div class="key-data"><div class="key-data-head"><h3>关键数据</h3><span>最近 6 期</span></div><div class="table-scroll"><table><thead><tr><th>期间</th><th>数值</th><th>同比 / 变化</th></tr></thead><tbody class="key-data-body">{summary_rows_html(first)}</tbody></table></div></div></div>{all_data_html(series, period_label)}</section>'

def choose_record(records: list[dict[str, Any]], metric: str, preferred_period: str | None = None) -> dict[str, Any] | None:
    candidates = [row for row in records if row.get("metric") == metric]
    group_candidates = [row for row in candidates if row.get("scope") in {None, "", "group"}]
    if group_candidates: candidates = group_candidates
    if preferred_period:
        same_period = [row for row in candidates if row.get("period") == preferred_period]
        if same_period: candidates = same_period
    return max(candidates, key=period_sort_key) if candidates else None

def metric_cards_html(records: list[dict[str, Any]], company: str, latest_period: str) -> str:
    cards = []
    for metric in COMPANY_PRESENTATION[company]["featured"]:
        row = choose_record(records, metric, latest_period)
        if not row: continue
        cards.append(f'<article class="reader-metric-card"><small>{e(METRIC_LABELS.get(metric, row.get("metric_name") or metric))}</small><strong>{e(format_value(row.get("value"), row.get("unit")))}</strong><span>{e(display_unit(row.get("unit")))} · {e(row.get("period"))}</span></article>')
    return '<section class="reader-metric-grid" id="overview">' + "".join(cards) + '</section>'

def quick_nav_html(groups: dict[str, list[dict[str, Any]]]) -> str:
    links = ['<a href="#overview">概览</a>']
    links += [f'<a href="#{e(group)}">{e(SECTION_META[group][0])}</a>' for group in groups]
    links.append('<a href="#methodology">来源与口径</a>')
    return '<nav class="section-nav" aria-label="公司页快速导航">' + "".join(links) + '</nav>'

def notes_html(manifest: dict[str, Any] | None) -> str:
    if not manifest: return '<section class="methodology-notes" id="methodology"><details><summary>阅读与来源说明</summary><p>各指标的来源、公式和备注可在“查看全部数据与来源”中逐项展开。</p></details></section>'
    note_items = "".join(f'<li>{e(note)}</li>' for note in (manifest.get("comparability_notes") or []))
    return '<section class="methodology-notes" id="methodology"><details><summary>来源与口径说明</summary><div class="methodology-content"><p>以下边界来自本次提供的数据说明。</p><ul>' + note_items + '</ul></div></details></section>'

def chart_groups(groups: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {group: [{"series_id": item["series_id"], "label": item["label"], "unit": item["unit"], "display_unit": item["display_unit"], "records": [{"period": row["period"], "value": row["value"], "qoq": row.get("qoq"), "yoy": row.get("yoy"), "yoy_pp": row.get("yoy_pp")} for row in item["records"]]} for item in series] for group, series in groups.items()}

def financial_records_for_company(company: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if company == "赛力斯": return [row for row in records if row.get("metric") in SERES_FINANCIAL_METRICS]
    return [row for row in records if row.get("metric") not in SALES_METRICS]

def render_company(company: str, ticker: str | None, records: list[dict[str, Any]], groups: dict[str, list[dict[str, Any]]], manifest: dict[str, Any] | None) -> str:
    config = COMPANY_PRESENTATION[company]; financial_records = financial_records_for_company(company, records)
    latest_period = str(max(financial_records, key=period_sort_key).get("period") or "")
    identity = " · ".join(value for value in (ticker, str(config["industry"])) if value)
    sales_link = '<a class="hero-shortcut" href="#company_sales">直接看销量 →</a>' if company == "赛力斯" else ""
    body = f'<a class="back-link" href="/">← 返回公司列表</a><section class="company-hero reader-company-hero"><div><p class="eyebrow">{e(config["industry"])}</p><h1>{e(config["display_name"])}</h1><p>{e(identity)}</p>{sales_link}</div><aside><small>最新财务期</small><strong>{e(latest_period)}</strong><span>以财务数据自身期间判断</span></aside></section>'
    body += metric_cards_html(records, company, latest_period) + quick_nav_html(groups)
    body += "".join(section_html(group, series) for group, series in groups.items())
    return body + notes_html(manifest)

def home_metrics(records: list[dict[str, Any]], company: str, latest_period: str) -> list[dict[str, Any]]:
    result = []
    for metric in COMPANY_PRESENTATION[company]["featured"]:
        row = choose_record(records, metric, latest_period)
        if row: result.append({"label": METRIC_LABELS.get(metric, row.get("metric_name") or metric), "value": format_value(row.get("value"), row.get("unit")), "unit": display_unit(row.get("unit")), "period": row.get("period")})
    return result

def build(input_path: Path) -> dict[str, Any]:
    records = [normalized_record(record) for record in load_records(input_path)]; validation = validate_records(records)
    manifests = load_company_manifests(); by_company: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records: by_company[str(record["company"])].append(record)
    pages: dict[str, dict[str, Any]] = {}
    for company, company_records in sorted(by_company.items()):
        if company not in COMPANY_PRESENTATION: raise ValueError(f"missing presentation config: {company}")
        manifest = manifests.get(company); slug = company_slug(company, manifest); groups = series_groups_for_company(company, company_records)
        financial_records = financial_records_for_company(company, company_records); latest = max(financial_records, key=period_sort_key); latest_period = str(latest.get("period") or "")
        ticker = next((row.get("ticker") for row in company_records if row.get("ticker")), None); config = COMPANY_PRESENTATION[company]
        pages[slug] = {"company_slug": slug, "company": company, "display_name": config["display_name"], "industry": config["industry"], "ticker": ticker, "target_period": latest_period, "financial_period_count": len({record.get("period") for record in financial_records}), "metric_count": sum(len(series) for series in groups.values()), "record_count": len(company_records), "verified_record_count": sum(record.get("status") == "verified" for record in company_records), "featured_metrics": home_metrics(company_records, company, latest_period), "html": render_company(company, ticker, company_records, groups, manifest), "page_data": {"series_groups": chart_groups(groups)}}
    payload: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "authoritative": False, "production_mutation": False, "input_contract": "GPT-owned JSON/CSV; display-only parser", "input_file": str(input_path.relative_to(PROJECT_DIR)), "input_sha256": sha256_bytes(input_path.read_bytes()), "summary": {"company_count": validation["companies"], "record_count": validation["records"], "verified_count": validation["verified"], "needs_review_count": validation["needs_review"], "program_calculated_count": validation["program_calculated"]}, "company_pages": pages}
    payload["snapshot_content_sha256"] = sha256_bytes(stable_json(payload).encode("utf-8")); return payload

def main() -> int:
    parser = argparse.ArgumentParser(); parser.add_argument("--input", type=Path, default=DEFAULT_INPUT); parser.add_argument("--verify", action="store_true"); args = parser.parse_args()
    try:
        payload = build(args.input)
        if args.verify:
            if json.loads(OUTPUT_PATH.read_text(encoding="utf-8")) != payload: raise ValueError("visualizer snapshot is stale")
        else: atomic_write(OUTPUT_PATH, (json.dumps(payload, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        print(json.dumps({"status": "PASS", **payload["summary"], "snapshot_content_sha256": payload["snapshot_content_sha256"]}, ensure_ascii=False)); return 0
    except Exception as exc:
        print(json.dumps({"status": "FAIL_CLOSED", "error": str(exc)}, ensure_ascii=False)); return 1

if __name__ == "__main__": raise SystemExit(main())
