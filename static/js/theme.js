(function() {
  const STORAGE_KEY = 'cph_theme';
  const THEMES = { light: 'light', dark: 'dark' };

  function getStoredTheme() {
    return localStorage.getItem(STORAGE_KEY) || 'light';
  }

  function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem(STORAGE_KEY, theme);
    updateToggleIcon(theme);
  }

  function updateToggleIcon(theme) {
    const icon = document.getElementById('themeIcon');
    const label = document.getElementById('themeLabel');
    if (icon) {
      icon.innerHTML = theme === 'dark'
        ? '<i class="fa-solid fa-sun" aria-hidden="true"></i>'
        : '<i class="fa-solid fa-moon" aria-hidden="true"></i>';
    }
    if (label) label.textContent = theme === 'dark' ? 'الوضع الفاتح' : 'الوضع الداكن';
  }

  function initTheme() {
    const theme = getStoredTheme();
    setTheme(theme);

    document.getElementById('themeToggle')?.addEventListener('click', function() {
      const next = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
      setTheme(next);
    });
  }

  function initMobileSidebar() {
    const menuBtn = document.getElementById('sidebarToggle');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    if (!sidebar) return;

    function openSidebar() {
      sidebar.classList.add('open');
      document.body.style.overflow = 'hidden';
      overlay?.classList.remove('hidden');
    }
    function closeSidebar() {
      sidebar.classList.remove('open');
      document.body.style.overflow = '';
      overlay?.classList.add('hidden');
    }

    menuBtn?.addEventListener('click', function() {
      sidebar.classList.contains('open') ? closeSidebar() : openSidebar();
    });
    overlay?.addEventListener('click', closeSidebar);

    window.addEventListener('resize', function() {
      if (window.innerWidth > 768) closeSidebar();
    });
  }

  document.addEventListener('DOMContentLoaded', function() {
    initTheme();
    initMobileSidebar();
  });
})();
