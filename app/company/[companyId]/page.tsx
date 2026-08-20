import type { Metadata } from "next";
import { notFound } from "next/navigation";
import snapshot from "../../../snapshot/visualizer_snapshot.json";

type CompanyPageData = {
  company_slug: string;
  company: string;
  html: string;
  page_data: unknown;
};

type PageProps = {
  params: Promise<{ companyId: string }>;
};

function getPage(companyId: string): CompanyPageData | undefined {
  return (snapshot.company_pages as Record<string, CompanyPageData>)[companyId];
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { companyId } = await params;
  const page = getPage(companyId);
  return page
    ? { title: `${page.company}财报数据`, description: `查看${page.company}核心财务、经营指标与历史趋势。` }
    : { title: "暂无公司数据" };
}

export default async function CompanyPage({ params }: PageProps) {
  const { companyId } = await params;
  const page = getPage(companyId);
  if (!page) notFound();
  const pageData = JSON.stringify(page.page_data).replaceAll("</", "<\\/");
  return (
    <>
      <main dangerouslySetInnerHTML={{ __html: page.html }} />
      <script
        id="page-data"
        type="application/json"
        dangerouslySetInnerHTML={{ __html: pageData }}
      />
    </>
  );
}
