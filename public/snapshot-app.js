(() => {
  const tabs = [...document.querySelectorAll('[data-tab]')];
  const panels = [...document.querySelectorAll('[data-panel]')];
  function activate(name) {
    tabs.forEach((tab) => tab.classList.toggle('active', tab.dataset.tab === name));
    panels.forEach((panel) => panel.classList.toggle('active', panel.dataset.panel === name));
    history.replaceState(null, '', `#${name}`);
    if (name === 'financial') requestAnimationFrame(drawChart);
  }
  tabs.forEach((tab) => tab.addEventListener('click', () => activate(tab.dataset.tab)));
  const initial = location.hash.slice(1);
  if (tabs.some((tab) => tab.dataset.tab === initial)) activate(initial);

  const filter = document.querySelector('#source-filter');
  if (filter) filter.addEventListener('input', () => {
    const query = filter.value.trim().toLowerCase();
    document.querySelectorAll('[data-source-row]').forEach((row) => {
      row.hidden = query && !row.textContent.toLowerCase().includes(query);
    });
  });

  const dataNode = document.querySelector('#page-data');
  const chart = document.querySelector('#trend-chart');
  const selector = document.querySelector('#chart-series');
  let pageData = null;
  if (dataNode) {
    try { pageData = JSON.parse(dataNode.textContent); } catch (_) { pageData = null; }
  }

  function drawChart() {
    if (!chart || !selector || !pageData) return;
    const series = pageData.financial_series.find((item) => item.series_id === selector.value);
    if (!series) return;
    const rect = chart.getBoundingClientRect();
    const scale = Math.min(window.devicePixelRatio || 1, 2);
    const width = Math.max(320, rect.width);
    const height = 300;
    chart.width = width * scale;
    chart.height = height * scale;
    const ctx = chart.getContext('2d');
    ctx.scale(scale, scale);
    ctx.clearRect(0, 0, width, height);
    const pad = {left: 66, right: 52, top: 22, bottom: 48};
    const values = series.records.map((row) => Number.isFinite(Number(row.value)) ? Number(row.value) : null);
    const actual = values.filter((value) => value !== null);
    if (!actual.length) return;
    let min = Math.min(...actual), max = Math.max(...actual);
    if (min === max) { min -= 1; max += 1; }
    const spread = max - min;
    min -= spread * .12; max += spread * .12;
    const x = (index) => pad.left + (width - pad.left - pad.right) * (values.length === 1 ? .5 : index / (values.length - 1));
    const y = (value) => pad.top + (height - pad.top - pad.bottom) * (1 - (value - min) / (max - min));
    ctx.font = '11px system-ui'; ctx.fillStyle = '#71717a'; ctx.strokeStyle = '#e5e5eb'; ctx.lineWidth = 1;
    for (let i = 0; i <= 4; i++) {
      const yy = pad.top + (height - pad.top - pad.bottom) * i / 4;
      const val = max - (max - min) * i / 4;
      ctx.beginPath(); ctx.moveTo(pad.left, yy); ctx.lineTo(width - pad.right, yy); ctx.stroke();
      ctx.fillText(Math.abs(val) >= 1000 ? val.toLocaleString(undefined, {maximumFractionDigits: 0}) : val.toFixed(1), 4, yy + 4);
    }
    series.records.forEach((row, index) => {
      ctx.fillStyle = '#68716c'; ctx.textAlign = 'center';
      ctx.fillText(row.period, x(index), height - 20);
    });
    ctx.strokeStyle = '#6332FF'; ctx.lineWidth = 3; ctx.lineJoin = 'round'; ctx.lineCap = 'round';
    let open = false;
    values.forEach((value, index) => {
      if (value === null) { open = false; return; }
      if (!open) { ctx.beginPath(); ctx.moveTo(x(index), y(value)); open = true; }
      else ctx.lineTo(x(index), y(value));
      const nextMissing = index === values.length - 1 || values[index + 1] === null;
      if (nextMissing) { ctx.stroke(); open = false; }
    });
    values.forEach((value, index) => {
      if (value === null) return;
      ctx.beginPath(); ctx.arc(x(index), y(value), 4, 0, Math.PI * 2); ctx.fillStyle = '#ffffff'; ctx.fill(); ctx.strokeStyle = '#6332FF'; ctx.lineWidth = 2; ctx.stroke();
    });
    document.querySelector('#chart-unit').textContent = `单位：${series.unit}`;
    document.querySelector('#chart-legend').textContent = `${series.label} · ${series.basis || ''} · 缺失值不连线`;
  }
  if (selector) selector.addEventListener('change', drawChart);
  window.addEventListener('resize', drawChart);
  drawChart();
})();
