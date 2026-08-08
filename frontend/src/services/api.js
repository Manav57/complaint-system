const BASE = '/api'

async function request(path, options = {}) {
  // FormData (multipart upload) must NOT set Content-Type — the browser adds the boundary.
  const headers = options.body instanceof FormData ? {} : { 'Content-Type': 'application/json' }
  const res = await fetch(`${BASE}${path}`, {
    headers,
    ...options,
  })
  if (!res.ok) {
    let detail = res.statusText
    try {
      const body = await res.json()
      detail = body.detail || JSON.stringify(body)
    } catch {
      /* keep statusText */
    }
    throw new Error(detail)
  }
  if (res.status === 204) return null
  return res.json()
}

export const api = {
  listComplaints: (params = {}) => {
    const qs = new URLSearchParams(
      Object.entries(params).filter(([, v]) => v !== undefined && v !== null && v !== '')
    ).toString()
    return request(`/complaints${qs ? `?${qs}` : ''}`)
  },
  getComplaint: (id) => request(`/complaints/${id}`),
  createComplaint: (data) => request('/complaints', { method: 'POST', body: JSON.stringify(data) }),
  updateComplaint: (id, data) => request(`/complaints/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteComplaint: (id) => request(`/complaints/${id}`, { method: 'DELETE' }),
  getStatusHistory: (id) => request(`/complaints/${id}/status-history`),

  aiExtract: (text) => request('/ai/extract', { method: 'POST', body: JSON.stringify({ text }) }),
  aiAssess: (payload) => request('/ai/assess', { method: 'POST', body: JSON.stringify(payload) }),
  aiCompleteness: (text) => request('/ai/completeness', { method: 'POST', body: JSON.stringify({ text }) }),
  aiDuplicates: (id) => request(`/ai/duplicates/${id}`),
  aiAnalyze: (id) => request(`/ai/analyze?complaint_id=${id}`, { method: 'POST' }),

  aiCreateSession: () => request('/ai/session', { method: 'POST' }),
  aiSendMessage: (sessionId, body) => {
    if (body instanceof FormData) {
      return request(`/ai/session/${sessionId}/message`, { method: 'POST', body })
    }
    return request(`/ai/session/${sessionId}/message`, { method: 'POST', body: JSON.stringify(body) })
  },
}
