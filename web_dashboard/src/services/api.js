// LabelSure — API service for web dashboard
const _rawUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const BASE_URL = _rawUrl.replace(/\/+$/, '');

let _token = localStorage.getItem('labelsure_token');

export function setToken(token) {
  _token = token;
  localStorage.setItem('labelsure_token', token);
}

export function clearToken() {
  _token = null;
  localStorage.removeItem('labelsure_token');
}

export function getToken() {
  return _token;
}

async function request(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...options.headers };
  if (_token) headers['Authorization'] = `Bearer ${_token}`;

  const res = await fetch(`${BASE_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  login: (email, password) =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  getMe: () => request('/auth/me'),

  listUsers: () => request('/auth/users'),

  registerUser: (userData) =>
    request('/auth/register', {
      method: 'POST',
      body: JSON.stringify(userData),
    }),

  getHealth: () => request('/health'),

  listScans: ({ verdict, page = 1, pageSize = 20 } = {}) => {
    const params = new URLSearchParams({ page, page_size: pageSize });
    if (verdict) params.set('verdict', verdict);
    return request(`/scans?${params}`);
  },

  getScan: (id) => request(`/scans/${id}`),

  getAnalytics: () => request('/reports/analytics'),

  exportUrl: (verdict, fmt = 'csv') => {
    const params = new URLSearchParams({ fmt });
    if (verdict) params.set('verdict', verdict);
    if (_token) params.set('token', _token); // For direct download links
    return `${BASE_URL}/reports/export?${params}`;
  },
};
