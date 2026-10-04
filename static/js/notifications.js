(function() {
  let pollTimer = null;
  let prevUnread = null;
  let panelOpen = false;
  let askedPerm = false;

  function esc(s) {
    if (s === undefined || s === null) return '';
    const d = document.createElement('div');
    d.textContent = String(s);
    return d.innerHTML;
  }

  async function fetchNotifs() {
    const res = await apiRequest('/notifications');
    if (!res.ok) return;
    const data = await res.json();
    const badge = document.getElementById('notifBadge');
    const list = document.getElementById('notifList');
    if (!badge) return;

    const unread = data.unread_count || 0;
    if (unread > 0) {
      badge.textContent = unread > 99 ? '99+' : String(unread);
      badge.classList.remove('hidden');
    } else {
      badge.classList.add('hidden');
    }

    if (prevUnread !== null && unread > prevUnread && typeof Notification !== 'undefined' && Notification.permission === 'granted') {
      const n = (data.notifications || []).find(function(x) { return !x.read_at; });
      if (n) {
        try {
          new Notification(n.title, { body: n.body || '', tag: n.notification_id });
        } catch (e) {}
      }
    }
    prevUnread = unread;

    if (!list || !panelOpen) return;
    const items = data.notifications || [];
    list.innerHTML = items.length
      ? items.map(function(n) {
          return (
            '<div class="notif-item' + (n.read_at ? ' read' : '') + '" data-id="' + esc(n.notification_id) + '" data-report="' + esc(n.report_id) + '">' +
            '<div class="notif-item-icon" aria-hidden="true"><i class="fa-solid fa-message"></i></div>' +
            '<div class="notif-item-text">' +
            '<strong>' + esc(n.title) + '</strong>' +
            '<p>' + esc(n.body) + '</p>' +
            '<small><i class="fa-regular fa-clock"></i> ' + esc(n.created_at || '') + '</small>' +
            '</div></div>'
          );
        }).join('')
      : '<div class="notif-empty-state"><i class="fa-regular fa-bell-slash" aria-hidden="true"></i><p>لا توجد إشعارات حالية</p>' +
        '<p class="notif-hint">ستُعرض هنا إشعارات التواصل مع المحقق وتحديثات البلاغ. إذا كان الخادم يعمل، أعد تحميل الصفحة بعد التشغيل لتحميل بيانات المحاكاة من قاعدة البيانات.</p></div>';
    list.querySelectorAll('.notif-item').forEach(function(el) {
      el.onclick = async function(ev) {
        ev.stopPropagation();
        const id = el.getAttribute('data-id');
        const rid = el.getAttribute('data-report');
        await apiRequest('/notifications/' + id + '/read', { method: 'POST', body: '{}' });
        window.location.href = 'chat.html?id=' + encodeURIComponent(rid);
      };
    });
  }

  window.initNotifications = function() {
    const bell = document.getElementById('notifBell');
    const panel = document.getElementById('notifPanel');
    const markAll = document.getElementById('notifMarkAll');
    if (!bell || !panel) return;

    bell.onclick = function(e) {
      e.stopPropagation();
      if (!askedPerm && typeof Notification !== 'undefined' && Notification.permission === 'default') {
        askedPerm = true;
        Notification.requestPermission().catch(function() {});
      }
      panel.classList.toggle('hidden');
      panelOpen = !panel.classList.contains('hidden');
      if (panelOpen) fetchNotifs();
    };

    document.addEventListener('click', function(e) {
      if (!panel.classList.contains('hidden') && !panel.contains(e.target) && e.target !== bell && !bell.contains(e.target)) {
        panel.classList.add('hidden');
        panelOpen = false;
      }
    });

    if (markAll) {
      markAll.onclick = async function(e) {
        e.stopPropagation();
        await apiRequest('/notifications/read-all', { method: 'POST', body: '{}' });
        fetchNotifs();
      };
    }

    fetchNotifs();
    if (pollTimer) clearInterval(pollTimer);
    pollTimer = setInterval(fetchNotifs, 4000);
  };

  window.refreshNotifications = function() {
    if (document.getElementById('notifBell')) fetchNotifs();
  };
})();
