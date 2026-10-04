document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  if (typeof initNotifications === 'function') initNotifications();

  const params = new URLSearchParams(location.search);
  const reportId = params.get('id');
  if (!reportId) {
    location.href = getCurrentUser()?.user_type === 'victim' ? 'victim.html' : 'investigator.html';
    return;
  }

  let report = null;

  document.getElementById('backLink').href = getCurrentUser()?.user_type === 'victim' ? 'victim.html' : 'investigator.html';
  document.getElementById('chatLink').href = 'chat.html?id=' + reportId;

  document.getElementById('logout').onclick = () => {
    localStorage.removeItem('cph_token');
    localStorage.removeItem('cph_user');
    window.location.href = 'index.html';
  };

  const res = await apiRequest('/reports/' + reportId);
  if (!res.ok) {
    alert('البلاغ غير موجود');
    location.href = getCurrentUser()?.user_type === 'victim' ? 'victim.html' : 'investigator.html';
    return;
  }
  report = await res.json();

  const viewer = getCurrentUser();
  const statusLabel = viewer?.user_type === 'victim' ? 'حالة بلاغك (كما في النظام)' : 'حالة البلاغ في النظام';

  const baseUrl = API_BASE.replace('/api', '');

  async function loadAIModel() {
    const r = await apiRequest('/ai-recommendations/' + reportId);
    const el = document.getElementById('aiModelOutput');
    if (!r.ok) {
      el.innerHTML = '<p class="ai-error">تعذر تحميل التوصيات</p>';
      return;
    }
    const data = await r.json();
    el.innerHTML = `
      ${data.model_used ? '<div class="ai-model-badge-inline">نموذج مدرب فعلي</div>' : '<div class="ai-model-fallback">استخدم python train_model.py لتدريب النموذج</div>'}
      <div class="ai-summary">${data.summary}</div>
      <div class="ai-threat">مستوى التهديد: <strong class="risk-${data.threat_level === 'عالي' ? 'high' : data.threat_level === 'متوسط' ? 'medium' : 'low'}">${data.threat_level}</strong></div>
      <div class="ai-rec-list">
        <strong>توصيات النموذج المدرب:</strong>
        <ul>${(data.recommendations || []).map(rec => `<li>${rec}</li>`).join('')}</ul>
      </div>
      <div class="ai-confidence">ثقة النموذج: ${((data.confidence || 0) * 100).toFixed(0)}%</div>
    `;
  }
  loadAIModel();

  document.getElementById('reportInfo').innerHTML = `
    <h2>البلاغ #${report.report_id?.slice(0,8)}</h2>
    <div class="report-meta">
      <p><strong>النوع:</strong> ${report.report_type}</p>
      <p><strong>الوصف:</strong> ${report.description || '-'}</p>
      <p><strong>المبلغ المأخوذ/المطالب به:</strong> ${report.financial_amount || 0} ريال</p>
      <p id="reportStatusLine"><strong>${statusLabel}:</strong> <span class="status-emphasis">${report.status}</span></p>
    </div>
    ${report.screenshots?.length ? `<p><strong>صور المحادثات:</strong></p><div class="screenshot-thumbs">${report.screenshots.map(s => `<img src="${baseUrl}/uploads/${s.file_path}" alt="لقطة" class="thumb">`).join('')}</div>` : ''}
    ${report.links?.length ? `<p><strong>الروابط:</strong></p><ul>${report.links.map(l => `<li>${l.link_url}</li>`).join('')}</ul>` : ''}
    ${report.accounts?.length ? `<p><strong>الحسابات:</strong></p><ul>${report.accounts.map(a => `<li>${a.platform_name}: ${a.username}</li>`).join('')}</ul>` : ''}
  `;

  const inv = getCurrentUser();
  if (inv && inv.user_type === 'investigator') {
    const card = document.getElementById('investigatorStatusCard');
    const sel = document.getElementById('reportStatusSelect');
    const btn = document.getElementById('saveReportStatusBtn');
    const feedback = document.getElementById('statusSaveFeedback');
    if (card && sel && btn) {
      card.classList.remove('hidden');
      sel.value = report.status || 'قيد الانتظار';
      btn.onclick = async () => {
        const newStatus = sel.value;
        feedback.classList.add('hidden');
        const r = await apiRequest('/reports/' + reportId, {
          method: 'PUT',
          body: JSON.stringify({ status: newStatus })
        });
        const data = await r.json().catch(() => ({}));
        if (!r.ok) {
          feedback.textContent = data.error || 'تعذر حفظ الحالة';
          feedback.classList.remove('hidden');
          return;
        }
        report.status = newStatus;
        const line = document.getElementById('reportStatusLine');
        if (line) {
          line.innerHTML = `<strong>${statusLabel}:</strong> <span class="status-emphasis">${newStatus}</span>`;
        }
        feedback.textContent = 'تم حفظ الحالة. سيظهر التحديث عند الضحية بعد تحديث الصفحة، وسيصل إشعار إذا كان هناك تغييراً فعلياً في الحالة.';
        feedback.classList.remove('hidden');
        if (typeof window.refreshNotifications === 'function') window.refreshNotifications();
      };
    }
  }

  if (report.links?.length) document.getElementById('linkInput').placeholder = report.links[0].link_url;
  if (report.accounts?.length) document.getElementById('accountUsername').value = report.accounts[0].username;

  document.querySelectorAll('.analysis-tab').forEach(tab => {
    tab.onclick = () => {
      document.querySelectorAll('.analysis-tab').forEach(t => t.classList.remove('active'));
      document.querySelectorAll('.analysis-tab-content').forEach(c => c.classList.remove('active'));
      tab.classList.add('active');
      const id = 'tab' + tab.dataset.tab.charAt(0).toUpperCase() + tab.dataset.tab.slice(1);
      document.getElementById(id).classList.add('active');
    };
  });

  document.getElementById('runLinkAnalysis').onclick = async () => {
    const url = document.getElementById('linkInput').value.trim() || report?.links?.[0]?.link_url;
    if (!url) { alert('أدخل الرابط'); return; }
    const r = await apiRequest('/analyze/link', { method: 'POST', body: JSON.stringify({ url, report_id: reportId }) });
    const data = await r.json();
    const el = document.getElementById('linkResult');
    el.innerHTML = `<div class="analysis-result-box">
      <p><strong>دولة السيرفر:</strong> ${data.server_country}</p>
      <p><strong>مخفي خلف VPN/Proxy:</strong> ${data.vpn_proxy ? 'نعم ⚠️' : 'لا'}</p>
      <p><strong>القوائم السوداء:</strong> ${data.blacklisted ? 'مسجل ⚠️' : 'لا'}</p>
      <p><strong>مستوى التهديد:</strong> <span class="risk-${data.threat_level === 'عالي' ? 'high' : data.threat_level === 'متوسط' ? 'medium' : 'low'}">${data.threat_level}</span></p>
    </div>`;
    el.classList.remove('hidden');
  };

  document.getElementById('runAccountAnalysis').onclick = async () => {
    const username = document.getElementById('accountUsername').value.trim().replace('@', '') || report?.accounts?.[0]?.username;
    const platform = document.getElementById('accountPlatform').value;
    if (!username) { alert('أدخل اسم المستخدم'); return; }
    const r = await apiRequest('/analyze/account', { method: 'POST', body: JSON.stringify({ username, platform, report_id: reportId }) });
    const data = await r.json();
    const el = document.getElementById('accountResult');
    el.innerHTML = `<div class="analysis-result-box">
      <p><strong>تاريخ إنشاء تقديري:</strong> ${data.created_approx || '-'}</p>
      <p><strong>تغييرات اليوزر:</strong> ${data.username_changes || '-'}</p>
      <p><strong>المتابعين:</strong> ${data.followers || 0}</p>
      <p><strong>بوتات:</strong> ${data.is_bot ? 'نعم ⚠️' : 'لا'}</p>
      <p><strong>التصنيف:</strong> ${data.classification || '-'} (حساب وهمي = جديد للابتزاز، مسروق = قديم)</p>
    </div>`;
    el.classList.remove('hidden');
  };

  document.getElementById('runImageAnalysis').onclick = async () => {
    const input = document.getElementById('imageInput');
    let imgData = '';
    if (input.files?.length) {
      const file = input.files[0];
      const reader = new FileReader();
      reader.onload = async () => {
        const r = await apiRequest('/analyze/image', { method: 'POST', body: JSON.stringify({ image: reader.result, report_id: reportId }) });
        const data = await r.json();
        const el = document.getElementById('imageResult');
        el.innerHTML = `<div class="analysis-result-box">
          <p><strong>احتمال التزييف (Deepfake):</strong> ${data.deepfake_probability || 0}% ${(data.deepfake_probability || 0) > 70 ? '⚠️ فيديو/صورة مفبركة محتملة' : ''}</p>
          <p><strong>بيانات EXIF:</strong> ${data.exif_found ? data.exif_summary : 'غير متوفرة'}</p>
          <p>${data.explanation || ''}</p>
        </div>`;
        el.classList.remove('hidden');
      };
      reader.readAsDataURL(file);
    } else if (report?.media?.length) {
      const el = document.getElementById('imageResult');
      const m = report.media[0];
      const score = ((m?.deepfake_score || 0.15) * 100).toFixed(1);
      el.innerHTML = `<div class="analysis-result-box">
        ${m ? `<img src="${baseUrl}/uploads/${m.file_path}" alt="وسائط" class="thumb">` : ''}
        <p><strong>احتمال التزييف (Deepfake):</strong> ${score}% ${parseFloat(score) > 70 ? '⚠️ صورة/فيديو مفبرك محتمل' : ''}</p>
        <p><strong>بيانات EXIF:</strong> ${m?.exif_data ? 'موجود - تم استخراجها' : 'غير متوفرة'}</p>
      </div>`;
      el.classList.remove('hidden');
    } else alert('ارفع صورة أولاً');
  };

  document.getElementById('runStylometryAnalysis').onclick = async () => {
    const text = document.getElementById('stylometryInput').value.trim() || (report?.screenshots?.length ? 'نص محادثة من الصور...' : '');
    if (!text) { alert('أدخل النص أو ارفع صور المحادثة'); return; }
    const r = await apiRequest('/analyze/stylometry', { method: 'POST', body: JSON.stringify({ text, report_id: reportId }) });
    const data = await r.json();
    const el = document.getElementById('stylometryResult');
    el.innerHTML = `<div class="analysis-result-box">
      <p><strong>اللهجة:</strong> ${data.dialect || '-'}</p>
      <p><strong>الكلمات المتكررة:</strong> ${(data.repeated_words || []).join(', ') || '-'}</p>
      <p><strong>الأخطاء الإملائية:</strong> ${(data.spelling_errors || []).join(', ') || '-'}</p>
      <p><strong>الكلمات المفتاحية:</strong> ${(data.key_phrases || []).join(', ') || '-'}</p>
      <p class="style-note">لو أسلوب مشابه في بلاغ آخر → المبتز غالباً نفس الشخص</p>
    </div>`;
    el.classList.remove('hidden');
  };

  document.getElementById('runReverseAnalysis').onclick = async () => {
    const input = document.getElementById('reverseImageInput');
    let imgData = '';
    if (input.files?.length) {
      const file = input.files[0];
      const reader = new FileReader();
      reader.onload = async () => {
        const r = await apiRequest('/reverse-image', { method: 'POST', body: JSON.stringify({ image: reader.result }) });
        const data = await r.json();
        const el = document.getElementById('reverseResult');
        el.innerHTML = `<div class="analysis-result-box">
          <p><strong>المنصات المحتملة:</strong> ${(data.potential_matches || []).join(', ')}</p>
          <p><strong>نسبة التطابق:</strong> ${data.match_score || 0}%</p>
          <p>${data.explanation || ''}</p>
        </div>`;
        el.classList.remove('hidden');
      };
      reader.readAsDataURL(file);
    } else alert('ارفع صورة البروفايل أولاً');
  };

  function renderSavedAnalyses() {
    const html = [];
    if (report.ai_analyses?.length) {
      report.ai_analyses.forEach(a => {
        let r = {};
        try { r = typeof a.result === 'string' ? JSON.parse(a.result || '{}') : (a.result || {}); } catch (e) {}
        html.push(`<div class="analysis-item"><strong>${a.analysis_type}</strong>: <pre>${JSON.stringify(r, null, 2)}</pre></div>`);
      });
    }
    if (report.stylometry?.length) {
      report.stylometry.forEach(s => {
        html.push(`<div class="analysis-item"><strong>أسلوب الكتابة:</strong> لهجة ${s.suspected_dialect || '-'}</div>`);
      });
    }
    if (report.linked_cases?.length) {
      html.push(`<div class="analysis-item"><strong>قضايا مرتبطة:</strong> ${report.linked_cases.map(l => `#${(l.report_id_1 === reportId ? l.report_id_2 : l.report_id_1).slice(0,8)}`).join(', ')}</div>`);
    }
    document.getElementById('savedAnalyses').innerHTML = html.length ? html.join('') : '<p>لا توجد تحليلات محفوظة بعد</p>';
  }
  renderSavedAnalyses();

  const POLL_MS = 4000;
  setInterval(async () => {
    const r = await apiRequest('/reports/' + reportId);
    if (!r.ok) return;
    const fresh = await r.json();
    if (fresh.status === report.status) return;
    report.status = fresh.status;
    const line = document.getElementById('reportStatusLine');
    if (line) {
      line.innerHTML = `<strong>${statusLabel}:</strong> <span class="status-emphasis">${fresh.status}</span>`;
    }
    const sel = document.getElementById('reportStatusSelect');
    if (sel && viewer?.user_type === 'investigator') sel.value = fresh.status;
  }, POLL_MS);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState !== 'visible') return;
    apiRequest('/reports/' + reportId).then(r => r.ok ? r.json() : null).then(fresh => {
      if (!fresh || fresh.status === report.status) return;
      report.status = fresh.status;
      const line = document.getElementById('reportStatusLine');
      if (line) {
        line.innerHTML = `<strong>${statusLabel}:</strong> <span class="status-emphasis">${fresh.status}</span>`;
      }
      const sel = document.getElementById('reportStatusSelect');
      if (sel && viewer?.user_type === 'investigator') sel.value = fresh.status;
    });
  });

  document.getElementById('generatePdf').onclick = () => {
    const content = document.querySelector('.main-content');
    const w = window.open('', '_blank');
    w.document.write(`
      <!DOCTYPE html>
      <html dir="rtl" lang="ar">
      <head>
        <meta charset="UTF-8">
        <title>التقرير الجنائي - البلاغ ${reportId?.slice(0,8)}</title>
        <style>
          body{font-family:'Segoe UI',Tahoma,sans-serif;padding:32px;direction:rtl;line-height:1.6;}
          h1,h2,h3{color:#0A2540;}
          .report-meta{border:1px solid #ddd;padding:16px;margin:16px 0;border-radius:8px;}
          .analysis-result-box{background:#f5f7fa;padding:16px;margin:12px 0;border-radius:8px;}
          pre{white-space:pre-wrap;}
          @media print{body{padding:16px;}}
        </style>
      </head>
      <body>
        <h1>التقرير الجنائي الآلي</h1>
        <p>المُخبر الرقمي الذكي – Cyber-Police Hub</p>
        <p>تاريخ التقرير: ${new Date().toLocaleDateString('ar-SA')}</p>
        <hr>
        ${content.innerHTML}
      </body>
      </html>
    `);
    w.document.close();
    w.print();
  };
});
