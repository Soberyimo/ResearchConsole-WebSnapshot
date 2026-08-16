import type { Metadata } from "next";
import Link from "next/link";
import snapshot from "../snapshot/data_platform_snapshot.json";

export const metadata: Metadata = {
  title: "公司财报数据",
  description: "浏览公司财务指标、历史期间、同比环比和数据覆盖。",
};

type CompanyPage = {
  company_id: string;
  company: string;
  ticker?: string;
  market?: string;
  target_period?: string;
  financial_period_count: number;
  metric_count: number;
  scope_label?: string;
};

export default function Home() {
  const companies = Object.values(snapshot.company_pages) as CompanyPage[];
  const summary = snapshot.summary;

  return (
    <main>
      <section className="hero">
        <div>
          <p className="eyebrow">云见财报 ResearchOS</p>
          <h1>财报预报与公司财务数据</h1>
          <p>查看即将发布的财报，也可按公司浏览历史指标、同比环比、单位口径与数据来源。</p>
          <div className="hero-actions">
            <Link className="button-link" href="/earnings">查看财报预报</Link>
            <a className="text-link" href="#companies">浏览公司数据</a>
          </div>
        </div>
      </section>

      <section className="summary-strip" aria-label="平台概览">
        <div><small>数据公司</small><strong>{summary.company_count}</strong></div>
        <div><small>即将发布</small><strong>{summary.upcoming_event_count}</strong></div>
        <div><small>已发布事件</small><strong>{summary.released_event_count}</strong></div>
        <div><small>数据模式</small><strong>只读</strong></div>
      </section>

      <section className="section-heading" id="companies">
        <div><p className="eyebrow">公司 / 财报数据</p><h2>公司数据</h2></div>
        <p>选择公司后查看最新财报期及历史财务、运营数据。</p>
      </section>

      <section className="company-grid">
        {companies.map((company) => (
          <Link className="company-card company-card-link" href={`/company/${company.company_id}`} key={company.company_id}>
            <div className="company-card-head">
              <div>
                <p className="eyebrow">{company.market || "公司财报数据"}</p>
                <h2>{company.company}</h2>
                <p>{company.ticker || company.company_id}</p>
              </div>
              <span className="status-dot" aria-hidden="true" />
            </div>
            <div className="card-metrics">
              <div><small>最新财报期</small><strong>{company.target_period || "—"}</strong></div>
              <div><small>历史期间</small><strong>{company.financial_period_count}</strong></div>
              <div><small>数据指标</small><strong>{company.metric_count}</strong></div>
            </div>
            <p className="coverage-line">{company.scope_label || "合并口径"}</p>
            <div className="card-footer"><span className="visibility">只读数据</span><span className="arrow">查看数据 →</span></div>
          </Link>
        ))}
      </section>
    </main>
  );
}
