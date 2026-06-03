/**
 * Chart.js helpers for live monitoring dashboards.
 */
window.MonitorCharts = (function () {
  const defaultOptions = {
    responsive: true,
    maintainAspectRatio: false,
    interaction: { mode: 'index', intersect: false },
    plugins: {
      legend: { position: 'bottom' },
    },
    scales: {
      x: {
        ticks: { maxTicksLimit: 8, maxRotation: 0 },
      },
      y: {
        beginAtZero: true,
        max: 100,
        title: { display: true, text: '%' },
      },
    },
  };

  function chartColors() {
    const dark = document.documentElement.getAttribute('data-bs-theme') === 'dark';
    return {
      grid: dark ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.08)',
      text: dark ? '#dee2e6' : '#495057',
    };
  }

  function applyTheme(chart) {
    const c = chartColors();
    if (chart.options.scales?.x) {
      chart.options.scales.x.grid = { color: c.grid };
      chart.options.scales.x.ticks = { ...chart.options.scales.x.ticks, color: c.text };
    }
    if (chart.options.scales?.y) {
      chart.options.scales.y.grid = { color: c.grid };
      chart.options.scales.y.ticks = { ...chart.options.scales.y.ticks, color: c.text };
    }
    chart.update('none');
  }

  function createMetricsChart(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'CPU %',
            data: [],
            borderColor: '#0d6efd',
            backgroundColor: 'rgba(13, 110, 253, 0.1)',
            tension: 0.3,
            fill: true,
          },
          {
            label: 'Memory %',
            data: [],
            borderColor: '#198754',
            backgroundColor: 'rgba(25, 135, 84, 0.1)',
            tension: 0.3,
            fill: true,
          },
          {
            label: 'Disk %',
            data: [],
            borderColor: '#ffc107',
            backgroundColor: 'rgba(255, 193, 7, 0.1)',
            tension: 0.3,
            fill: true,
          },
        ],
      },
      options: { ...defaultOptions },
    });

    window.addEventListener('theme-changed', () => applyTheme(chart));
    applyTheme(chart);
    return chart;
  }

  function createNetworkChart(canvasId) {
    const ctx = document.getElementById(canvasId);
    if (!ctx) return null;

    const chart = new Chart(ctx, {
      type: 'line',
      data: {
        labels: [],
        datasets: [
          {
            label: 'Sent (KB/s)',
            data: [],
            borderColor: '#6f42c1',
            tension: 0.3,
          },
          {
            label: 'Received (KB/s)',
            data: [],
            borderColor: '#20c997',
            tension: 0.3,
          },
        ],
      },
      options: {
        ...defaultOptions,
        scales: {
          x: defaultOptions.scales.x,
          y: {
            beginAtZero: true,
            title: { display: true, text: 'KB/s' },
          },
        },
      },
    });

    window.addEventListener('theme-changed', () => applyTheme(chart));
    applyTheme(chart);
    return chart;
  }

  function updateMetricsChart(chart, metrics) {
    if (!chart || !metrics?.length) return;
    const labels = metrics.map((m) => {
      const d = new Date(m.created_at);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
    });
    chart.data.labels = labels;
    chart.data.datasets[0].data = metrics.map((m) => m.cpu_usage);
    chart.data.datasets[1].data = metrics.map((m) => m.memory_usage);
    chart.data.datasets[2].data = metrics.map((m) => m.disk_usage);
    chart.update('none');
  }

  function updateNetworkChart(chart, metrics) {
    if (!chart || !metrics?.length) return;
    const labels = metrics.map((m) => {
      const d = new Date(m.created_at);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    });
    chart.data.labels = labels;
    chart.data.datasets[0].data = metrics.map((m) => (m.network_sent_rate || 0) / 1024);
    chart.data.datasets[1].data = metrics.map((m) => (m.network_received_rate || 0) / 1024);
    chart.update('none');
  }

  return {
    createMetricsChart,
    createNetworkChart,
    updateMetricsChart,
    updateNetworkChart,
  };
})();
