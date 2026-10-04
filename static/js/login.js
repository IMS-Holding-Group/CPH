document.addEventListener('DOMContentLoaded', () => {
  if (isLoggedIn()) redirectByRole();

  const loginForm = document.getElementById('loginForm');
  const registerForm = document.getElementById('registerForm');
  const showRegister = document.getElementById('showRegister');
  const showLogin = document.getElementById('showLogin');
  const regRole = document.getElementById('regRole');
  const regIqamaRow = document.getElementById('regIqamaRow');
  const regBadgeRow = document.getElementById('regBadgeRow');
  const regDeptRow = document.getElementById('regDeptRow');

  showRegister.onclick = e => {
    e.preventDefault();
    loginForm.classList.add('hidden');
    registerForm.classList.remove('hidden');
  };
  showLogin.onclick = e => {
    e.preventDefault();
    registerForm.classList.add('hidden');
    loginForm.classList.remove('hidden');
  };

  regRole.onchange = () => {
    const isInv = regRole.value === 'investigator';
    regBadgeRow.classList.toggle('hidden', !isInv);
    regDeptRow.classList.toggle('hidden', !isInv);
  };

  document.getElementById('registerFormEl').querySelector('[name="residency_status"]').onchange = function() {
    regIqamaRow.classList.toggle('hidden', this.value !== 'غير سعودي');
  };

  document.getElementById('loginFormEl').onsubmit = async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const res = await apiRequest('/login', {
      method: 'POST',
      body: JSON.stringify({
        email: fd.get('email'),
        password: fd.get('password')
      })
    });
    const data = await res.json();
    if (res.ok) {
      const wantedRole = fd.get('role');
      if (data.user_type !== wantedRole) {
        showAlert('loginAlert', 'الدور المحدد لا يتطابق مع الحساب', 'error');
        return;
      }
      localStorage.setItem('cph_token', data.user_id);
      localStorage.setItem('cph_user', JSON.stringify(data));
      redirectByRole();
    } else {
      showAlert('loginAlert', data.error || 'فشل تسجيل الدخول', 'error');
    }
  };

  document.getElementById('registerFormEl').onsubmit = async e => {
    e.preventDefault();
    const fd = new FormData(e.target);
    const residency = fd.get('residency_status');
    const body = {
      full_name: fd.get('full_name'),
      email: fd.get('email'),
      password: fd.get('password'),
      user_type: fd.get('user_type'),
      residency_status: residency,
      nationality: residency
    };
    if (residency === 'سعودي') body.national_id = fd.get('national_id');
    else body.iqama_number = fd.get('iqama_number');
    if (fd.get('user_type') === 'investigator') {
      body.badge_number = fd.get('badge_number');
      body.department = fd.get('department');
    }
    const res = await apiRequest('/register', {
      method: 'POST',
      body: JSON.stringify(body)
    });
    const data = await res.json();
    if (res.ok) {
      showAlert('registerAlert', 'تم التسجيل بنجاح. يمكنك تسجيل الدخول الآن.', 'success');
      setTimeout(() => {
        registerForm.classList.add('hidden');
        loginForm.classList.remove('hidden');
      }, 1500);
    } else {
      showAlert('registerAlert', data.error || 'فشل التسجيل', 'error');
    }
  };
});

function showAlert(id, msg, type) {
  const el = document.getElementById(id);
  el.textContent = msg;
  el.className = 'alert alert-' + (type === 'error' ? 'error' : 'success');
  el.classList.remove('hidden');
}
