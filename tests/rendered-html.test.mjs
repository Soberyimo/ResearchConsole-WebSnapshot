import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const projectRoot = new URL("../", import.meta.url);
const removedResearchTerms = /研究结论|管理层表态|研究缺口|research_output_id|finding_id|statement_id|M4 canonical/i;

async function render(path = "/") {
  const workerUrl = new URL("../dist/server/index.js", import.meta.url);
  workerUrl.searchParams.set("test", `${process.pid}-${Date.now()}-${path}`);
  const { default: worker } = await import(workerUrl.href);
  return worker.fetch(
    new Request(`http://localhost${path}`, { headers: { accept: "text/html" } }),
    { ASSETS: { fetch: async () => new Response("Not found", { status: 404 }) } },
    { waitUntil() {}, passThroughOnException() {} },
  );
}

test("financial chart keeps numeric pointer interaction", async () => {
  const app = await readFile(new URL("public/snapshot-app.js", projectRoot), "utf8");
  const polish = await readFile(new URL("public/snapshot-polish.css", projectRoot), "utf8");
  assert.match(app, /addEventListener\('pointermove', handleChartPointer\)/);
  assert.match(app, /addEventListener\('pointerdown', handleChartPointer\)/);
  assert.match(app, /formatValue\(point\.value, activeSeries\.unit\)/);
  assert.match(app, /chart-hover-tooltip/);
  assert.match(polish, /\.chart-hover-tooltip\.is-visible/);
});

test("snapshot contains only calendar and financial-data browser payloads", async () => {
  const snapshot = JSON.parse(
    await readFile(new URL("snapshot/data_platform_snapshot.json", projectRoot), "utf8"),
  );
  assert.equal(snapshot.schema_version, "ResearchOS-DataPlatformSnapshot-0.1");
  assert.equal(snapshot.derived, true);
  assert.equal(snapshot.authoritative, false);
  assert.equal(snapshot.production_mutation, false);
  assert.equal(snapshot.access_intent, "public_financial_data_platform");
  assert.ok(snapshot.frontend_input_manifest["frontend_data/earnings_calendar_supplements.json"]);
  assert.ok(snapshot.frontend_input_manifest["frontend_data/calendar_coverage_reviews.json"]);
  assert.equal(snapshot.summary.company_count, 6);
  assert.equal(snapshot.summary.calendar_event_count, 6);
  assert.deepEqual(Object.keys(snapshot.company_pages).sort(), [
    "co_000001", "co_000002", "co_000003", "co_000004", "co_000005", "co_000006",
  ]);
  assert.ok(snapshot.earnings_calendar.some((event) => event.released));
  assert.ok(snapshot.earnings_calendar.some((event) => !event.released));
  assert.ok(snapshot.earnings_calendar.some((event) =>
    event.company_id === "co_000006" && event.period === "2026H1" && event.official_appointment_date === "2026-08-17"
  ));
  for (const page of Object.values(snapshot.company_pages)) {
    assert.ok(page.page_data.financial_series.length > 0);
    const labels = page.page_data.financial_series.map((series) => series.label);
    assert.equal(new Set(labels).size, labels.length);
    const groups = Map.groupBy(page.page_data.financial_series, (series) => series.base_label);
    for (const duplicateSeries of groups.values()) {
      if (duplicateSeries.length < 2) continue;
      for (const series of duplicateSeries) {
        assert.match(series.label, /（.+ · .+）/);
      }
    }
    assert.doesNotMatch(page.html, removedResearchTerms);
    assert.equal("research_output_id" in page, false);
    assert.equal("management_statements" in page, false);
    assert.equal("findings" in page, false);
  }
});

test("calendar coverage gate tracks every company with an event or current review", async () => {
  const snapshot = JSON.parse(
    await readFile(new URL("snapshot/data_platform_snapshot.json", projectRoot), "utf8"),
  );
  const reviews = JSON.parse(
    await readFile(new URL("frontend_data/calendar_coverage_reviews.json", projectRoot), "utf8"),
  );
  const companiesWithUpcomingEvents = new Set(
    snapshot.earnings_calendar.filter((event) => !event.released).map((event) => event.company_id),
  );
  const reviewedCompanies = new Set(reviews.map((review) => review.company_id));
  for (const companyId of Object.keys(snapshot.company_pages)) {
    assert.ok(companiesWithUpcomingEvents.has(companyId) || reviewedCompanies.has(companyId));
  }
  assert.ok(reviews.every((review) => review.status === "needs_m1_review"));
});

test("home exposes only the two first-level product concepts", async () => {
  const response = await render("/");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /财报预报与公司财务数据/);
  assert.match(html, /财报预报/);
  assert.match(html, /公司 \/ 财报数据/);
  assert.match(html, /高通/);
  assert.match(html, /小鹏汽车/);
  assert.match(html, /宁德时代/);
  assert.match(html, /英伟达/);
  assert.doesNotMatch(html, /business \/ geography \/ product 独立保存/);
  assert.doesNotMatch(html, /readonly-badge|>只读数据<|primary-nav/);
  assert.doesNotMatch(html, removedResearchTerms);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/);
});

test("earnings forecast route keeps upcoming, released, time status, and source", async () => {
  const response = await render("/earnings");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /财报发布时间表/);
  assert.match(html, /即将发布/);
  assert.match(html, /已发布/);
  assert.match(html, /官方日期，时间未披露/);
  assert.match(html, /第三方预计/);
  assert.match(html, /公司IR|SEC/);
  assert.match(html, /吉利汽车控股有限公司/);
  assert.match(html, /2026-08-17（官方日期，时间未披露）/);
  assert.match(html, /吉利汽车公告/);
  assert.doesNotMatch(html, removedResearchTerms);
});

test("company pages default to financial data without a source-and-basis tab", async () => {
  for (const companyId of ["co_000001", "co_000002", "co_000004", "co_000006"]) {
    const response = await render(`/company/${companyId}`);
    assert.equal(response.status, 200);
    const html = await response.text();
    assert.match(html, /data-panel="financial"/);
    assert.match(html, /data-panel="financial"[^>]*active|class="panel active" data-panel="financial"/);
    assert.match(html, /财务与运营/);
    assert.match(html, /数据覆盖/);
    assert.match(html, /同比/);
    assert.match(html, /环比/);
    assert.match(html, /id="page-data"/);
    assert.doesNotMatch(html, /来源与口径|口径与来源|data-panel="sources"/);
    assert.doesNotMatch(html, removedResearchTerms);
  }
});

test("trend selector labels distinguish period and accounting basis", async () => {
  const response = await render("/company/co_000006");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /净利润（单季 · HKFRS归母）/);
  assert.match(html, /净利润（上半年累计 · HKFRS归母）/);
  assert.match(html, /整车交付量（全年 · 公司运营口径）/);
  assert.doesNotMatch(html, /<option[^>]*>净利润<\/option>/);
});

test("unknown companies return a clean data-platform 404", async () => {
  const response = await render("/company/co_999999");
  assert.equal(response.status, 404);
  const html = await response.text();
  assert.match(html, /暂无这家公司的财报数据/);
  assert.doesNotMatch(html, removedResearchTerms);
});
