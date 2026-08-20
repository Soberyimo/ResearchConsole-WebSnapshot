import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const projectRoot = new URL("../", import.meta.url);
const blockedTerms = /ResearchOS production|财报预报|研究结论|管理层表态|record_id|evidence_id|material_id/i;

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
  assert.match(app, /formatValue\(point\.value, activeSeries\.unit\)/);
  assert.match(polish, /\.chart-hover-tooltip\.is-visible/);
});

test("visualizer snapshot is static-input only", async () => {
  const snapshot = JSON.parse(await readFile(new URL("snapshot/visualizer_snapshot.json", projectRoot), "utf8"));
  assert.equal(snapshot.schema_version, "Yunjian-VisualizerSnapshot-1");
  assert.equal(snapshot.authoritative, false);
  assert.equal(snapshot.production_mutation, false);
  assert.equal(snapshot.summary.company_count, 7);
  assert.equal(snapshot.summary.record_count, 751);
  assert.equal(snapshot.summary.verified_count, 389);
  assert.equal(snapshot.summary.program_calculated_count, 128);
  assert.equal("earnings_calendar" in snapshot, false);
  assert.equal(Object.keys(snapshot.company_pages).length, 7);
  assert.equal(snapshot.company_pages.seres.target_period, "2026Q1");
  assert.doesNotMatch(JSON.stringify(snapshot), blockedTerms);
});

test("home identifies the Financial Data Visualizer", async () => {
  const response = await render("/");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /云见财报 Visualizer/);
  assert.match(html, /结构化财报数据可视化/);
  assert.match(html, /JSON \/ CSV/);
  assert.match(html, /751/);
  assert.match(html, /高通/);
  assert.match(html, /小鹏汽车/);
  assert.match(html, /赛力斯/);
  assert.match(html, /\/company\/seres/);
  assert.doesNotMatch(html, blockedTerms);
});

test("company pages display source metadata and input-only comparisons", async () => {
  const snapshot = JSON.parse(await readFile(new URL("snapshot/visualizer_snapshot.json", projectRoot), "utf8"));
  for (const page of Object.values(snapshot.company_pages)) {
    const response = await render(`/company/${page.company_slug}`);
    assert.equal(response.status, 200);
    const html = await response.text();
    assert.match(html, /财务历史趋势/);
    assert.match(html, /同比/);
    assert.match(html, /来源与口径/);
    assert.match(html, /待复核|已核实/);
    assert.match(html, /id="page-data"/);
    assert.doesNotMatch(html, blockedTerms);
  }
});

test("Seres page separates finance, company sales, and AITO model sales", async () => {
  const response = await render("/company/seres");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /2026Q1 财务数据/);
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
  assert.doesNotMatch(html, /2026Q2 财务数据/);
});

test("unknown companies return a clean 404", async () => {
  const response = await render("/company/unknown");
  assert.equal(response.status, 404);
  const html = await response.text();
  assert.match(html, /暂无这家公司的财报数据/);
  assert.doesNotMatch(html, blockedTerms);
});
