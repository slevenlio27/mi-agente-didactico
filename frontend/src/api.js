// En desarrollo, el backend corre aparte (puerto 8000). En producción, el backend sirve
// también el frontend, así que las llamadas van a la misma dirección (URL relativa).
const BASE = (import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '')).replace(/\/+$/, '')
const API_URL = `${BASE}/api`

async function request(path, options = {}) {
  const res = await fetch(`${API_URL}${path}`, {
    // credentials: 'include' es indispensable: así el navegador manda la
    // cookie HttpOnly de sesión en cada petición al backend.
    credentials: 'include',
    headers: options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' },
    ...options,
  })

  if (!res.ok) {
    let detail = 'Ocurrió un error inesperado. Intenta de nuevo.'
    try {
      const data = await res.json()
      detail = data.detail || detail
    } catch (e) {
      // el cuerpo no era JSON, se usa el mensaje genérico
    }
    throw new Error(detail)
  }

  if (res.status === 204) return null
  const contentType = res.headers.get('content-type') || ''
  return contentType.includes('application/json') ? res.json() : res
}

export const api = {
  register: (payload) => request('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),
  login: (payload) => request('/auth/login', { method: 'POST', body: JSON.stringify(payload) }),
  googleAuth: (credential) => request('/auth/google', { method: 'POST', body: JSON.stringify({ credential }) }),
  logout: () => request('/auth/logout', { method: 'POST' }),
  me: () => request('/auth/me'),

  listSessions: (q = '') => request(`/chat/sessions${q ? `?q=${encodeURIComponent(q)}` : ''}`),
  createSession: (provider, model) =>
    request('/chat/sessions', { method: 'POST', body: JSON.stringify({ provider, model }) }),
  getSession: (id) => request(`/chat/sessions/${id}`),
  deleteSession: (id) => request(`/chat/sessions/${id}`, { method: 'DELETE' }),
  sendMessage: (id, content, fileIds = []) =>
    request(`/chat/sessions/${id}/messages`, { method: 'POST', body: JSON.stringify({ content, file_ids: fileIds }) }),

  listFiles: () => request('/files'),

  getProfile: () => request('/profile'),
  updateProfile: (payload) => request('/profile', { method: 'PUT', body: JSON.stringify(payload) }),
  uploadFile: (file, sessionId) => {
    const form = new FormData()
    form.append('file', file)
    if (sessionId) form.append('session_id', sessionId)
    return request('/files/upload', { method: 'POST', body: form })
  },
  fileDownloadUrl: (id) => `${API_URL}/files/${id}/download`,
  deleteFile: (id) => request(`/files/${id}`, { method: 'DELETE' }),

  listEvents: () => request('/agenda/events'),
  createEvent: (payload) => request('/agenda/events', { method: 'POST', body: JSON.stringify(payload) }),
  deleteEvent: (id) => request(`/agenda/events/${id}`, { method: 'DELETE' }),

  getApiKeysStatus: () => request('/auth/me/api-keys'),
  updateApiKeys: (payload) => request('/auth/me/api-keys', { method: 'PUT', body: JSON.stringify(payload) }),

  logPageview: (path) => request('/analytics/pageview', { method: 'POST', body: JSON.stringify({ path }) }).catch(() => {}),

  getPublicSettings: () => request('/settings/public'),
  adminGetSettings: () => request('/admin/settings'),
  adminUpdateSettings: (payload) => request('/admin/settings', { method: 'PUT', body: JSON.stringify(payload) }),

  adminGetStats: () => request('/admin/stats'),
  adminListUsers: () => request('/admin/users'),
  adminToggleAdmin: (id) => request(`/admin/users/${id}/toggle-admin`, { method: 'PUT' }),
  adminDeleteUser: (id) => request(`/admin/users/${id}`, { method: 'DELETE' }),
}
