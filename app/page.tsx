import type { Metadata } from "next";
import Link from "next/link";
import snapshot from "../snapshot/visualizer_snapshot.json";

export const metadata: Metadata = {
  title: "云见财报",
  description: "看懂公司的收入、盈利、经营与销量变化。",
};

type FeaturedMetric = { label: string; value: string; unit: string; period: string };
type CompanyPage = {
  company_slug: string;
  display_name: string;
  industry: string;
  ticker?: string;
  target_period?: string;
  featured_metrics: FeaturedMetric[];
};

export default function Home() {
  const companies = Object.values(snapshot.company_pages) as CompanyPage[];
  const industries = companies.reduce<Record<string, CompanyPage[]>>((groups, company) => {
    (groups[company.industry] ||= []).push(company);
    return groups;
  }, {});

  return (
    <main>
      <section className="hero reader-home-hero">
        <div>
          <p className="eyebrow">云见财报</p>
          <h1>看懂公司的收入、盈利、经营与销量变化</h1>
          <p>从核心指标开始，沿着趋势图进入历史明细；需要时再展开来源、公式与口径。</p>
          <div className="hero-actions"><a className="button-link" href="#companies">选择一家公司</a></div>
        </div>
      </section>

      <section className="section-heading home-company-heading" id="companies">
        <div><p className="eyebrow">公司速览</p><h2>从你关心的公司开始</h2></div>
        <p>卡片展示各公司现有数据中的最新财务期与少量核心指标。</p>
      </section>

      {Object.entries(industries).map(([industry, industryCompanies]) => (
        <section className="industry-group" key={industry}>
          <div className="industry-heading"><h3>{industry}</h3><span>{industryCompanies.length} 家公司</span></div>
          <div className="company-grid">
            {industryCompanies.map((company) => (
              <Link className="company-card company-card-link" href={`/company/${company.company_slug}`} key={company.company_slug}>
                <div className="company-card-head">
                  <div><p className="eyebrow">{company.industry}</p><h2>{company.display_name}</h2><p>{company.ticker || "A股口径"}</p></div>
                  <span className="latest-period"><small>最新财务期</small><strong>{company.target_period || "—"}</strong></span>
                </div>
                <div className="card-reader-metrics">
                  {company.featured_metrics.map((metric) => (
                    <div key={`${metric.label}-${metric.period}`}><small>{metric.label}</small><strong>{metric.value}</strong><span>{metric.unit} · {metric.period}</span></div>
                  ))}
                </div>
                <div className="card-footer single"><span className="arrow">进入公司页 →</span></div>
              </Link>
            ))}
          </div>
        </section>
      ))}
    </main>
  );
}
