import { tg } from './telegram.js';

const API_URL = import.meta.env.VITE_API_URL || '';
const DEV_USER_ID = import.meta.env.VITE_DEV_USER_ID || '';

// ─────────────────────────────────────────────────────────────────────────
// Локальная валидация ника — должна совпадать с бэком (см. _validate_nickname).
// ─────────────────────────────────────────────────────────────────────────

const RESERVED = new Set([
  'admin', 'support', 'moderator', 'system', 'cybermate', 'cyber', 'mate',
  'help', 'info', 'official', 'staff',
]);

const BAD_WORDS = new Set([
  'fuck', 'shit', 'bitch', 'asshole', 'cunt',
  'huy', 'huynya', 'pidor', 'pidoras', 'suka', 'blyat', 'blyad', 'nahuy',
  'mudak', 'pizdec', 'pizda', 'eblan', 'ebal', 'manda',
]);

export const NICKNAME_REGEX = /^[a-z0-9](?:[a-z0-9_]{1,18}[a-z0-9])$/;

export function validateNicknameLocal(raw) {
  const n = (raw || '').trim().toLowerCase();
  if (n.length === 0) return { ok: false, code: 'empty' };
  if (n.length < 3) return { ok: false, code: 'too_short' };
  if (n.length > 20) return { ok: false, code: 'too_long' };
  if (!/^[a-z0-9_]+$/.test(n)) return { ok: false, code: 'bad_chars' };
  if (n.startsWith('_')) return { ok: false, code: 'leading_underscore' };
  if (n.endsWith('_')) return { ok: false, code: 'trailing_underscore' };
  if (/__/.test(n)) return { ok: false, code: 'double_underscore' };
  if (!NICKNAME_REGEX.test(n)) return { ok: false, code: 'bad_format' };
  if (RESERVED.has(n) || BAD_WORDS.has(n)) return { ok: false, code: 'forbidden' };
  return { ok: true, value: n };
}

// ─────────────────────────────────────────────────────────────────────────
// HTTP-клиент с авторизацией Telegram WebApp (initData) или dev-заголовком.
// ─────────────────────────────────────────────────────────────────────────

function extractMessage(status, body) {
  const detail = body?.detail;
  if (typeof detail === 'string' && detail) return detail;
  if (detail && typeof detail === 'object') {
    if (typeof detail.reason === 'string') return detail.reason;
    if (typeof detail.msg === 'string') return detail.msg;
    if (Array.isArray(detail)) {
      const parts = detail
        .map((d) => (typeof d === 'string' ? d : d?.msg || d?.reason))
        .filter(Boolean);
      if (parts.length) return parts.join('; ');
    }
  }
  return `HTTP ${status}`;
}

class ApiError extends Error {
  constructor(status, body) {
    super(extractMessage(status, body));
    this.status = status;
    this.body = body;
  }
}

function authHeaders() {
  const headers = { 'Content-Type': 'application/json' };
  const initData = tg?.initData;
  if (initData && initData.length > 0) {
    headers['X-Telegram-Init-Data'] = initData;
  } else if (DEV_USER_ID) {
    headers['X-Dev-User-Id'] = String(DEV_USER_ID);
  }
  return headers;
}

async function request(path, { method = 'GET', body = null, query = null } = {}) {
  let url = `${API_URL}${path}`;
  if (query) {
    const usp = new URLSearchParams();
    for (const [k, v] of Object.entries(query)) {
      if (v !== undefined && v !== null) usp.append(k, String(v));
    }
    const qs = usp.toString();
    if (qs) url += `?${qs}`;
  }
  const res = await fetch(url, {
    method,
    headers: authHeaders(),
    body: body !== null ? JSON.stringify(body) : undefined,
  });
  let payload = null;
  try {
    payload = await res.json();
  } catch (e) {
    payload = null;
  }
  if (!res.ok) throw new ApiError(res.status, payload);
  return payload;
}

// ─────────────────────────────────────────────────────────────────────────
// Эндпоинты ТЗ.
// ─────────────────────────────────────────────────────────────────────────

export async function getMe() {
  return request('/api/me');
}

export async function getMyStats() {
  return request('/api/me/stats');
}

export async function updateMe(patch) {
  const res = await request('/api/me', { method: 'PATCH', body: patch });
  return res.user;
}

export async function deleteMe() {
  return request('/api/me', { method: 'DELETE' });
}

export async function checkNicknameAvailable(nickname) {
  const local = validateNicknameLocal(nickname);
  if (!local.ok) return { available: false, reason: local.code };
  return request('/api/nickname/check', { query: { nickname: local.value } });
}

export async function registerUser(payload) {
  return request('/api/register', { method: 'POST', body: payload });
}

export async function listMyGameProfiles() {
  return request('/api/game-profiles/me');
}

export async function createGameProfile(payload) {
  const res = await request('/api/game-profiles', { method: 'POST', body: payload });
  return res.item;
}

export async function updateProfileStatus(profileId, status) {
  const res = await request(`/api/game-profiles/${profileId}/status`, {
    method: 'PATCH',
    body: { status },
  });
  return res.item;
}

export async function deleteProfile(profileId) {
  return request(`/api/game-profiles/${profileId}`, { method: 'DELETE' });
}

// ─────────────────────────────────────────────────────────────────────────
// Users / Activity / Chats
// ─────────────────────────────────────────────────────────────────────────

export async function searchUsers(q, limit = 20) {
  if (!q || q.trim().length < 2) return { items: [] };
  return request('/api/users/search', { query: { q: q.trim(), limit } });
}

export async function searchPlayers({
  game = 'mlbb',
  region,
  rank,
  skip_liked = true,
  limit = 30,
} = {}) {
  const query = { game, skip_liked, limit };
  if (region) query.region = region;
  if (rank) query.rank = rank;
  return request('/api/search', { query });
}

export async function listActivity(section, limit = 50) {
  return request(`/api/activity/${section}`, { query: { limit } });
}

export async function listChats(page = 1, page_size = 30) {
  return request('/api/chats', { query: { page, page_size } });
}

export async function startChat(targetUserId) {
  return request('/api/chats/start', {
    method: 'POST',
    body: { target_user_id: targetUserId },
  });
}

export async function listChatMessages(chatId, page = 1, page_size = 50) {
  return request(`/api/chats/${chatId}/messages`, { query: { page, page_size } });
}

export async function sendChatMessage(chatId, text) {
  return request(`/api/chats/${chatId}/messages`, {
    method: 'POST',
    body: { text },
  });
}

export async function deleteChat(chatId) {
  return request(`/api/chats/${chatId}`, { method: 'DELETE' });
}

export async function likeUser(targetUserId, game = 'mlbb') {
  return request('/api/interactions/like', {
    method: 'POST',
    body: { target_user_id: targetUserId, game },
  });
}

export async function toggleSubscription(targetUserId) {
  return request('/api/interactions/subscription/toggle', {
    method: 'POST',
    body: { target_user_id: targetUserId },
  });
}

export { ApiError };
