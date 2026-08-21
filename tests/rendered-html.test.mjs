import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const projectRoot = new URL("../", import.meta.url);
const blockedTerms = /ResearchOS|canonical|record_id|evidence_id|material_id|observation_key|business=|geography=|product=consolidated|AI抽取待复核|自动校验通过|唯一事实源|structured records|Structured financial data/i;

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
  assert.match(app, /activeSeries\.display_unit \|\| activeSeries\.unit/);
  assert.match(polish, /\.chart-hover-tooltip\.is-visible/);
});

test("visualizer snapshot is static-input only", async () => {
  const snapshot = JSON.parse(await readFile(new URL("snapshot/visualizer_snapshot.json", projectRoot), "utf8"));
  assert.equal(snapshot.schema_version, "Yunjian-VisualizerSnapshot-1");
  assert.equal(snapshot.authoritative, false);
  assert.equal(snapshot.production_mutation, false);
  assert.equal(snapshot.summary.company_count, 7);
  assert.equal(snapshot.summary.record_count, 898);
  assert.equal(snapshot.summary.verified_count, 512);
  assert.equal(snapshot.summary.calculated_count, 24);
  assert.equal(snapshot.summary.program_calculated_count, 152);
  assert.equal("earnings_calendar" in snapshot, false);
  assert.equal(Object.keys(snapshot.company_pages).length, 7);
  assert.equal(snapshot.company_pages.seres.target_period, "2026Q1");
  assert.doesNotMatch(JSON.stringify(snapshot), blockedTerms);
});

test("home leads with companies and reader-facing financial context", async () => {
  const response = await render("/");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /看懂公司的收入、盈利、经营与销量变化/);
  assert.match(html, /公司速览/);
  assert.match(html, /最新财务期/);
  assert.match(html, /整车/);
  assert.match(html, /半导体/);
  assert.match(html, /高通/);
  assert.match(html, /小鹏汽车/);
  assert.match(html, /赛力斯/);
  assert.match(html, /\/company\/seres/);
  assert.doesNotMatch(html, blockedTerms);
});

test("company pages prioritize readable sections and progressively disclose sources", async () => {
  const snapshot = JSON.parse(await readFile(new URL("snapshot/visualizer_snapshot.json", projectRoot), "utf8"));
  for (const page of Object.values(snapshot.company_pages)) {
    const response = await render(`/company/${page.company_slug}`);
    assert.equal(response.status, 200);
    const html = await response.text();
    assert.match(html, /最新财务期/);
    assert.match(html, /规模与收入/);
    assert.match(html, /关键数据/);
    assert.match(html, /查看全部数据与来源/);
    assert.match(html, /来源与口径/);
    assert.match(html, /section-nav/);
    assert.match(html, /id="page-data"/);
    assert.doesNotMatch(html, /全部记录|财务期间数|已核实|待复核/);
    assert.doesNotMatch(html, blockedTerms);
  }
});

test("Seres page separates finance, company sales, and AITO model sales", async () => {
  const response = await render("/company/seres");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /最新财务期[\s\S]*2026Q1/);
  assert.match(html, /直接看销量/);
  assert.match(html, /公司销量/);
  assert.match(html, /问界车型销量/);
  assert.match(html, /问界 M5 销量/);
  assert.match(html, /问界 M6 销量/);
  assert.match(html, /问界 M7 销量/);
  assert.match(html, /问界 M8 销量/);
  assert.match(html, /问界 M9 销量/);
  assert.match(html, /A\+H双上市公司/);
  assert.match(html, /保证类质保成本/);
  assert.match(html, /不等于问界品牌交付量/);
  assert.match(html, /28\.93/);
  assert.doesNotMatch(html, /2,893/);
  assert.doesNotMatch(html, /2026Q2 财务数据/);
});

test("six updated company pages expose the requested financial semantics", async () => {
  const snapshot = JSON.parse(await readFile(new URL("snapshot/visualizer_snapshot.json", projectRoot), "utf8"));
  const pages = Object.fromEntries(Object.values(snapshot.company_pages).map((page) => [page.company, page]));
  assert.match(pages["宁德时代"].html, /归母净利润/);
  assert.match(pages["宁德时代"].html, /498GWh 为电池系统产量/);
  assert.match(pages["吉利汽车"].html, /核心归母净利润/);
  assert.match(pages["吉利汽车"].html, /重述提示/);
  assert.match(pages["小鹏汽车"].html, /公司定义的复合 cash position/);
  assert.match(pages["小鹏汽车"].html, /归属普通股股东净利润/);
  assert.match(pages["理想汽车"].html, /单车汽车收入/);
  assert.match(pages["高通"].html, /QCT 与 QTL 并列，汽车业务属于 QCT/);
  assert.match(pages["高通"].html, /FY2026 9M/);
  assert.match(pages["英伟达"].html, /FY2027Q1 新披露框架/);
  assert.match(pages["英伟达"].html, /旧披露口径 \/ legacy/);
  assert.doesNotMatch(Object.values(pages).map((page) => page.html).join(""), /以财务数据自身期间判断/);
});

test("all reader-facing pages use 亿 money units without touching unit economics", async () => {
  const snapshot = JSON.parse(await readFile(new URL("snapshot/visualizer_snapshot.json", projectRoot), "utf8"));
  const routes = ["/", ...Object.values(snapshot.company_pages).map((page) => `/company/${page.company_slug}`)];
  const visiblePages = [];
  for (const route of routes) {
    const response = await render(route);
    assert.equal(response.status, 200);
    const html = await response.text();
    const visibleHtml = html.replace(/<script\b[\s\S]*?<\/script>/gi, "").replace(/<style\b[\s\S]*?<\/style>/gi, "");
    assert.doesNotMatch(visibleHtml, /CNY million|USD million|HKD million|EUR million|百万元|万元/);
    visiblePages.push(visibleHtml);
  }
  const combined = visiblePages.join("\n");
  assert.match(combined, /亿元/);
  assert.match(combined, /亿美元/);
  assert.match(combined, /元\/辆/);
  assert.match(combined, /万辆/);
  assert.match(combined, /GWh/);
  assert.match(combined, /%/);
});

test("unknown companies return a clean 404", async () => {
  const response = await render("/company/unknown");
  assert.equal(response.status, 404);
  const html = await response.text();
  assert.match(html, /暂无这家公司的财报数据/);
  assert.doesNotMatch(html, blockedTerms);
});
