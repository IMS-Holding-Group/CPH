function getCurrentUser() {
  const data = localStorage.getItem('cph_user');
  return data ? JSON.parse(data) : null;
}

function isLoggedIn() {
  return !!localStorage.getItem('cph_token');
}

function requireAuth() {
  if (!isLoggedIn()) {
    window.location.href = 'index.html';
    return false;
  }
  return true;
}

function redirectByRole() {
  const user = getCurrentUser();
  if (!user) return;
  if (user.user_type === 'victim') window.location.href = 'victim.html';
  else window.location.href = 'investigator.html';
}
