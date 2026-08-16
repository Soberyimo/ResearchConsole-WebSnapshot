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

  const dataNode = document.querySelector('#page-data');
  const chart = document.querySelector('#trend-chart');
  const selector = document.querySelector('#chart-series');
  const chartShell = chart?.closest('.chart-shell');
  let pageData = null;
  let chartPoints = [];
  let activeSeries = null;
  let tooltip = null;
  if (dataNode) {
    try { pageData = JSON.parse(dataNode.textContent); } catch (_) { pageData = null; }
  }

  function ensureTooltip() {
    if (!chartShell) return null;
    if (tooltip) return tooltip;
    tooltip = document.createElement('div');
    tooltip.className = 'chart-hover-tooltip';
    tooltip.setAttribute('role', 'status');
    tooltip.hidden = true;
    chartShell.appendChild(tooltip);
    return tooltip;
  }

  function formatValue(value, unit) {
    const maximumFractionDigits = Math.abs(value) >= 1000 ? 0 : 2;
    const formatted = value.toLocaleString('zh-CN', { maximumFractionDigits });
    return unit ? `${formatted} ${unit}` : formatted;
  }

  function hideTooltip() {
    if (!tooltip) return;
    tooltip.hidden = true;
    tooltip.classList.remove('is-visible');
  }

  function showTooltip(point) {
    const node = ensureTooltip();
    if (!node || !chart || !chartShell || !activeSeries) return;
    node.textContent = `${point.record.period}\n${activeSeries.label}：${formatValue(point.value, activeSeries.unit)}`;
    node.hidden = false;
    node.classList.add('is-visible');

    const chartRect = chart.getBoundingClientRect();
    const shellRect = chartShell.getBoundingClientRect();
    const anchorX = chartRect.left - shellRect.left + point.x;
    const anchorY = chartRect.top - shellRect.top + point.y;
    const halfWidth = node.offsetWidth / 2;
    const left = Math.min(chartShell.clientWidth - node.offsetWidth - 8, Math.max(8, anchorX - halfWidth));
    const top = Math.max(8, anchorY - node.offsetHeight - 14);
    node.style.left = `${left}px`;
    node.style.top = `${top}px`;
  }

  function nearestPoint(event) {
    if (!chart || !chartPoints.length) return null;
    const rect = chart.getBoundingClientRect();
    const mouseX = event.clientX - rect.left;
    const mouseY = event.clientY - rect.top;
    if (mouseX < 0 || mouseX > rect.width || mouseY < 0 || mouseY > rect.height) return null;

    let nearest = null;
    let nearestDistance = Infinity;
    chartPoints.forEach((point) => {
      const distance = Math.hypot(mouseX - point.x, mouseY - point.y);
      if (distance < nearestDistance) {
        nearest = point;
        nearestDistance = distance;
      }
    });
    return nearestDistance <= 28 ? nearest : null;
  }

  function handleChartPointer(event) {
    const point = nearestPoint(event);
    if (point) showTooltip(point);
    else hideTooltip();
  }

  function drawChart() {
    hideTooltip();
    chartPoints = [];
    activeSeries = null;
    if (!chart || !selector || !pageData) return;
    const series = pageData.financial_series.find((item) => item.series_id === selector.value);
    if (!series) return;
    activeSeries = series;
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
      const point = { x: x(index), y: y(value), value, record: series.records[index] };
      chartPoints.push(point);
      ctx.beginPath(); ctx.arc(point.x, point.y, 4, 0, Math.PI * 2); ctx.fillStyle = '#ffffff'; ctx.fill(); ctx.strokeStyle = '#6332FF'; ctx.lineWidth = 2; ctx.stroke();
    });
    document.querySelector('#chart-unit').textContent = `单位：${series.unit}`;
    document.querySelector('#chart-legend').textContent = `${series.label} · ${series.basis || ''} · 悬停或点击数据点查看数值 · 缺失值不连线`;
  }
  if (selector) selector.addEventListener('change', drawChart);
  if (chart) {
    chart.addEventListener('pointermove', handleChartPointer);
    chart.addEventListener('pointerdown', handleChartPointer);
    chart.addEventListener('pointerleave', hideTooltip);
  }
  window.addEventListener('resize', drawChart);
  drawChart();
})();
