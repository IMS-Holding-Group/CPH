document.addEventListener('DOMContentLoaded', () => {
  if (!requireAuth()) return;
  if (typeof initNotifications === 'function') initNotifications();
  const user = getCurrentUser();
  if (user && user.user_type === 'victim') {
    window.location.href = 'victim.html';
    return;
  }

  document.getElementById('logout').onclick = () => {
    localStorage.removeItem('cph_token');
    localStorage.removeItem('cph_user');
    window.location.href = 'index.html';
  };

  let currentFilter = 'all';
  document.querySelectorAll('.filter-btn').forEach(btn => {
    btn.onclick = () => {
      document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.dataset.filter;
      loadReports(currentFilter);
    };
  });

  document.getElementById('searchInput').oninput = () => loadReports(currentFilter);

  loadReports();
  const POLL_MS = 3500;
  const pollTimer = setInterval(() => loadReports(currentFilter), POLL_MS);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') loadReports(currentFilter);
  });
  window.addEventListener('pagehide', () => clearInterval(pollTimer));
});

function getRiskLevel(report) {
  if (report.priority === 'عالي' || report.report_type === 'ابتزاز') return 'high';
  if (report.financial_amount > 10000) return 'high';
  if (report.financial_amount > 1000) return 'medium';
  return 'low';
}

function getRiskLabel(level) {
  const map = {
    high: '<span class="risk-ico risk-ico-high" aria-hidden="true"><i class="fa-solid fa-triangle-exclamation"></i></span> خطر مؤكد',
    medium: '<span class="risk-ico risk-ico-medium" aria-hidden="true"><i class="fa-solid fa-circle-exclamation"></i></span> اشتباه',
    low: '<span class="risk-ico risk-ico-low" aria-hidden="true"><i class="fa-solid fa-shield-halved"></i></span> منخفض'
  };
  return map[level] || map.low;
}

function getRiskClass(level) {
  return { high: 'risk-high', medium: 'risk-medium', low: 'risk-low' }[level];
}

async function loadReports(filter = 'all') {
  const res = await apiRequest('/reports');
  const allReports = await res.json();
  let reports = allReports;
  if (filter === 'new') reports = reports.filter(r => r.status === 'قيد الانتظار');
  else if (filter === 'investigating') reports = reports.filter(r => r.status === 'تحت التحقيق');
  else if (filter === 'solved') reports = reports.filter(r => r.status === 'منتهي');

  const search = (document.getElementById('searchInput')?.value || '').trim().toLowerCase();
  if (search) {
    reports = reports.filter(r =>
      (r.description || '').toLowerCase().includes(search) ||
      (r.report_type || '').toLowerCase().includes(search) ||
      (r.victim_name || '').toLowerCase().includes(search) ||
      (r.report_id || '').toLowerCase().includes(search)
    );
  }

  document.getElementById('statTotal').textContent = allReports.length;
  document.getElementById('statNew').textContent = allReports.filter(r => r.status === 'قيد الانتظار').length;
  document.getElementById('statInvestigating').textContent = allReports.filter(r => r.status === 'تحت التحقيق').length;
  document.getElementById('statDone').textContent = allReports.filter(r => r.status === 'منتهي').length;

  const html = reports.length ? reports.map(r => {
    const risk = getRiskLevel(r);
    const riskLabel = getRiskLabel(risk);
    const riskClass = getRiskClass(risk);
    const statusBadge = r.status === 'قيد الانتظار' ? 'new' : r.status === 'تحت التحقيق' ? 'investigating' : 'done';
    return `
      <div class="report-chat-card" onclick="location.href='analysis.html?id=${r.report_id}'">
        <div class="report-chat-header">
          <span class="risk-indicator ${riskClass}">${riskLabel}</span>
          <span class="badge badge-${statusBadge}">${r.status}</span>
        </div>
        <div class="report-chat-body">
          <p class="report-preview">#${r.report_id?.slice(0,8)} – ${r.report_type} – ${r.financial_amount || 0} ريال</p>
          ${r.victim_name ? `<p class="report-victim">الضحية: ${r.victim_name}</p>` : ''}
          <p class="report-time">${r.submitted_at ? r.submitted_at.slice(0, 19) : ''}</p>
        </div>
      </div>
    `;
  }).join('') : '<div class="no-reports">لا توجد بلاغات</div>';

  document.getElementById('reportsList').innerHTML = html;
}
