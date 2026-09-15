import { getMeta, setMeta, deleteMeta } from './db.js';

const API = '/api/v1';
const FETCH_MS = 6000;
const PING_MS = 2500;

export class ApiError extends Error {
  constructor(message, status, data) {
    super(message);
    this.status = status;
    this.data = data;
  }
}

export class NetworkError extends Error {
  constructor(message = 'Offline') {
    super(message);
    this.offline = true;
  }
}

function fetchTimeout(url, opts = {}, ms = FETCH_MS) {
  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), ms);
  const headers = opts.headers;
  const rest = Object.assign({}, opts);
  delete rest.timeoutMs;
  delete rest.headers;
  return fetch(url, Object.assign({}, rest, { headers, signal: ctrl.signal }))
    .catch(() => {
      throw new NetworkError();
    })
    .finally(() => clearTimeout(timer));
}

async function saveTokens(data) {
  if (data.access) await setMeta('access', data.access);
  if (data.refresh) await setMeta('refresh', data.refresh);
  if (data.username) await setMeta('username', data.username);
}

export async function clearTokens() {
  await deleteMeta('access');
  await deleteMeta('refresh');
}

export async function hasSession() {
  return Boolean(await getMeta('access') || await getMeta('refresh'));
}

async function refreshAccess() {
  const refresh = await getMeta('refresh');
  if (!refresh) return false;
  const res = await fetchTimeout(API + '/refresh', {
    method: 'POST',
    headers: { Authorization: 'Bearer ' + refresh }
  });
  if (!res.ok) {
    await deleteMeta('refresh');
    return false;
  }
  const data = await res.json();
  await saveTokens(data);
  return true;
}

export async function loginWithPassword(username, password) {
  const res = await fetchTimeout(API + '/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username, password })
  });
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError(data.message || 'Login failed', res.status, data);
  }
  const data = await res.json();
  await saveTokens(data);
  return data;
}

export async function loginFromFlaskSession() {
  const res = await fetchTimeout(API + '/pwa/token', {
    method: 'POST',
    credentials: 'same-origin'
  });
  if (!res.ok) return false;
  const data = await res.json();
  await saveTokens(data);
  return true;
}

export async function ensureAuth() {
  if (await getMeta('access')) return true;
  if (!navigator.onLine) return Boolean(await getMeta('refresh'));
  try {
    if (await loginFromFlaskSession()) return true;
  } catch (e) {
    if (!(e instanceof NetworkError)) throw e;
  }
  try {
    if (await refreshAccess()) return true;
  } catch (e) {
    if (e instanceof NetworkError) {
      return Boolean(await getMeta('refresh'));
    }
  }
  return false;
}

async function parseBody(res) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export async function apiFetch(path, opts = {}, retry = true) {
  const access = await getMeta('access');
  const headers = Object.assign({}, opts.headers || {});
  if (access) headers.Authorization = 'Bearer ' + access;
  if (opts.body && typeof opts.body === 'object' && !(opts.body instanceof URLSearchParams)) {
    headers['Content-Type'] = 'application/json';
    opts = Object.assign({}, opts, { body: JSON.stringify(opts.body) });
  }
  const timeoutMs = opts.timeoutMs || FETCH_MS;
  const fetchOpts = Object.assign({}, opts, { headers, credentials: 'same-origin' });
  delete fetchOpts.timeoutMs;
  const res = await fetchTimeout(API + path, fetchOpts, timeoutMs);
  if ((res.status === 401 || res.status === 422) && retry) {
    const ok = await refreshAccess();
    if (ok) return apiFetch(path, opts, false);
    await deleteMeta('access');
    const fromSession = await loginFromFlaskSession().catch(() => false);
    if (fromSession) return apiFetch(path, opts, false);
    throw new ApiError('Session expired', res.status);
  }
  const data = await parseBody(res);
  if (!res.ok) {
    const msg = (data && data.message) || ('HTTP ' + res.status);
    throw new ApiError(msg, res.status, data);
  }
  return data;
}

function filenameFromDisposition(header, fallback) {
  if (!header) return fallback;
  const star = /filename\*=UTF-8''([^;]+)/i.exec(header);
  if (star) {
    try { return decodeURIComponent(star[1]); } catch { /* keep going */ }
  }
  const plain = /filename="?([^";]+)"?/i.exec(header);
  return plain ? plain[1] : fallback;
}

export async function apiFetchBlob(path, opts = {}, retry = true) {
  const access = await getMeta('access');
  const headers = Object.assign({}, opts.headers || {});
  if (access) headers.Authorization = 'Bearer ' + access;
  const timeoutMs = opts.timeoutMs || FETCH_MS;
  const fetchOpts = Object.assign({}, opts, { headers, credentials: 'same-origin' });
  delete fetchOpts.timeoutMs;
  const res = await fetchTimeout(API + path, fetchOpts, timeoutMs);
  if ((res.status === 401 || res.status === 422) && retry) {
    const ok = await refreshAccess();
    if (ok) return apiFetchBlob(path, opts, false);
    await deleteMeta('access');
    const fromSession = await loginFromFlaskSession().catch(() => false);
    if (fromSession) return apiFetchBlob(path, opts, false);
    throw new ApiError('Session expired', res.status);
  }
  if (!res.ok) {
    const data = await res.json().catch(() => ({}));
    throw new ApiError((data && data.message) || ('HTTP ' + res.status), res.status, data);
  }
  const blob = await res.blob();
  const filename = filenameFromDisposition(res.headers.get('Content-Disposition'), '');
  return { blob, filename };
}

export async function ping() {
  try {
    const res = await fetchTimeout('/health', { method: 'GET' }, PING_MS);
    return res.ok;
  } catch {
    return false;
  }
}
