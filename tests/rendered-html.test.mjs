import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const projectRoot = new URL("../", import.meta.url);

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

test("snapshot contract remains derived, canonical-only, and internal", async () => {
  const snapshot = JSON.parse(
    await readFile(new URL("snapshot/research_snapshot.json", projectRoot), "utf8"),
  );
  assert.equal(snapshot.schema_version, "ResearchConsole-WebSnapshot-0.1");
  assert.equal(snapshot.derived, true);
  assert.equal(snapshot.authoritative, false);
  assert.equal(snapshot.production_mutation, false);
  assert.equal(snapshot.access_intent, "owner_only_private_preview");
  assert.equal(snapshot.source_console_version, "0.1.3");
  assert.equal(snapshot.summary.canonical_output_count, 2);
  assert.equal(snapshot.summary.finding_count, 72);
  assert.deepEqual(Object.keys(snapshot.company_pages).sort(), ["co_000002", "co_000004"]);
  for (const page of Object.values(snapshot.company_pages)) {
    assert.equal(page.visibility, "internal_only");
    assert.match(page.research_output_id, /^ro_[0-9a-f]{24}$/);
  }
  assert.ok(Object.keys(snapshot.source_manifest).length > 0);
  assert.equal(
    Object.keys(snapshot.source_manifest).some((path) => /staged|dryrun/i.test(path)),
    false,
  );
});

test("home renders the frozen v0.1.3 product scope", async () => {
  const response = await render("/");
  assert.equal(response.status, 200);
  const html = await response.text();
  assert.match(html, /结论、数据、证据，都在这里/);
  assert.match(html, /高通/);
  assert.match(html, /小鹏汽车/);
  assert.doesNotMatch(html, /宁德时代|理想汽车|英伟达|吉利汽车/);
  assert.match(html, /私密快照 · 只读/);
  assert.match(html, /noindex/);
  assert.doesNotMatch(html, /codex-preview|react-loading-skeleton/);
});

test("canonical company pages default to financial data and keep source modules", async () => {
  for (const companyId of ["co_000004", "co_000002"]) {
    const response = await render(`/company/${companyId}`);
    assert.equal(response.status, 200);
    const html = await response.text();
    assert.match(html, /data-panel="financial"/);
    assert.match(html, /data-panel="financial"[^>]*active|class="panel active" data-panel="financial"/);
    assert.match(html, /财务与运营/);
    assert.match(html, /研究结论/);
    assert.match(html, /管理层表态/);
    assert.match(html, /研究缺口/);
    assert.match(html, /来源与证据/);
    assert.match(html, /数据覆盖/);
    assert.match(html, /internal_only/);
    assert.match(html, /id="page-data"/);
  }
});

test("unknown companies fail closed without borrowing another canonical output", async () => {
  const response = await render("/company/co_000001");
  assert.equal(response.status, 404);
  const html = await response.text();
  assert.match(html, /尚无正式研究结果/);
  assert.doesNotMatch(html, /ro_41c82f9d82e343d3c278968b|ro_351e8bf1f00e2875ac3fed65/);
});
