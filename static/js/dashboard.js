/**
 * Dashboard live updates — summary cards, charts, recent alerts.
 */
(function () {
  const REFRESH_MS = 5000;
  let metricsChart;
  let networkChart;

  function pct(id, value, barId) {
    const el = document.getElementById(id);
    const bar = document.getElementById(barId);
    if (!el) return;
    const v = value != null ? Number(value) : null;
    el.textContent = v != null ? v.toFixed(1) + '%' : '—';
    if (bar) bar.style.width = (v != null ? Math.min(100, v) : 0) + '%';
  }

  function formatTime(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString();
  }

  function severityBadge(sev) {
    const map = { critical: 'danger', warning: 'warning', info: 'info' };
    return `<span class="badge bg-${map[sev] || 'secondary'}">${sev}</span>`;
  }

  async function loadSummary() {
    const res = await fetch('/api/dashboard/summary');
    const json = await res.json();
    if (!json.success) return;

    const d = json.data;
    const cur = d.current;
    if (cur) {
      pct('cpuValue', cur.cpu_usage, 'cpuBar');
      pct('memoryValue', cur.memory_usage, 'memoryBar');
      pct('diskValue', cur.disk_usage, 'diskBar');
      document.getElementById('healthValue').textContent =
        cur.health_score != null ? cur.health_score.toFixed(1) : '—';
    }
    document.getElementById('uptimeValue').textContent = d.uptime_formatted || '—';
    document.getElementById('activeAlertsCount').textContent = d.active_alerts ?? 0;
    document.getElementById('lastUpdated').textContent =
      cur ? 'Updated ' + formatTime(cur.created_at) : 'No data yet';
  }

  async function loadCharts() {
    const hours = document.getElementById('historyHours')?.value || 1;
    const res = await fetch(`/api/metrics/history?hours=${hours}&limit=500`);
    const json = await res.json();
    if (!json.success || !json.data?.length) return;

    if (!metricsChart) metricsChart = MonitorCharts.createMetricsChart('metricsChart');
    if (!networkChart) networkChart = MonitorCharts.createNetworkChart('networkChart');

    MonitorCharts.updateMetricsChart(metricsChart, json.data);
    MonitorCharts.updateNetworkChart(networkChart, json.data);
  }

  async function loadRecentAlerts() {
    const res = await fetch('/api/alerts/active');
    const json = await res.json();
    const tbody = document.getElementById('recentAlertsBody');
    if (!tbody) return;

    if (!json.success || !json.data?.length) {
      tbody.innerHTML =
        '<tr><td colspan="4" class="text-center text-muted py-3">No active alerts</td></tr>';
      return;
    }

    tbody.innerHTML = json.data.slice(0, 8).map((a) => `
      <tr>
        <td class="small text-nowrap">${formatTime(a.created_at)}</td>
        <td>${severityBadge(a.severity)}</td>
        <td><code>${a.metric_name}</code></td>
        <td class="small">${a.message}</td>
      </tr>
    `).join('');
  }

  async function refresh() {
    await Promise.all([loadSummary(), loadCharts(), loadRecentAlerts()]);
  }

  document.getElementById('historyHours')?.addEventListener('change', loadCharts);
  refresh();
  setInterval(refresh, REFRESH_MS);
})();
