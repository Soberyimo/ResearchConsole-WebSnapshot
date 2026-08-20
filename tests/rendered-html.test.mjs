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
  assert.equal(snapshot.summary.record_count, 751);
  assert.equal(snapshot.summary.verified_count, 389);
  assert.equal(snapshot.summary.program_calculated_count, 128);
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

test("unknown companies return a clean 404", async () => {
  const response = await render("/company/unknown");
  assert.equal(response.status, 404);
  const html = await response.text();
  assert.match(html, /暂无这家公司的财报数据/);
  assert.doesNotMatch(html, blockedTerms);
});
