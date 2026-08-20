import type { Metadata } from "next";
import Link from "next/link";
import snapshot from "../snapshot/visualizer_snapshot.json";

export const metadata: Metadata = {
  title: "云见财报 Visualizer",
  description: "浏览 GPT 结构化输入中的公司财务指标与历史趋势。",
};

type CompanyPage = {
  company_slug: string;
  company: string;
  ticker?: string;
  target_period?: string;
  financial_period_count: number;
  metric_count: number;
  record_count: number;
};

export default function Home() {
  const companies = Object.values(snapshot.company_pages) as CompanyPage[];
  const summary = snapshot.summary;

  return (
    <main>
      <section className="hero">
        <div>
          <p className="eyebrow">云见财报 Visualizer</p>
          <h1>结构化财报数据可视化</h1>
          <p>读取 GPT 提供的 JSON / CSV，展示指标、历史趋势、来源与备注；不判断或重算财经事实。</p>
          <div className="hero-actions">
            <a className="button-link" href="#companies">浏览公司数据</a>
          </div>
        </div>
      </section>

      <section className="summary-strip" aria-label="平台概览">
        <div><small>数据公司</small><strong>{summary.company_count}</strong></div>
        <div><small>结构化记录</small><strong>{summary.record_count}</strong></div>
        <div><small>待人工复核</small><strong>{summary.needs_review_count}</strong></div>
        <div><small>程序计算输入</small><strong>{summary.program_calculated_count}</strong></div>
      </section>

      <section className="section-heading" id="companies">
        <div><p className="eyebrow">Structured Data</p><h2>公司数据</h2></div>
        <p>选择公司查看输入文件中已有的财务与运营历史。</p>
      </section>

      <section className="company-grid">
        {companies.map((company) => (
          <Link className="company-card company-card-link" href={`/company/${company.company_slug}`} key={company.company_slug}>
            <div className="company-card-head">
              <div>
                <p className="eyebrow">Structured financial data</p>
                <h2>{company.company}</h2>
                <p>{company.ticker || "结构化输入"}</p>
              </div>
              <span className="status-dot" aria-hidden="true" />
            </div>
            <div className="card-metrics">
              <div><small>最新财报期</small><strong>{company.target_period || "—"}</strong></div>
              <div><small>历史期间</small><strong>{company.financial_period_count}</strong></div>
              <div><small>数据记录</small><strong>{company.record_count}</strong></div>
            </div>
            <div className="card-footer single"><span className="arrow">查看数据 →</span></div>
          </Link>
        ))}
      </section>
    </main>
  );
}
