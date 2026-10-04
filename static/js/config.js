/**
 * ——— عدّل السطر 11 فقط ———
 * اكتب عنوان الجهاز الذي يشغّل python app.py
 *
 * على نفس الجهاز: اترك 127.0.0.1
 * من لابتوب ثانٍ على نفس الواي فاي: افتح CMD على جهاز الخادم واكتب ipconfig
 * وخذ "IPv4 Address" (مثل 192.168.1.23) وحطه مكان 127.0.0.1
 *
 * الشكل الصحيح: http://192.168.1.23:5000  (بدون شرطة في النهاية، مع :5000)
 */
const CPH_SERVER = 'http://127.0.0.1:5000';

const API_BASE = (function () {
  const apiSuffix = '/api';
  const backend = CPH_SERVER.replace(/\/$/, '') + apiSuffix;

  if (typeof window === 'undefined' || !window.location) {
    return backend;
  }
  try {
    const override = localStorage.getItem('cph_api_url');
    if (override && /^https?:\/\//i.test(override.trim())) {
      const u = override.trim().replace(/\/$/, '');
      return u.endsWith('/api') ? u : u + apiSuffix;
    }
  } catch (e) {}

  const port = window.location.port;
  if (port === '5000') {
    return window.location.origin + apiSuffix;
  }
  return backend;
})();

function apiRequest(url, options = {}) {
  const token = localStorage.getItem('cph_token');
  const headers = {
    'Content-Type': 'application/json',
    ...(token && { 'Authorization': `Bearer ${token}` }),
    ...options.headers
  };
  return fetch(API_BASE + url, { ...options, headers });
}
