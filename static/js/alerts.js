/**
 * Alerts page — list, filter, acknowledge, resolve.
 */
(function () {
  let page = 1;
  const perPage = 25;

  function formatTime(iso) {
    if (!iso) return '—';
    return new Date(iso).toLocaleString();
  }

  function severityBadge(sev) {
    const map = { critical: 'danger', warning: 'warning', info: 'info' };
    return `<span class="badge bg-${map[sev] || 'secondary'}">${sev}</span>`;
  }

  function statusBadge(st) {
    const map = { active: 'danger', acknowledged: 'warning', resolved: 'success' };
    return `<span class="badge bg-${map[st] || 'secondary'}">${st}</span>`;
  }

  async function loadStats() {
    const hours = document.querySelector('[name=hours]')?.value || 24;
    const res = await fetch('/api/alerts/statistics?hours=' + hours);
    const json = await res.json();
    if (!json.success) return;
    const d = json.data;
    document.getElementById('statTotal').textContent = d.total ?? 0;
    document.getElementById('statCritical').textContent = d.by_severity?.critical ?? 0;
    document.getElementById('statActive').textContent = d.by_status?.active ?? 0;
  }

  async function loadAlerts() {
    const form = document.getElementById('alertFilters');
    const fd = new FormData(form);
    const params = new URLSearchParams({ page, per_page: perPage });
    ['severity', 'status', 'hours', 'metric'].forEach((k) => {
      const v = fd.get(k);
      if (v) params.set(k, v);
    });

    const res = await fetch('/api/alerts?' + params);
    const json = await res.json();
    const tbody = document.getElementById('alertsTableBody');

    if (!json.success) {
      tbody.innerHTML =
        '<tr><td colspan="8" class="text-danger text-center">Failed to load alerts</td></tr>';
      return;
    }

    if (!json.data.length) {
      tbody.innerHTML =
        '<tr><td colspan="8" class="text-center text-muted py-4">No alerts found</td></tr>';
    } else {
      tbody.innerHTML = json.data
        .map((a) => {
          let actions = '';
          if (a.status === 'active') {
            actions = `
              <button class="btn btn-sm btn-outline-warning me-1" data-action="ack" data-id="${a.id}">Ack</button>
              <button class="btn btn-sm btn-outline-success" data-action="resolve" data-id="${a.id}">Resolve</button>
            `;
          } else if (a.status === 'acknowledged') {
            actions = `<button class="btn btn-sm btn-outline-success" data-action="resolve" data-id="${a.id}">Resolve</button>`;
          } else {
            actions = '<span class="text-muted small">—</span>';
          }
          return `
            <tr>
              <td>${a.id}</td>
              <td class="small text-nowrap">${formatTime(a.created_at)}</td>
              <td>${severityBadge(a.severity)}</td>
              <td><code>${a.metric_name}</code></td>
              <td>${a.metric_value}%</td>
              <td>${statusBadge(a.status)}</td>
              <td class="small">${a.message}</td>
              <td>${actions}</td>
            </tr>
          `;
        })
        .join('');
    }

    const p = json.pagination;
    document.getElementById('paginationInfo').textContent =
      `Page ${p.page} of ${p.pages || 1} (${p.total} total)`;
    document.getElementById('prevPage').disabled = !p.has_prev;
    document.getElementById('nextPage').disabled = !p.has_next;
  }

  async function alertAction(id, action) {
    const res = await fetch(`/api/alerts/${id}/${action}`, {
      method: 'POST',
      credentials: 'same-origin',
    });
    if (res.status === 401) {
      window.location.href = '/login?next=' + encodeURIComponent(window.location.pathname);
      return;
    }
    const json = await res.json();
    if (json.success) {
      loadAlerts();
      loadStats();
    } else {
      alert(json.error || 'Action failed');
    }
  }

  document.getElementById('alertFilters').addEventListener('submit', (e) => {
    e.preventDefault();
    page = 1;
    loadAlerts();
    loadStats();
  });

  document.getElementById('prevPage').addEventListener('click', () => {
    if (page > 1) {
      page--;
      loadAlerts();
    }
  });
  document.getElementById('nextPage').addEventListener('click', () => {
    page++;
    loadAlerts();
  });

  document.getElementById('alertsTableBody').addEventListener('click', (e) => {
    const btn = e.target.closest('[data-action]');
    if (!btn) return;
    alertAction(btn.dataset.id, btn.dataset.action);
  });

  loadStats();
  loadAlerts();
})();
