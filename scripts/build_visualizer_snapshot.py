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
    "accounts_receivable": "应收账款", "administrative_expense": "管理费用",
    "asp": "平均售价（ASP）", "automotive_revenue_share": "汽车业务收入占比",
    "battery_capacity": "产能", "battery_capacity_under_construction": "在建产能",
    "battery_production": "产量", "bev_sales": "纯电销量", "capex": "资本开支",
    "capacity_utilization": "产能利用率", "cash_position": "公司定义现金储备",
    "construction_in_progress": "在建工程", "contract_liabilities": "合同负债",
    "core_net_profit": "核心净利润", "debt": "债务", "export_nev_sales": "出口新能源销量",
    "export_sales": "出口销量", "export_sales_share": "出口占比", "fixed_assets": "固定资产",
    "free_cash_flow": "自由现金流", "funding_reserve": "资金储备", "ice_hev_sales": "燃油及混动销量",
    "long_term_borrowings": "长期借款", "marketable_securities": "有价证券",
    "monetary_funds": "货币资金", "nev_sales_share": "新能源占比",
    "net_income": "净利润", "net_margin_consolidated": "净利率",
    "net_profit_attributable": "归母净利润", "net_profit_consolidated": "合并净利润",
    "nev_sales": "新能源汽车销量", "nev_sales_share": "新能源占比",
    "operating_cash_flow": "经营活动现金流", "operating_income": "营业利润",
    "operating_margin": "营业利润率", "other_vehicle_sales": "其他车型销量",
    "rd_expense": "研发费用", "rnd_expense": "研发费用", "revenue": "营业收入",
    "profit_per_vehicle": "单车归属利润", "non_gaap_profit_per_vehicle": "Non-GAAP 单车归属利润",
    "rnd_expense_per_vehicle": "单车研发费用", "selling_expense_per_vehicle": "单车销售费用",
    "sga_expense_per_vehicle": "单车销售及管理费用", "segment_ebt": "分部税前利润",
    "segment_ebt_margin": "分部税前利润率", "short_term_borrowings": "短期借款",
    "revenue_share_of_group": "业务收入占比", "selling_expense": "销售费用",
    "seres_auto_sales": "赛力斯汽车销量", "sga_expense": "销售及管理费用",
    "total_vehicle_sales": "总销量", "vehicle_deliveries": "整车交付量",
    "vehicle_gross_profit_per_vehicle": "单车毛利", "vehicle_revenue_per_vehicle": "单车汽车收入",
    "vehicle_sales": "总销量", "zeekr_sales": "极氪销量", "overseas_revenue_share": "海外收入占比",
}
UNIT_LABELS = {
    "CNY million": "亿元", "USD million": "亿美元", "HKD million": "亿港元",
    "EUR million": "亿欧元", "vehicles": "辆", "辆": "辆",
}
BUSINESS_LABELS = {
    "Automotive": "汽车业务", "Data Center": "Data Center", "Edge Computing": "Edge Computing",
    "Hyperscale": "Hyperscale", "AI Clouds, Industrial & Enterprise (ACIE)": "AI Clouds、工业与企业（ACIE）",
    "QCT": "QCT", "QCT Handsets": "Handsets", "QCT Automotive": "Automotive", "QCT IoT": "IoT", "QTL": "QTL",
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
SALES_METRICS = SERES_COMPANY_SALES_METRICS | SERES_MODEL_SALES_METRICS | {
    "vehicle_deliveries", "vehicle_sales", "export_sales", "export_nev_sales", "bev_sales",
    "phev_sales", "ice_hev_sales", "zeekr_sales", "asp", "nev_sales_share", "export_sales_share",
    "profit_per_vehicle", "non_gaap_profit_per_vehicle", "vehicle_revenue_per_vehicle",
    "vehicle_gross_profit_per_vehicle", "rnd_expense_per_vehicle", "selling_expense_per_vehicle",
    "sga_expense_per_vehicle",
}
PROFITABILITY_METRICS = {
    "cost_of_sales", "gross_profit", "gross_margin", "net_income", "net_margin_consolidated",
    "net_profit_attributable", "net_profit_consolidated", "operating_income", "operating_margin",
}
OPERATIONS_METRICS = {
    "cash_and_equivalents", "cash_position", "monetary_funds", "inventory", "operating_cash_flow",
    "free_cash_flow", "capex", "rd_expense", "rnd_expense",
    "selling_expense", "administrative_expense", "finance_expense", "sga_expense",
}
COMPANY_ALIASES = {"吉利汽车控股有限公司": "吉利汽车"}
COMPANY_SLUGS = {"吉利汽车": "company-27747e102ec1"}
COMPANY_PRESENTATION = {
    "吉利汽车": {"display_name": "吉利汽车", "industry": "整车", "target_period": "2026H1", "featured": [
        {"metric": "revenue", "scope": "group"}, {"metric": "core_net_profit"}, {"metric": "asp"},
        {"metric": "gross_margin", "scope": "group"}, {"metric": "vehicle_sales"}, {"metric": "export_sales"},
    ]},
    "宁德时代": {"display_name": "宁德时代", "industry": "动力电池", "target_period": "2026H1", "featured": [
        {"metric": "revenue", "scope": "group"}, {"metric": "net_income", "scope": "group"},
        {"metric": "revenue", "business": "动力电池系统"}, {"metric": "revenue", "business": "储能电池系统"},
        {"metric": "gross_margin", "business": "动力电池系统"}, {"metric": "gross_margin", "business": "储能电池系统"},
        {"metric": "capacity_utilization"}, {"metric": "operating_cash_flow"}, {"metric": "free_cash_flow"},
    ]},
    "小鹏汽车": {"display_name": "小鹏汽车", "industry": "整车", "target_period": "2026Q1", "featured": [
        {"metric": "revenue", "scope": "group"}, {"metric": "revenue", "business": "Vehicle sales"},
        {"metric": "gross_margin", "scope": "group"}, {"metric": "gross_margin", "business": "Vehicle sales"},
        {"metric": "vehicle_deliveries"}, {"metric": "vehicle_revenue_per_vehicle"},
        {"metric": "vehicle_gross_profit_per_vehicle"}, {"metric": "net_income", "basis": "US_GAAP_attributable_to_ordinary_shareholders"},
    ]},
    "理想汽车": {"display_name": "理想汽车", "industry": "整车", "target_period": "2026Q1", "featured": [
        {"metric": "revenue", "scope": "group"}, {"metric": "revenue", "business": "Vehicle sales"},
        {"metric": "gross_margin", "scope": "group"}, {"metric": "gross_margin", "business": "Vehicle sales"},
        {"metric": "vehicle_deliveries"}, {"metric": "vehicle_revenue_per_vehicle"},
        {"metric": "vehicle_gross_profit_per_vehicle"}, {"metric": "operating_cash_flow"}, {"metric": "free_cash_flow"},
    ]},
    "英伟达": {"display_name": "英伟达", "industry": "半导体", "target_period": "FY2027Q1", "featured": [
        {"metric": "revenue", "scope": "group"}, {"metric": "revenue", "business": "Data Center", "basis": "US_GAAP_management_reporting_recast"},
        {"metric": "revenue", "business": "Edge Computing"}, {"metric": "revenue", "business": "Hyperscale"},
        {"metric": "revenue", "business": "AI Clouds, Industrial & Enterprise (ACIE)"}, {"metric": "gross_margin"},
        {"metric": "operating_cash_flow"}, {"metric": "free_cash_flow"}, {"metric": "rnd_expense"}, {"metric": "inventory"},
    ]},
    "高通": {"display_name": "高通", "industry": "半导体", "target_period": "FY2026Q3", "featured": [
        {"metric": "revenue", "scope": "group"}, {"metric": "revenue", "business": "QCT"}, {"metric": "revenue", "business": "QTL"},
        {"metric": "revenue", "business": "QCT Handsets"}, {"metric": "revenue", "business": "QCT Automotive"},
        {"metric": "revenue", "business": "QCT IoT"}, {"metric": "segment_ebt_margin", "business": "QCT"},
        {"metric": "segment_ebt_margin", "business": "QTL"}, {"metric": "rnd_expense"},
    ]},
    "赛力斯": {"display_name": "赛力斯", "industry": "整车", "target_period": "2026Q1", "featured": [
        {"metric": "revenue"}, {"metric": "gross_margin"}, {"metric": "net_profit_attributable"},
    ]},
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
    if company in COMPANY_SLUGS: return COMPANY_SLUGS[company]
    return "company-" + sha256_bytes(company.encode("utf-8"))[:12]

def infer_period_type(period: Any) -> str:
    value = str(period or "")
    if re.fullmatch(r"\d{4}-\d{2}", value): return "month"
    if re.fullmatch(r"(?:FY)?\d{4}Q[1-4]", value): return "quarter"
    if re.fullmatch(r"\d{4}H[12]", value): return "half"
    if re.fullmatch(r"(?:FY)?\d{4}M6", value): return "ytd6"
    if re.fullmatch(r"(?:FY)?\d{4}M9", value): return "ytd9"
    if re.fullmatch(r"(?:\d{4}FY|FY\d{4})", value): return "fy"
    return "unspecified"

def display_period(period: Any) -> str:
    value = str(period or "")
    match = re.fullmatch(r"(FY)?(\d{4})M([69])", value)
    if match:
        prefix = "FY" if match.group(1) else ""
        label = "H1" if match.group(3) == "6" else "9M"
        return f"{prefix}{match.group(2)} {label}"
    return value

def period_sort_key(record: dict[str, Any]) -> tuple[Any, ...]:
    end_date = str(record.get("period_end_date") or "")
    if end_date: return (end_date, 9, str(record.get("period") or ""))
    period = str(record.get("period") or "")
    match = re.fullmatch(r"(\d{4})-(\d{2})", period)
    if match: return (f"{match.group(1)}-{match.group(2)}", 1, period)
    match = re.fullmatch(r"(\d{4})Q([1-4])", period)
    if match: return (f"{match.group(1)}-{int(match.group(2)) * 3:02d}", 2, period)
    match = re.fullmatch(r"FY(\d{4})Q([1-4])", period)
    if match: return (f"{match.group(1)}-{int(match.group(2)) * 3:02d}", 2, period)
    match = re.fullmatch(r"(\d{4})H([12])", period)
    if match: return (f"{match.group(1)}-{6 if match.group(2) == '1' else 12:02d}", 3, period)
    match = re.fullmatch(r"(\d{4})FY", period) or re.fullmatch(r"FY(\d{4})", period)
    if match: return (f"{match.group(1)}-12", 4, period)
    match = re.fullmatch(r"(FY)?(\d{4})M([69])", period)
    if match: return (f"{match.group(2)}-{int(match.group(3)):02d}", 3, period)
    return (period, 0, period)

def normalized_record(record: dict[str, Any]) -> dict[str, Any]:
    result = dict(record)
    result["period_type"] = result.get("period_type") or infer_period_type(result.get("period"))
    result["metric_name"] = result.get("metric_name") or METRIC_LABELS.get(str(result.get("metric"))) or result.get("metric")
    return result

def display_unit(unit: Any) -> str:
    return UNIT_LABELS.get(str(unit), str(unit or ""))

def display_number(value: Any, unit: Any, compact_sales: bool = False) -> tuple[Any, str]:
    if not isinstance(value, (int, float)) or isinstance(value, bool): return value, display_unit(unit)
    if unit in {"CNY million", "USD million", "HKD million", "EUR million"}:
        return value / 100, display_unit(unit)
    if compact_sales and unit in {"辆", "vehicles"}:
        return value / 10000, "万辆"
    return value, display_unit(unit)

def format_value(value: Any, unit: str | None) -> str:
    if not isinstance(value, (int, float)) or isinstance(value, bool): return "—"
    if unit == "%": return f"{value:,.2f}"
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.2f}"

def comparison_view(value: Any, suffix: str = "%") -> str:
    if value is None: return '<span class="muted">—</span>'
    css_class = "positive" if value > 0 else "negative" if value < 0 else ""
    return f'<span class="{css_class}">{value:+.2f}{e(suffix)}</span>'

def canonical_company(company: Any) -> str:
    value = str(company or "")
    return COMPANY_ALIASES.get(value, value)

def semantic_metric_label(record: dict[str, Any]) -> str:
    metric = str(record.get("metric") or "")
    basis = str(record.get("basis") or "")
    if metric == "net_income":
        if basis == "Non_GAAP_attributable_to_ordinary_shareholders":
            return "Non-GAAP 归属普通股股东净利润"
        if basis.endswith("_attributable_to_ordinary_shareholders"):
            return "归属普通股股东净利润"
        if "_attributable_to_parent" in basis:
            return "归母净利润"
        return "净利润"
    if metric == "core_net_profit" and "_attributable_to_parent" in basis:
        return "核心归母净利润"
    return str(record.get("metric_name") or METRIC_LABELS.get(metric) or metric or "未命名指标")

def is_legacy_series(record: dict[str, Any]) -> bool:
    if canonical_company(record.get("company")) != "英伟达": return False
    if record.get("scope") == "legacy_submarket" or "legacy" in str(record.get("basis") or "").lower(): return True
    business = str(record.get("business") or "")
    if business in {"Gaming", "Automotive", "Professional Visualization"}: return True
    if business == "Data Center" and record.get("basis") != "US_GAAP_management_reporting_recast": return True
    return False

def base_label(record: dict[str, Any]) -> str:
    metric = semantic_metric_label(record)
    business = record.get("business"); scope = str(record.get("scope") or "group")
    if not business and scope.startswith("business="): business = scope.split("=", 1)[1]
    dimension = business or record.get("geography") or record.get("product")
    label = f'{BUSINESS_LABELS.get(str(dimension), str(dimension))} · {metric}' if dimension else metric
    return f"{label}（旧披露口径 / legacy）" if is_legacy_series(record) else label

def series_key(record: dict[str, Any]) -> tuple[str, ...]:
    return tuple(str(record.get(field) or "") for field in ("metric", "scope", "business", "geography", "product", "unit", "currency", "basis", "measurement_basis", "period_type"))

def build_series(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records: grouped[series_key(record)].append(record)
    series: list[dict[str, Any]] = []
    for identity, rows in grouped.items():
        rows.sort(key=period_sort_key); first = rows[-1]; label = base_label(first)
        sample_value, sample_unit = display_number(first.get("value"), first.get("unit"))
        series.append({
            "series_id": "series_" + sha256_bytes("|".join(identity).encode("utf-8"))[:16],
            "metric": first.get("metric"), "label": label, "unit": first.get("unit"),
            "display_unit": sample_unit, "basis": first.get("basis") or "",
            "legacy": is_legacy_series(first),
            "period_type": first.get("period_type"), "records": [{
                "period": row.get("period"), "display_period": display_period(row.get("period")), "period_type": row.get("period_type"),
                "period_start_date": row.get("period_start_date"), "period_end_date": row.get("period_end_date"),
                "value": row.get("value"), "unit": row.get("unit"), "currency": row.get("currency"),
                "qoq": row.get("qoq"), "yoy": row.get("yoy"), "yoy_pp": row.get("yoy_pp"),
                "source_type": row.get("source_type"), "source": row.get("source"),
                "source_url": row.get("source_url"), "source_location": row.get("source_location"),
                "formula": row.get("formula"), "note": row.get("note"), "basis": row.get("basis"),
                "metric_definition": row.get("metric_definition"), "status": row.get("status"),
            } for row in rows],
        })
    by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in series: by_label[item["label"]].append(item)
    for label, duplicates in by_label.items():
        if len(duplicates) < 2: continue
        for item in duplicates:
            qualifiers = [PERIOD_TYPE_LABELS.get(str(item.get("period_type")), "其他")]
            if item.get("basis") and item["basis"] not in {"reported_currency", "company_operating_metric"}:
                qualifiers.append(str(item["basis"]))
            identity = next(key for key, rows in grouped.items() if rows and "series_" + sha256_bytes("|".join(key).encode("utf-8"))[:16] == item["series_id"])
            scope, geography, product, measurement_basis = identity[1], identity[3], identity[4], identity[8]
            if scope not in {"", "group", "business"} and not scope.startswith(("business=", "geography=", "product=")):
                qualifiers.append("经营口径" if scope == "operating" else scope)
            if geography: qualifiers.append(geography)
            if product: qualifiers.append(product)
            if measurement_basis and measurement_basis not in {"reported_currency", "period_flow"}: qualifiers.append(measurement_basis)
            item["label"] = f'{label}（{" · ".join(qualifiers)}）'
    labels = [item["label"] for item in series]
    if len(labels) != len(set(labels)): raise ValueError("series labels remain ambiguous")
    return sorted(series, key=lambda item: (item.get("legacy", False), item["label"]))

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
    if record.get("yoy_pp") is not None: return record.get("yoy_pp"), " 个百分点"
    if record.get("yoy") is not None: return record.get("yoy"), "%"
    return None, "%"

def summary_table_html(item: dict[str, Any], limit: int = 6) -> str:
    visible = list(reversed(item["records"]))[:limit]
    has_comparison = any(row.get("yoy") is not None or row.get("yoy_pp") is not None for row in visible)
    rows = []
    for record in visible:
        comparison, suffix = latest_comparison(record)
        value, unit = display_number(record.get("value"), item.get("unit"))
        comparison_cell = f'<td>{comparison_view(comparison, suffix)}</td>' if has_comparison else ""
        rows.append(f'<tr><td>{e(record.get("display_period"))}</td><td><strong>{e(format_value(value, item.get("unit")))}</strong> <small>{e(unit)}</small></td>{comparison_cell}</tr>')
    comparison_head = '<th class="summary-change-head">同比 / 变化</th>' if has_comparison else '<th class="summary-change-head" hidden>同比 / 变化</th>'
    return f'<table><thead><tr><th>期间</th><th>数值</th>{comparison_head}</tr></thead><tbody class="key-data-body">{"".join(rows)}</tbody></table>'

def source_details(record: dict[str, Any]) -> str:
    source = e(record.get("source") or "来源说明未提供")
    if record.get("source_url"): source = f'<a class="source-link" href="{e(record["source_url"])}" target="_blank" rel="noreferrer">{source}</a>'
    parts = [f'<span class="source-badge">{e(SOURCE_TYPE_LABELS.get(record.get("source_type"), "来源"))}</span>', f'<p>{source}</p>']
    blocked = re.compile(r"ResearchOS|canonical|production|record_id|evidence_id|material_id|observation_key|business=|geography=|product=consolidated", re.I)
    source_location = record.get("source_location")
    formula = record.get("formula")
    note = record.get("note")
    basis = record.get("basis")
    metric_definition = record.get("metric_definition")
    parts.append(f'<small>位置：{e(source_location) if source_location and not blocked.search(str(source_location)) else "未提供"}</small>')
    parts.append(f'<small>来源类型：{e(SOURCE_TYPE_LABELS.get(record.get("source_type"), record.get("source_type") or "未提供"))}</small>')
    parts.append(f'<small>口径：{e(basis) if basis and not blocked.search(str(basis)) else "未提供"}</small>')
    parts.append(f'<small>公式：{e(formula) if formula and not blocked.search(str(formula)) else "—"}</small>')
    parts.append(f'<small>指标定义：{e(metric_definition) if metric_definition and not blocked.search(str(metric_definition)) else "未提供"}</small>')
    parts.append(f'<small>说明：{e(note) if note and not blocked.search(str(note)) else "—"}</small>')
    return "".join(parts)

def all_data_html(series: list[dict[str, Any]], period_label: str) -> str:
    metrics = []
    for item in series:
        has_qoq = any(record.get("qoq") is not None for record in item["records"])
        has_yoy = any(record.get("yoy") is not None or record.get("yoy_pp") is not None for record in item["records"])
        rows = []
        for record in reversed(item["records"]):
            comparison, suffix = latest_comparison(record)
            value, unit = display_number(record.get("value"), item.get("unit"))
            qoq_cell = f'<td>{comparison_view(record.get("qoq"))}</td>' if has_qoq else ""
            yoy_cell = f'<td>{comparison_view(comparison, suffix)}</td>' if has_yoy else ""
            rows.append(f'<tr><td><strong>{e(record.get("display_period"))}</strong></td><td>{e(format_value(value, item.get("unit")))} <small>{e(unit)}</small></td>{qoq_cell}{yoy_cell}<td><details class="row-source"><summary>查看</summary><div>{source_details(record)}</div></details></td></tr>')
        qoq_head = "<th>环比</th>" if has_qoq else ""
        yoy_head = "<th>同比 / 变化</th>" if has_yoy else ""
        metrics.append(f'<details class="metric-table"><summary><span>{e(item["label"])}</span><small>{e(PERIOD_TYPE_LABELS.get(str(item.get("period_type")), "其他"))}</small></summary><div class="table-scroll"><table><thead><tr><th>{e(period_label)}</th><th>数值</th>{qoq_head}{yoy_head}<th>来源与口径</th></tr></thead><tbody>{"".join(rows)}</tbody></table></div></details>')
    return '<details class="all-data-details"><summary>查看全部数据与来源</summary><div class="metric-tables">' + "".join(metrics) + "</div></details>"

def option_html(series: list[dict[str, Any]]) -> str:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in series: grouped[PERIOD_TYPE_LABELS.get(str(item.get("period_type")), "其他")].append(item)
    ordered = ["月度", "季度", "半年", "半年累计", "九个月累计", "年度", "时点", "其他"]
    return "".join(f'<optgroup label="{e(label)}">' + "".join(f'<option value="{e(item["series_id"])}">{e(item["label"])}</option>' for item in grouped[label]) + '</optgroup>' for label in ordered if grouped.get(label))

def section_html(group: str, series: list[dict[str, Any]]) -> str:
    title, eyebrow, description = SECTION_META[group]; first = series[0]
    period_label = "销量期间" if group in {"sales", "company_sales", "model_sales"} else "财务期间"
    return f'<section class="data-section" id="{e(group)}"><div class="section-heading compact"><div><p class="eyebrow">{e(eyebrow)}</p><h2>{e(title)}</h2></div><p>{e(description)}</p></div><div class="reader-data-layout"><div class="chart-shell trend-widget" data-series-group="{e(group)}"><div class="chart-toolbar"><label><span>选择指标与频率</span><select class="chart-series">{option_html(series)}</select></label><div class="chart-unit"></div></div><canvas class="trend-chart" height="300" aria-label="{e(title)}趋势图"></canvas><div class="chart-legend"></div></div><div class="key-data"><div class="key-data-head"><h3>关键数据</h3><span>最近 6 期</span></div><div class="table-scroll">{summary_table_html(first)}</div></div></div>{all_data_html(series, period_label)}</section>'

def choose_record(records: list[dict[str, Any]], selector: dict[str, Any], preferred_period: str | None = None) -> dict[str, Any] | None:
    candidates = [
        row for row in records
        if all(row.get(field) == expected for field, expected in selector.items())
    ]
    metric = str(selector.get("metric") or "")
    group_candidates = [row for row in candidates if row.get("scope") in {None, "", "group"}]
    if "scope" not in selector and "business" not in selector and group_candidates: candidates = group_candidates
    if preferred_period:
        same_period = [row for row in candidates if row.get("period") == preferred_period]
        if same_period: candidates = same_period
    return max(candidates, key=period_sort_key) if candidates else None

def metric_cards_html(records: list[dict[str, Any]], company: str, latest_period: str) -> str:
    cards = []
    for selector in COMPANY_PRESENTATION[company]["featured"]:
        row = choose_record(records, selector, latest_period)
        if not row: continue
        value, unit = display_number(row.get("value"), row.get("unit"), compact_sales=True)
        cards.append(f'<article class="reader-metric-card"><small>{e(base_label(row))}</small><strong>{e(format_value(value, row.get("unit")))}</strong><span>{e(unit)} · {e(display_period(row.get("period")))}</span></article>')
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

def company_semantic_html(company: str, records: list[dict[str, Any]], latest_period: str) -> str:
    if company == "高通":
        def node(business: str) -> str:
            row = choose_record(records, {"metric": "revenue", "business": business}, latest_period)
            if not row: return f'<li><span>{e(BUSINESS_LABELS.get(business, business))}</span></li>'
            value, unit = display_number(row.get("value"), row.get("unit"))
            return f'<li><span>{e(BUSINESS_LABELS.get(business, business))}</span><strong>{e(format_value(value, row.get("unit")))} {e(unit)}</strong></li>'
        return (
            '<section class="semantic-panel" id="business-framework"><div class="section-heading compact"><div><p class="eyebrow">业务层级</p>'
            '<h2>QCT 与 QTL 并列，汽车业务属于 QCT</h2></div><p>按公司披露层级展示，不把收入流平铺为集团并列分部；累计现金流期间独立显示为 FY2026 9M。</p></div>'
            '<div class="business-tree"><div class="tree-root"><strong>集团</strong></div><div class="tree-branches"><article><h3>QCT</h3><ul>'
            + node("QCT Handsets") + node("QCT Automotive") + node("QCT IoT") + '</ul></article><article><h3>QTL</h3><ul>'
            + node("QTL") + '</ul></article></div></div></section>'
        )
    if company == "英伟达":
        return '<aside class="semantic-callout"><strong>FY2027Q1 新披露框架</strong><p>主展示采用 Data Center（含 Hyperscale、ACIE）与 Edge Computing。历史 Gaming、Automotive、Professional Visualization 及 Data Center compute/networking 均标记为“旧披露口径 / legacy”，不与新框架无提示连线。</p></aside>'
    if company == "吉利汽车":
        return '<aside class="semantic-callout"><strong>重述提示</strong><p>补丁注明 2025H1 比较数据包含 Radar 同一控制业务合并重述；旧 as-reported 历史继续保留，未被静默覆盖。</p></aside>'
    if company == "宁德时代":
        return '<aside class="semantic-callout"><strong>产量不等于出货量</strong><p>2026H1 的 498GWh 为电池系统产量。当前没有正式出货量输入，因此不展示单 Wh 指标占位卡。</p></aside>'
    if company == "小鹏汽车":
        return '<aside class="semantic-callout"><strong>现金口径提示</strong><p>420.9亿元为公司定义的复合 cash position，不等同于资产负债表“现金及现金等价物”。</p></aside>'
    return ""

def chart_groups(groups: dict[str, list[dict[str, Any]]]) -> dict[str, list[dict[str, Any]]]:
    return {
        group: [{
            "series_id": item["series_id"], "label": item["label"], "unit": item["unit"],
            "display_unit": item["display_unit"], "legacy": item.get("legacy", False),
            "records": [{
                "period": row["period"], "display_period": row.get("display_period"),
                "value": display_number(row["value"], item["unit"])[0], "qoq": row.get("qoq"),
                "yoy": row.get("yoy"), "yoy_pp": row.get("yoy_pp"),
            } for row in item["records"]],
        } for item in series]
        for group, series in groups.items()
    }

def financial_records_for_company(company: str, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if company == "赛力斯": return [row for row in records if row.get("metric") in SERES_FINANCIAL_METRICS]
    return [row for row in records if row.get("metric") not in SALES_METRICS]

def render_company(company: str, ticker: str | None, records: list[dict[str, Any]], groups: dict[str, list[dict[str, Any]]], manifest: dict[str, Any] | None) -> str:
    config = COMPANY_PRESENTATION[company]; financial_records = financial_records_for_company(company, records)
    latest_period = str(config.get("target_period") or max(financial_records, key=period_sort_key).get("period") or "")
    identity = " · ".join(value for value in (ticker, str(config["industry"])) if value)
    sales_link = '<a class="hero-shortcut" href="#company_sales">直接看销量 →</a>' if company == "赛力斯" else ""
    body = f'<a class="back-link" href="/">← 返回公司列表</a><section class="company-hero reader-company-hero"><div><p class="eyebrow">{e(config["industry"])}</p><h1>{e(config["display_name"])}</h1><p>{e(identity)}</p>{sales_link}</div><aside><small>最新财务期</small><strong>{e(display_period(latest_period))}</strong><span>公司披露期间</span></aside></section>'
    body += '<div class="overview-heading"><p class="eyebrow">先看重点</p><h2>关键经营与财务指标</h2></div>'
    body += metric_cards_html(records, company, latest_period) + quick_nav_html(groups) + company_semantic_html(company, records, latest_period)
    body += "".join(section_html(group, series) for group, series in groups.items())
    return body + notes_html(manifest)

def home_metrics(records: list[dict[str, Any]], company: str, latest_period: str) -> list[dict[str, Any]]:
    result = []
    for selector in COMPANY_PRESENTATION[company]["featured"][:3]:
        row = choose_record(records, selector, latest_period)
        if row:
            value, unit = display_number(row.get("value"), row.get("unit"), compact_sales=True)
            result.append({"label": base_label(row), "value": format_value(value, row.get("unit")), "unit": unit, "period": display_period(row.get("period"))})
    return result

def build(input_path: Path) -> dict[str, Any]:
    records = [normalized_record(record) for record in load_records(input_path)]; validation = validate_records(records)
    manifests = load_company_manifests(); by_company: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records: by_company[canonical_company(record["company"])].append(record)
    pages: dict[str, dict[str, Any]] = {}
    for company, company_records in sorted(by_company.items()):
        if company not in COMPANY_PRESENTATION: raise ValueError(f"missing presentation config: {company}")
        manifest = manifests.get(company) or next((manifests.get(alias) for alias, canonical in COMPANY_ALIASES.items() if canonical == company and manifests.get(alias)), None)
        slug = company_slug(company, manifest); groups = series_groups_for_company(company, company_records)
        financial_records = financial_records_for_company(company, company_records)
        config = COMPANY_PRESENTATION[company]
        latest_period = str(config.get("target_period") or max(financial_records, key=period_sort_key).get("period") or "")
        ticker = next((row.get("ticker") for row in company_records if row.get("ticker")), None)
        pages[slug] = {"company_slug": slug, "company": company, "display_name": config["display_name"], "industry": config["industry"], "ticker": ticker, "target_period": display_period(latest_period), "financial_period_count": len({record.get("period") for record in financial_records}), "metric_count": sum(len(series) for series in groups.values()), "record_count": len(company_records), "verified_record_count": sum(record.get("status") == "verified" for record in company_records), "calculated_record_count": sum(record.get("status") == "calculated" for record in company_records), "featured_metrics": home_metrics(company_records, company, latest_period), "html": render_company(company, ticker, company_records, groups, manifest), "page_data": {"series_groups": chart_groups(groups)}}
    payload: dict[str, Any] = {"schema_version": SCHEMA_VERSION, "authoritative": False, "production_mutation": False, "input_contract": "GPT-owned JSON/CSV; display-only parser", "input_file": str(input_path.relative_to(PROJECT_DIR)), "input_sha256": sha256_bytes(input_path.read_bytes()), "summary": {"company_count": len(pages), "raw_company_identity_count": validation["companies"], "record_count": validation["records"], "verified_count": validation["verified"], "calculated_count": validation["calculated"], "needs_review_count": validation["needs_review"], "program_calculated_count": validation["program_calculated"]}, "company_pages": pages}
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
