document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  if (typeof initNotifications === 'function') initNotifications();
  const user = getCurrentUser();
  if (user?.user_type === 'victim') {
    window.location.href = 'victim.html';
    return;
  }

  document.getElementById('logout').onclick = () => {
    localStorage.removeItem('cph_token');
    localStorage.removeItem('cph_user');
    window.location.href = 'index.html';
  };

  const [reportsRes, invRes] = await Promise.all([
    apiRequest('/reports'),
    apiRequest('/investigators')
  ]);
  const reports = await reportsRes.json();
  const investigators = await invRes.json();

  const reportSelect = document.getElementById('reportSelect');
  reports.forEach(r => {
    const opt = document.createElement('option');
    opt.value = r.report_id;
    opt.textContent = `#${r.report_id?.slice(0,8)} - ${r.report_type}`;
    reportSelect.appendChild(opt);
  });

  const invSelect = document.getElementById('investigatorSelect');
  investigators.forEach(i => {
    const opt = document.createElement('option');
    opt.value = i.investigator_id;
    opt.textContent = `${i.full_name} - ${i.department || ''}`;
    invSelect.appendChild(opt);
  });

  reportSelect.onchange = async () => {
    const id = reportSelect.value;
    if (!id) {
      document.getElementById('adminForm').classList.add('hidden');
      return;
    }
    const res = await apiRequest('/reports/' + id);
    const report = await res.json();
    document.getElementById('statusSelect').value = report.status || 'قيد الانتظار';
    document.getElementById('caseStage').value = report.case_stage || '';
    document.getElementById('notes').value = report.notes || '';
    document.getElementById('investigatorSelect').value = report.investigator_id || '';
    document.getElementById('adminForm').classList.remove('hidden');
  };

  document.getElementById('saveBtn').onclick = async () => {
    const reportId = reportSelect.value;
    if (!reportId) return;

    const res = await apiRequest('/reports/' + reportId, {
      method: 'PUT',
      body: JSON.stringify({
        status: document.getElementById('statusSelect').value,
        case_stage: document.getElementById('caseStage').value,
        notes: document.getElementById('notes').value,
        investigator_id: document.getElementById('investigatorSelect').value || null
      })
    });
    if (res.ok) {
      alert('تم الحفظ بنجاح');
    } else {
      const d = await res.json();
      alert(d.error || 'فشل الحفظ');
    }
  };
});
