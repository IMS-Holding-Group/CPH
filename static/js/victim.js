document.addEventListener('DOMContentLoaded', () => {
  if (!requireAuth()) return;
  if (typeof initNotifications === 'function') initNotifications();
  const user = getCurrentUser();
  if (user && user.user_type !== 'victim') {
    window.location.href = 'investigator.html';
    return;
  }

  document.getElementById('logout').onclick = () => {
    localStorage.removeItem('cph_token');
    localStorage.removeItem('cph_user');
    window.location.href = 'index.html';
  };

  document.getElementById('residencyStatus').onchange = function() {
    document.getElementById('iqamaRow').classList.toggle('hidden', this.value !== 'غير سعودي');
  };

  document.getElementById('analyzeLinkBtn').onclick = async () => {
    const val = document.getElementById('suspectLink').value.trim();
    if (!val || !val.includes('http') && !val.includes('.')) {
      alert('أدخل رابطاً صالحاً للتحليل');
      return;
    }
    const res = await apiRequest('/analyze/link', { method: 'POST', body: JSON.stringify({ url: val }) });
    const data = await res.json();
    const preview = document.getElementById('analysisPreview');
    preview.innerHTML = `<strong>تحليل الرابط:</strong><br>دولة السيرفر: ${data.server_country}<br>VPN/Proxy: ${data.vpn_proxy ? 'نعم' : 'لا'}<br>القوائم السوداء: ${data.blacklisted ? 'نعم' : 'لا'}<br>مستوى التهديد: ${data.threat_level}`;
    preview.classList.remove('hidden');
  };

  document.getElementById('analyzeAccountBtn').onclick = async () => {
    const val = document.getElementById('suspectLink').value.trim().replace('@', '');
    if (!val) {
      alert('أدخل اسم مستخدم للتحليل');
      return;
    }
    const res = await apiRequest('/analyze/account', { method: 'POST', body: JSON.stringify({ username: val }) });
    const data = await res.json();
    const preview = document.getElementById('analysisPreview');
    preview.innerHTML = `<strong>تحليل الحساب:</strong><br>تاريخ إنشاء تقديري: ${data.created_approx}<br>المتابعين: ${data.followers}<br>بوت: ${data.is_bot ? 'نعم' : 'لا'}<br>التصنيف: ${data.classification}`;
    preview.classList.remove('hidden');
  };

  document.getElementById('reportForm').onsubmit = async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const residency = fd.get('residency_status');
    if (residency === 'غير سعودي' && !fd.get('iqama_number')?.trim()) {
      showFormAlert('حقل الإقامة إجباري لغير السعوديين');
      return;
    }

    const links = [];
    const accounts = [];
    const suspectLink = fd.get('suspect_link')?.trim();
    if (suspectLink) {
      if (suspectLink.includes('http') || suspectLink.includes('.')) {
        links.push({ url: suspectLink });
      } else {
        accounts.push({ platform: 'إنستقرام', username: suspectLink.replace('@', '') });
      }
    }

    const formData = new FormData();
    formData.append('report_type', fd.get('report_type'));
    formData.append('description', fd.get('description'));
    formData.append('financial_amount', fd.get('financial_amount') || '0');
    formData.append('residency_info', residency === 'غير سعودي' ? fd.get('iqama_number') : '');
    formData.append('links', JSON.stringify(links));
    formData.append('accounts', JSON.stringify(accounts));

    const screens = document.getElementById('screenshots').files;
    for (let i = 0; i < screens.length; i++) formData.append('screenshots', screens[i]);
    const media = document.getElementById('media').files;
    for (let i = 0; i < media.length; i++) formData.append('media', media[i]);

    const token = localStorage.getItem('cph_token');
    const res = await fetch(API_BASE + '/reports', {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` },
      body: formData
    });
    const data = await res.json();
    if (res.ok) {
      showFormAlert('تم تقديم البلاغ بنجاح', 'success');
      e.target.reset();
      loadReports();
    } else {
      showFormAlert(data.error || 'فشل تقديم البلاغ', 'error');
    }
  };

  loadReports();
  const POLL_MS = 3500;
  const pollTimer = setInterval(() => loadReports(), POLL_MS);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') loadReports();
  });
  window.addEventListener('pagehide', () => clearInterval(pollTimer));
});

function showFormAlert(msg, type = 'error') {
  const el = document.getElementById('formAlert');
  el.textContent = msg;
  el.className = 'alert alert-' + (type === 'error' ? 'error' : 'success');
  el.classList.remove('hidden');
}

async function loadReports() {
  const res = await apiRequest('/reports');
  const reports = await res.json();
  const html = reports.length ? reports.map(r => {
    const badge = r.status === 'قيد الانتظار' ? 'new' : r.status === 'تحت التحقيق' ? 'investigating' : 'done';
    return `
    <div class="report-status-card" onclick="location.href='analysis.html?id=${r.report_id}'">
      <span class="badge badge-${badge}">${r.status}</span>
      <strong>#${r.report_id.slice(0,8)}</strong> – ${r.report_type}
      <small>${r.submitted_at ? r.submitted_at.slice(0,19) : ''}</small>
    </div>
  `;
  }).join('') : '<p>لا توجد بلاغات</p>';
  document.getElementById('reportsList').innerHTML = html;
}
