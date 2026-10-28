// Thin API client for the AML Shield FastAPI backend.
// Requests are same-origin (/api/...) and proxied to :8000 by Vite in dev.
// Responses are already camelCase (FastAPI serializes by alias), so they match
// the shapes in src/data/constants.js — components need no reshaping.

const BASE = '/api/v1';

async function req(path, opts = {}) {
  const res = await fetch(BASE + path, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} on ${path}`);
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  // cases
  listCases: () => req('/cases'),
  getCase: (id) => req(`/cases/${id}`),
  claimCase: (id, analystName = 'Priya Venkatesh') =>
    req(`/cases/${id}/claim`, { method: 'POST', body: JSON.stringify({ analyst_name: analystName }) }),
  closeCase: (id, reason, actor = 'Priya Venkatesh') =>
    req(`/cases/${id}/close?actor=${encodeURIComponent(actor)}`, {
      method: 'POST', body: JSON.stringify({ reason }),
    }),
  escalateCase: (id, officerId, note, priority = 'normal') =>
    req(`/cases/${id}/escalate`, {
      method: 'POST', body: JSON.stringify({ officer_id: officerId, note, priority }),
    }),
  handoffCase: (id, recipientHandle, note) =>
    req(`/cases/${id}/handoff`, {
      method: 'POST', body: JSON.stringify({ recipient_handle: recipientHandle, note }),
    }),

  // investigation (the full per-case bundle)
  getInvestigation: (id) => req(`/cases/${id}/investigation`),
  addNote: (id, body, mentions = []) =>
    req(`/cases/${id}/notes`, { method: 'POST', body: JSON.stringify({ body, mentions }) }),
  updateConfidence: (id, confidence) =>
    req(`/cases/${id}/confidence`, { method: 'PATCH', body: JSON.stringify({ confidence }) }),

  // session (logged-in user + team roster)
  getSession: () => req('/session'),

  // STR
  strGenerate: (id, analystConfidence = 87, linkedCaseIds = []) =>
    req(`/cases/${id}/str/generate`, {
      method: 'POST',
      body: JSON.stringify({ analystConfidence, linkedCaseIds }),
    }),
  strJob: (id, jobId) => req(`/cases/${id}/str/generate/${jobId}`),
  strGet: (id) => req(`/cases/${id}/str`),
  strUpdate: (id, { narrative, evidenceChips, entities } = {}) =>
    req(`/cases/${id}/str`, {
      method: 'PUT',
      body: JSON.stringify({ narrative, evidenceChips, entities }),
    }),
  strSubmitReview: (id) => req(`/cases/${id}/str/submit-review`, { method: 'POST' }),
  strFile: (id) => req(`/cases/${id}/str/file`, { method: 'POST' }),

  // copilot (case-grounded, OpenAI-backed)
  copilot: (caseId, question) =>
    req(`/cases/${caseId}/copilot`, { method: 'POST', body: JSON.stringify({ question }) }),
  // streams the answer token-by-token; onToken(text) is called for each chunk
  copilotStream: async (caseId, question, onToken) => {
    const res = await fetch(`${BASE}/cases/${caseId}/copilot/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
    });
    if (!res.ok || !res.body) throw new Error(`${res.status} ${res.statusText}`);
    const reader = res.body.getReader();
    const decoder = new TextDecoder();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });
      if (chunk) onToken(chunk);
    }
  },
  copilotHistory: (caseId) => req(`/cases/${caseId}/copilot/history`),

  // notifications
  listNotifications: () => req('/notifications'),
  markNotificationRead: (id) => req(`/notifications/${id}/read`, { method: 'PATCH' }),
  markAllNotificationsRead: () => req('/notifications/read-all', { method: 'PATCH' }),
  dismissNotification: (id) => req(`/notifications/${id}`, { method: 'DELETE' }),

  // health (used to detect whether the backend is reachable)
  health: () => req('/health'),
};
