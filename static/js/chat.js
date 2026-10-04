document.addEventListener('DOMContentLoaded', async () => {
  if (!requireAuth()) return;
  if (typeof initNotifications === 'function') initNotifications();

  const params = new URLSearchParams(location.search);
  const presetReportId = params.get('id');

  document.getElementById('backLink').href = getCurrentUser()?.user_type === 'victim' ? 'victim.html' : 'investigator.html';

  document.getElementById('logout').onclick = () => {
    localStorage.removeItem('cph_token');
    localStorage.removeItem('cph_user');
    window.location.href = 'index.html';
  };

  let chatPollTimer = null;
  const CHAT_POLL_MS = 2500;
  const REPORTS_POLL_MS = 5000;

  function startChatPoll(reportId) {
    if (chatPollTimer) clearInterval(chatPollTimer);
    if (!reportId) return;
    chatPollTimer = setInterval(() => loadChat(reportId, { scrollIfNearBottom: true }), CHAT_POLL_MS);
  }

  async function refreshReportOptions(selectedId) {
    const res = await apiRequest('/reports');
    if (!res.ok) return;
    const reports = await res.json();
    const select = document.getElementById('reportSelect');
    const prev = selectedId || select.value;
    select.innerHTML = '<option value="">— اختر بلاغاً —</option>';
    reports.forEach(r => {
      const opt = document.createElement('option');
      opt.value = r.report_id;
      opt.textContent = `#${r.report_id?.slice(0,8)} - ${r.report_type}`;
      select.appendChild(opt);
    });
    if (prev && reports.some(r => r.report_id === prev)) select.value = prev;
  }

  await refreshReportOptions(presetReportId || undefined);
  const select = document.getElementById('reportSelect');

  if (presetReportId) {
    select.value = presetReportId;
    loadChat(presetReportId, { scrollToBottom: true });
    document.getElementById('chatCard').classList.remove('hidden');
    startChatPoll(presetReportId);
  }

  setInterval(() => refreshReportOptions(select.value), REPORTS_POLL_MS);
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && select.value) {
      loadChat(select.value, { scrollIfNearBottom: true });
      refreshReportOptions(select.value);
    }
  });

  select.onchange = () => {
    const id = select.value;
    if (chatPollTimer) clearInterval(chatPollTimer);
    if (id) {
      loadChat(id, { scrollToBottom: true });
      document.getElementById('chatCard').classList.remove('hidden');
      startChatPoll(id);
    } else {
      document.getElementById('chatCard').classList.add('hidden');
    }
  };

  document.getElementById('sendBtn').onclick = sendMessage;
  document.getElementById('messageInput').onkeypress = e => { if (e.key === 'Enter') sendMessage(); };

  function sendMessage() {
    const reportId = select.value;
    if (!reportId) return;
    const text = document.getElementById('messageInput').value.trim();
    if (!text) return;

    apiRequest('/chat/' + reportId, {
      method: 'POST',
      body: JSON.stringify({ message: text })
    }).then(async res => {
      if (res.ok) {
        document.getElementById('messageInput').value = '';
        loadChat(reportId, { scrollToBottom: true });
        if (typeof refreshNotifications === 'function') refreshNotifications();
      }
    });
  }

  async function loadChat(reportId, opts = {}) {
    const container = document.getElementById('messagesContainer');
    const nearBottom = container && (container.scrollHeight - container.scrollTop - container.clientHeight < 100);

    const res = await apiRequest('/chat/' + reportId);
    const messages = await res.json();
    const userId = localStorage.getItem('cph_token');
    const html = messages.map(m => `
      <div class="msg ${m.sender_id === userId ? 'sent' : 'received'}">
        <strong>${m.full_name || 'مستخدم'}</strong>: ${m.message_text}
        <small>${m.sent_at ? m.sent_at.slice(0,19) : ''}</small>
      </div>
    `).join('');
    container.innerHTML = html || '<p>لا توجد رسائل</p>';

    const shouldScroll = opts.scrollToBottom || (opts.scrollIfNearBottom && nearBottom);
    if (shouldScroll) {
      container.scrollTop = container.scrollHeight;
    }
  }

  window.addEventListener('pagehide', () => {
    if (chatPollTimer) clearInterval(chatPollTimer);
  });
});
