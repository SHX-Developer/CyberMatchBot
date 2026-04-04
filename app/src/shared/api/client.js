import { API_BASE_URL } from '../config/api';

function withQuery(url, params = {}) {
  const target = new URL(url, API_BASE_URL.endsWith('/') ? API_BASE_URL : `${API_BASE_URL}/`);
  Object.entries(params).forEach(([key, value]) => {
    if (value === undefined || value === null || value === '') return;
    target.searchParams.set(key, String(value));
  });
  return target.toString();
}

async function parseResponse(response) {
  if (response.ok) {
    if (response.status === 204) return null;
    return response.json();
  }
  let detail = `HTTP ${response.status}`;
  try {
    const payload = await response.json();
    if (payload?.detail) {
      detail = typeof payload.detail === 'string' ? payload.detail : JSON.stringify(payload.detail);
    }
  } catch {
    // noop
  }
  throw new Error(detail);
}

export async function apiGet(path, params = {}) {
  const response = await fetch(withQuery(path, params));
  return parseResponse(response);
}

export async function apiPost(path, body, params = {}) {
  const response = await fetch(withQuery(path, params), {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  return parseResponse(response);
}

export async function apiDelete(path, params = {}) {
  const response = await fetch(withQuery(path, params), { method: 'DELETE' });
  return parseResponse(response);
}

export const webApi = {
  health: () => apiGet('health'),
  profile: (userId) => apiGet('profile', { user_id: userId }),
  myProfiles: (userId) => apiGet('profiles', { user_id: userId }),
  saveMlbbProfile: (payload) => apiPost('profiles/mlbb', payload),
  resetProfile: (userId, profileId) => apiPost(`profiles/${profileId}/reset`, {}, { user_id: userId }),
  deleteProfile: (userId, profileId) => apiDelete(`profiles/${profileId}`, { user_id: userId }),
  searchProfiles: (userId, game = 'mlbb') => apiGet('search', { user_id: userId, game }),
  like: (userId, targetUserId, game = 'mlbb') => apiPost('interactions/like', {
    user_id: userId,
    target_user_id: targetUserId,
    game,
  }),
  toggleSubscription: (userId, targetUserId) =>
    apiPost('interactions/subscription/toggle', {
      user_id: userId,
      target_user_id: targetUserId,
    }),
  sendDirectMessage: (userId, targetUserId, text) =>
    apiPost('interactions/message', {
      user_id: userId,
      target_user_id: targetUserId,
      text,
    }),
  activity: (section, userId, limit = 50) => apiGet(`activity/${section}`, { user_id: userId, limit }),
  chats: (userId, page = 1, pageSize = 10) => apiGet('chats', { user_id: userId, page, page_size: pageSize }),
  startChat: (userId, target) => apiPost('chats/start', { user_id: userId, target }),
  chatMessages: (chatId, userId, page = 1, pageSize = 10) =>
    apiGet(`chats/${chatId}/messages`, { user_id: userId, page, page_size: pageSize }),
  sendChatMessage: (chatId, userId, text) =>
    apiPost(`chats/${chatId}/messages`, { user_id: userId, text }),
  deleteChat: (chatId, userId) => apiDelete(`chats/${chatId}`, { user_id: userId }),
};
