import * as db from './db.js';
import * as api from './api.js';
import * as sync from './sync.js';
import { renderMarkdown } from './markdown.js';

const APP_NAME = window.RN?.appName || 'Razor Notes';
const HOME_LATEST = 20;
const ALL_PAGE_SIZE = 25;
const SEARCH_MIN = 3;
const root = document.getElementById('app');
let toastTimer = null;
let searchQuery = '';
let online = navigator.onLine;
let staleTimer = null;
let staleWatchId = null;
let staleWatchMode = null;
let staleMinimized = false;
let keepMineUntilLeave = false;
let staleChecking = false;
let staleBaseline = '';
let lastFocusSync = 0;
let openInEdit = new Set();
let saveMode = 'auto';
let connecting = true;
let downloadOffer = false;

function esc(s) {
  return String(s ?? '').replace(/[&<>"']/g, (c) => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  }[c]));
}

function toast(msg, ms = 2800) {
  let el = document.getElementById('toast');
  if (!el) {
    el = document.createElement('div');
    el.id = 'toast';
    el.className = 'toast';
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add('show');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove('show'), ms);
}

function toastConflicts(conflicts) {
  if (!conflicts || !conflicts.length) return false;
  const names = conflicts.map((c) => c.conflictTitle || 'Conflict copy').join(', ');
  toast('Server had a newer version. Your edit was saved as "' + names + '".', 6000);
  return true;
}

function closeClipModal() {
  const el = document.getElementById('clip-modal');
  if (el) el.remove();
  const pending = closeClipModal._finish;
  if (pending) {
    closeClipModal._finish = null;
    pending(null);
  }
}

function showClipModal({ title, hint, text = '', readonly = false, okLabel = 'Save', showCopy = false }) {
  closeClipModal();
  return new Promise((resolve) => {
    const wrap = document.createElement('div');
    wrap.id = 'clip-modal';
    wrap.className = 'clip-modal';
    wrap.innerHTML = `
      <div class="clip-panel" role="dialog" aria-modal="true" aria-labelledby="clip-title">
        <h2 id="clip-title">${esc(title)}</h2>
        <p class="muted">${esc(hint)}</p>
        <textarea id="clip-text" rows="7"${readonly ? ' readonly' : ''}></textarea>
        <div class="row-actions">
          ${showCopy ? '<button class="btn solid" type="button" data-clip="copy">Copy</button>' : ''}
          <button class="btn ${showCopy ? 'ghost' : 'solid'}" type="button" data-clip="ok">${esc(okLabel)}</button>
          <button class="btn ghost" type="button" data-clip="cancel">Cancel</button>
        </div>
      </div>`;
    document.body.appendChild(wrap);
    const ta = wrap.querySelector('#clip-text');
    ta.value = text;
    ta.focus();
    if (readonly || text) ta.select();
    let settled = false;
    const onKey = (ev) => {
      if (ev.key === 'Escape') {
        ev.preventDefault();
        finish(null);
      }
    };
    const finish = (value) => {
      if (settled) return;
      settled = true;
      closeClipModal._finish = null;
      document.removeEventListener('keydown', onKey);
      const el = document.getElementById('clip-modal');
      if (el) el.remove();
      resolve(value);
    };
    closeClipModal._finish = finish;
    document.addEventListener('keydown', onKey);
    wrap.addEventListener('click', (ev) => {
      if (ev.target === wrap) finish(null);
    });
    wrap.addEventListener('click', async (ev) => {
      const btn = ev.target.closest('[data-clip]');
      if (!btn) return;
      if (btn.dataset.clip === 'cancel') {
        finish(null);
        return;
      }
      if (btn.dataset.clip === 'copy') {
        ta.select();
        let ok = false;
        if (navigator.clipboard && navigator.clipboard.writeText) {
          try {
            await navigator.clipboard.writeText(ta.value);
            ok = true;
          } catch { /* try execCommand */ }
        }
        if (!ok) {
          try { ok = document.execCommand('copy'); } catch { ok = false; }
        }
        toast(ok ? 'Clipboard loaded!' : 'Select the text and copy it');
        if (ok) finish(ta.value);
        return;
      }
      if (btn.dataset.clip === 'ok') finish(ta.value);
    });
  });
}

async function readDeviceClipboard() {
  if (navigator.clipboard && navigator.clipboard.readText) {
    try {
      return await navigator.clipboard.readText();
    } catch { /* need paste fallback */ }
  }
  return null;
}

async function writeDeviceClipboard(text) {
  if (navigator.clipboard && navigator.clipboard.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch { /* show copy fallback */ }
  }
  return false;
}

async function saveClipboardToServer() {
  if (!filesOnline()) {
    toast('Connect to use clipboard');
    return;
  }
  let text = await readDeviceClipboard();
  if (text == null) {
    text = await showClipModal({
      title: 'Save clipboard',
      hint: 'This browser blocked clipboard access. Paste the text to store on the server.',
      okLabel: 'Save'
    });
    if (text == null) return;
  }
  try {
    await api.apiFetch('/clipboard', { method: 'POST', body: { key: text } });
    toast('Clipboard saved!');
  } catch (e) {
    toast(e.message || 'Clipboard save failed');
  }
}

async function loadClipboardFromServer() {
  if (!filesOnline()) {
    toast('Connect to use clipboard');
    return;
  }
  let data;
  try {
    data = await api.apiFetch('/clipboard');
  } catch (e) {
    toast(e.message || 'Clipboard load failed');
    return;
  }
  const text = data && data.clipboard != null ? String(data.clipboard) : '';
  if (await writeDeviceClipboard(text)) {
    toast(text ? 'Clipboard loaded!' : 'Clipboard is empty');
    return;
  }
  await showClipModal({
    title: 'Clipboard from server',
    hint: 'Automatic copy failed. Copy the text below.',
    text,
    readonly: true,
    okLabel: 'Done',
    showCopy: true
  });
}

function hideStaleUi() {
  const banner = document.getElementById('stale-banner');
  const dot = document.getElementById('stale-dot');
  if (banner) banner.hidden = true;
  if (dot) dot.hidden = true;
}

function stopStaleWatch() {
  clearInterval(staleTimer);
  staleTimer = null;
  staleWatchId = null;
  staleWatchMode = null;
  staleMinimized = false;
  keepMineUntilLeave = false;
  hideStaleUi();
}

function editHasUnsaved() {
  if (!root._edit) return false;
  const title = root.querySelector('#title');
  const body = root.querySelector('#body');
  const n = root._edit.note;
  if (!n) return false;
  if (n.dirty) return true;
  if (!title || !body) return Boolean(n.dirty);
  return title.value.trim() !== (n.title || '').trim() || body.value !== (n.text || '');
}

function paintStaleBanner() {
  const banner = document.getElementById('stale-banner');
  if (!banner) return;
  const reload = banner.querySelector('[data-stale="reload"]');
  const keep = banner.querySelector('[data-stale="keep"]');
  const load = banner.querySelector('[data-stale="load"]');
  const dirtyEdit = staleWatchMode === 'edit' && editHasUnsaved();
  if (reload) reload.hidden = dirtyEdit;
  if (keep) keep.hidden = !dirtyEdit;
  if (load) load.hidden = !dirtyEdit;
}

function showStaleUi() {
  ensureStaleEls();
  paintStaleBanner();
  const banner = document.getElementById('stale-banner');
  const dot = document.getElementById('stale-dot');
  if (staleMinimized || keepMineUntilLeave) {
    if (banner) banner.hidden = true;
    if (dot) dot.hidden = false;
    return;
  }
  if (banner) banner.hidden = false;
  if (dot) dot.hidden = true;
}

function ensureStaleEls() {
  if (document.getElementById('stale-banner')) return;
  const banner = document.createElement('div');
  banner.id = 'stale-banner';
  banner.className = 'stale-banner';
  banner.hidden = true;
  banner.innerHTML = `
    <div class="stale-banner-text">This note changed on the server.</div>
    <div class="stale-banner-actions">
      <button class="btn solid" data-stale="reload">Reload</button>
      <button class="btn ghost" data-stale="keep">Keep mine</button>
      <button class="btn ghost" data-stale="load">Load server</button>
      <button class="btn ghost" data-stale="min" aria-label="Minimize">–</button>
    </div>`;
  const dot = document.createElement('button');
  dot.id = 'stale-dot';
  dot.className = 'stale-dot';
  dot.type = 'button';
  dot.hidden = true;
  dot.setAttribute('aria-label', 'Server has a newer version');
  dot.textContent = '!';
  document.body.appendChild(banner);
  document.body.appendChild(dot);
  banner.addEventListener('click', (ev) => {
    const btn = ev.target.closest('[data-stale]');
    if (!btn) return;
    ev.preventDefault();
    onStaleAction(btn.dataset.stale);
  });
  dot.addEventListener('click', (ev) => {
    ev.preventDefault();
    onStaleAction('expand');
  });
}

function startStaleWatch(id, mode, hash) {
  clearInterval(staleTimer);
  staleTimer = null;
  hideStaleUi();
  staleMinimized = false;
  keepMineUntilLeave = false;
  staleWatchId = id;
  staleWatchMode = mode;
  staleBaseline = hash || '';
  if (!filesOnline() || db.isLocalId(id) || id == null || id === 'new') return;
  ensureStaleEls();
  staleTimer = setInterval(() => { checkStale(); }, sync.STALE_POLL_MS);
}

async function checkStale() {
  if (!staleWatchId || staleChecking || document.hidden) return;
  if (!filesOnline() || db.isLocalId(staleWatchId)) return;
  staleChecking = true;
  try {
    const remote = await sync.serverHash(staleWatchId);
    const local = await db.getNote(staleWatchId);
    const known = (local && local.v_hash) || staleBaseline;
    if (remote && known && remote !== known) showStaleUi();
    else if (remote && !known) showStaleUi();
    else {
      keepMineUntilLeave = false;
      staleMinimized = false;
      hideStaleUi();
    }
  } catch {
    /* stay quiet while polling */
  } finally {
    staleChecking = false;
  }
}

async function onStaleAction(act) {
  if (act === 'min') {
    staleMinimized = true;
    showStaleUi();
    return;
  }
  if (act === 'expand') {
    staleMinimized = false;
    keepMineUntilLeave = false;
    showStaleUi();
    return;
  }
  if (act === 'keep') {
    if (root._flushEdit) await root._flushEdit(true, true);
    root._holdPush = true;
    keepMineUntilLeave = true;
    staleMinimized = true;
    showStaleUi();
    return;
  }
  const id = staleWatchId;
  const mode = staleWatchMode;
  if (!id) return;
  try {
    if (act === 'reload') {
      await sync.fetchNote(id);
      hideStaleUi();
      if (mode === 'edit') await renderEdit(id);
      else await renderView(id);
      return;
    }
    if (act === 'load') {
      if (root._flushEdit) await root._flushEdit(true, true);
      const result = await sync.takeServerVersion(id);
      if (result.conflict) toastConflicts([result]);
      hideStaleUi();
      keepMineUntilLeave = false;
      if (mode === 'edit') await renderEdit(id);
      else await renderView(id);
    }
  } catch (e) {
    toast(e.message || 'Could not load server copy');
  }
}

function applyTheme(theme) {
  document.documentElement.setAttribute('data-theme', theme);
  localStorage.setItem('rn-theme', theme);
}

function currentTheme() {
  return localStorage.getItem('rn-theme')
    || (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
}

function parseHash() {
  const raw = (location.hash || '#/').replace(/^#/, '') || '/';
  const parts = raw.split('/').filter(Boolean);
  if (!parts.length) return { name: 'list' };
  if (parts[0] === 'all') {
    const page = Math.max(0, parseInt(parts[1], 10) || 0);
    return { name: 'all', page };
  }
  if (parts[0] === 'note' && parts[1]) return { name: 'view', id: coerceId(parts[1]) };
  if (parts[0] === 'edit') return { name: 'edit', id: parts[1] ? coerceId(parts[1]) : 'new' };
  if (parts[0] === 'settings') return { name: 'settings' };
  return { name: 'list' };
}

function coerceId(s) {
  if (s.startsWith('l')) return s;
  const n = Number(s);
  return Number.isFinite(n) ? n : s;
}

function go(path) {
  location.hash = '#' + path;
}

async function loadPrefs() {
  openInEdit = await db.openInEditIds();
  saveMode = await db.getSaveMode();
}

function editingNoteId() {
  return (root._edit && root._edit.note && root._edit.note.id != null) ? root._edit.note.id : null;
}

function skipEditIds() {
  const id = editingNoteId();
  return id == null ? [] : [id];
}

function noteHref(n) {
  const id = encodeURIComponent(n.id);
  return openInEdit.has(String(n.id)) ? `#/edit/${id}` : `#/note/${id}`;
}

function iconBtn(action, label, text, { disabled = false, extraClass = '' } = {}) {
  const cls = extraClass ? 'icon-btn ' + extraClass : 'icon-btn';
  return `<button class="${cls}" data-act="${action}" aria-label="${esc(label)}" title="${esc(label)}"${disabled ? ' disabled' : ''}>${text}</button>`;
}

function statusClass() {
  if (db.isForceLocal()) return 'local';
  if (sync.isSyncing()) return 'syncing';
  if (connecting) return 'syncing';
  if (!online) return 'offline';
  return '';
}

function statusText() {
  if (db.isForceLocal()) return 'Local only (this session)';
  if (sync.isSyncing()) return 'Syncing…';
  if (connecting) return 'Connecting…';
  if (!online) return 'Offline';
  return 'Online';
}

function formatBytes(n) {
  if (!Number.isFinite(n) || n <= 0) return '0 B';
  const units = ['B', 'KB', 'MB', 'GB'];
  let i = 0;
  let x = n;
  while (x >= 1024 && i < units.length - 1) {
    x /= 1024;
    i += 1;
  }
  return (i === 0 ? String(Math.round(x)) : x.toFixed(1)) + ' ' + units[i];
}

function notesWithBody(notes) {
  return notes.filter((n) => n.text && !n.body_missing).length;
}

async function requestPersistentStorage() {
  if (!navigator.storage || !navigator.storage.persist) return false;
  try {
    if (await navigator.storage.persisted()) return true;
    return await navigator.storage.persist();
  } catch {
    return false;
  }
}

async function storageInfo() {
  let persistent = false;
  let quota = '';
  try {
    if (navigator.storage && navigator.storage.persisted) {
      persistent = await navigator.storage.persisted();
    }
  } catch { /* ignore */ }
  try {
    if (navigator.storage && navigator.storage.estimate) {
      const est = await navigator.storage.estimate();
      quota = formatBytes(est.usage || 0) + ' of ' + formatBytes(est.quota || 0);
    }
  } catch { /* ignore */ }
  return { persistent, quota };
}

async function maybePrepareDownloadOffer() {
  downloadOffer = false;
  if (!filesOnline()) return;
  if (await db.getMeta('asked_full_download', false)) return;
  const mode = await db.getSyncMode();
  if (mode === 'full_mirror' || mode === 'remote_only') return;
  const notes = await db.allNotes();
  if (notesWithBody(notes) >= 30) {
    await db.setMeta('asked_full_download', true);
    return;
  }
  downloadOffer = true;
}

function downloadOfferHtml() {
  if (!downloadOffer) return '';
  return `<div class="offline-offer">
    <div>Download all notes so they work without internet?</div>
    <div class="row-actions">
      <button class="btn solid" data-act="download-all">Download all</button>
      <button class="btn ghost" data-act="dismiss-download">Not now</button>
    </div>
  </div>`;
}

function updateStatusBar() {
  const bar = document.querySelector('.status-bar');
  if (!bar || !bar.lastElementChild) return;
  bar.className = 'status-bar ' + statusClass();
  bar.lastElementChild.textContent = statusText();
}

function registerServiceWorker() {
  if (!('serviceWorker' in navigator)) return;
  navigator.serviceWorker.register('/app/sw.js', {
    scope: '/app/',
    updateViaCache: 'none'
  }).then((reg) => {
    if (navigator.onLine) {
      try { reg.update(); } catch { /* ignore */ }
    }
  }).catch(() => {});
}

function shell(title, inner, { back = false, fab = false, editFab = false, extra = '', mainClass = '' } = {}) {
  const standalone = matchMedia('(display-mode: standalone)').matches || navigator.standalone;
  const onHome = title === APP_NAME;
  const pageTitle = onHome ? '<span class="topbar-spacer"></span>' : `<h1>${esc(title)}</h1>`;
  return `
    <header class="topbar">
      ${back ? iconBtn('back', 'Back', '←') : ''}
      <button class="brand" data-act="home" aria-label="Home">${esc(APP_NAME)}</button>
      ${pageTitle}
      ${iconBtn('clip-set', 'Save clipboard to server', 'Set', { disabled: !filesOnline(), extraClass: 'clip-set' })}
      ${iconBtn('clip-get', 'Load clipboard from server', 'Get', { disabled: !filesOnline(), extraClass: 'clip-get' })}
      ${iconBtn('theme', 'Toggle theme', '◐')}
      ${iconBtn('settings', 'Settings', '⚙')}
    </header>
    <div class="status-bar ${statusClass()}"><span class="dot"></span><span>${esc(statusText())}</span></div>
    ${!standalone && extra === 'list' ? `<div class="install-hint">Install: browser menu → Add to Home screen. Then this app works offline.</div>` : ''}
    <div class="main ${esc(mainClass)}">${inner}</div>
    ${fab ? `<button class="fab" data-act="new" aria-label="New note">+</button>` : ''}
    ${editFab ? `<button class="fab fab-edit" data-act="edit-note" aria-label="Edit note">✎</button>` : ''}
  `;
}

async function requireAuth() {
  try {
    if (await api.ensureAuth()) return true;
  } catch (e) {
    if (e instanceof api.NetworkError) {
      if (await api.hasSession()) return true;
      renderLogin('Server unreachable. Log in once while online, or use the full site.');
      return false;
    }
  }
  renderLogin();
  return false;
}

function renderLogin(msg = '') {
  root.innerHTML = `
    <header class="topbar"><h1>${esc(APP_NAME)}</h1>${iconBtn('theme', 'Toggle theme', '◐')}</header>
    <div class="login">
      <p>Sign in to this Razor Notes server.</p>
      <form id="login-form">
        <label>Username or email</label>
        <input name="username" autocomplete="username" required>
        <label>Password</label>
        <input name="password" type="password" autocomplete="current-password" required>
        <div class="err">${esc(msg)}</div>
        <button class="btn solid" type="submit">Sign in</button>
      </form>
      <p class="muted"><a class="inline" href="/">Open full site</a></p>
    </div>
  `;
  root.querySelector('#login-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const fd = new FormData(ev.target);
    try {
      await api.loginWithPassword(fd.get('username'), fd.get('password'));
      await requestPersistentStorage();
      await route();
    } catch (e) {
      ev.target.querySelector('.err').textContent = e.message || 'Login failed';
    }
  });
}

function noteCard(n) {
  const cls = ['card'];
  if (n.dirty) cls.push('dirty');
  if (db.isLocalId(n.id)) cls.push('local-only');
  const preview = sync.listPreview(n);
  const openEdit = openInEdit.has(String(n.id));
  const badges = [
    n.pinned ? '<span class="badge">Pinned</span>' : '',
    n.note_type === 1 ? '<span class="badge">Task</span>' : '',
    openEdit ? '<span class="badge">Edit</span>' : '',
    n.held ? '<span class="badge">Draft</span>' : (n.dirty ? '<span class="badge">Pending</span>' : '')
  ].join('');
  return `<a class="${cls.join(' ')}" href="${noteHref(n)}">
    <div>
      <h3>${badges}${esc(n.title || 'Untitled')}</h3>
      <p>${esc(preview)}${preview.length >= 100 ? '…' : ''}</p>
    </div>
  </a>`;
}

function filesOnline() {
  return online && !db.isForceLocal();
}

function byDateDesc(a, b) {
  return String(b.date_mod || '').localeCompare(String(a.date_mod || ''));
}

async function loadNotes() {
  let notes = await db.allNotes();
  const mode = await db.getSyncMode();
  if (mode === 'remote_only' && filesOnline()) {
    try {
      const meta = await api.apiFetch('/notes/meta');
      const dirty = notes.filter((n) => n.dirty);
      const remote = meta.map((m) => ({
        id: m._id ?? m.id,
        title: m.title,
        preview: m.preview,
        text: '',
        pinned: Boolean(m.pinned),
        relevant: m.relevant !== false,
        date_mod: m.date_mod,
        v_hash: m.v_hash,
        note_type: m.note_type || 0
      }));
      const dirtyIds = new Set(dirty.map((d) => String(d.id)));
      notes = dirty.concat(remote.filter((n) => !dirtyIds.has(String(n.id))));
    } catch { /* keep cache */ }
  }
  return notes;
}

function bindSearch() {
  const search = root.querySelector('#search');
  if (!search) return;
  search.addEventListener('input', () => {
    searchQuery = search.value;
    clearTimeout(search._t);
    search._t = setTimeout(() => route(), 280);
  });
  if (searchQuery) {
    search.focus();
    search.setSelectionRange(searchQuery.length, searchQuery.length);
  }
}

function matchesQuery(n, q) {
  if (!q) return true;
  return (n.title || '').toLowerCase().includes(q) || (n.text || '').toLowerCase().includes(q)
    || (n.preview || '').toLowerCase().includes(q);
}

async function useServerSearch() {
  return filesOnline() && !(await db.isSearchLocalOnly());
}

async function searchPlaceholder() {
  return (await useServerSearch()) ? 'Search notes…' : 'Search cached notes…';
}

function searchBox(ph) {
  return `<input class="search" id="search" placeholder="${esc(ph)}" value="${esc(searchQuery)}">`;
}

async function runSearch(cached) {
  const q = searchQuery.trim();
  if (!q) return { kind: 'home' };
  const server = await useServerSearch();
  if (server && q.length < SEARCH_MIN) {
    return { kind: 'hint', message: 'Type at least 3 characters to search the server.' };
  }
  if (server) {
    try {
      const data = await api.apiFetch('/search', { method: 'POST', body: { key: q } });
      const localById = new Map(cached.map((n) => [String(n.id), n]));
      const hits = Object.entries(data || {}).map(([id, pair]) => {
        const loc = localById.get(String(id));
        const title = (Array.isArray(pair) ? pair[0] : '') || '';
        const snippet = (Array.isArray(pair) ? pair[1] : '') || '';
        const coerced = coerceId(id);
        if (loc) {
          return Object.assign({}, loc, {
            title: loc.dirty ? loc.title : (title || loc.title),
            preview: snippet || loc.preview || ''
          });
        }
        return {
          id: coerced,
          title,
          preview: snippet,
          text: '',
          pinned: false,
          relevant: true,
          date_mod: '',
          note_type: 0
        };
      });
      const hitIds = new Set(hits.map((h) => String(h.id)));
      const qLower = q.toLowerCase();
      const extra = cached.filter((n) =>
        (n.dirty || db.isLocalId(n.id)) && matchesQuery(n, qLower) && !hitIds.has(String(n.id)));
      return { kind: 'results', notes: extra.concat(hits), source: 'server' };
    } catch {
      const qLower = q.toLowerCase();
      return {
        kind: 'results',
        notes: cached.filter((n) => matchesQuery(n, qLower)).sort(byDateDesc),
        source: 'fallback'
      };
    }
  }
  const qLower = q.toLowerCase();
  return {
    kind: 'results',
    notes: cached.filter((n) => matchesQuery(n, qLower)).sort(byDateDesc),
    source: 'local'
  };
}

function homeBody(notes, ph, hint) {
  const pinned = notes.filter((n) => n.pinned && n.relevant !== false).sort(byDateDesc);
  const rest = notes.filter((n) => !n.pinned && (n.relevant !== false || n.dirty || db.isLocalId(n.id))).sort(byDateDesc);
  const latest = rest.slice(0, HOME_LATEST);
  const showAll = notes.length > pinned.length + latest.length || rest.length > HOME_LATEST;
  return `
    ${searchBox(ph)}
    ${hint ? `<p class="muted search-hint">${esc(hint)}</p>` : ''}
    ${downloadOfferHtml()}
    ${notes.length === 0 ? `<div class="empty">No notes on this device yet. Open notes while online, or download all in Settings.</div>` : ''}
    <div class="home-cols">
      ${pinned.length ? `<section class="home-col"><div class="section-label">Pinned</div>${pinned.map(noteCard).join('')}</section>` : ''}
      ${latest.length ? `<section class="home-col"><div class="section-label">Latest</div>${latest.map(noteCard).join('')}</section>` : ''}
    </div>
    ${showAll ? `<div class="view-all-wrap"><button class="btn ghost" data-act="view-all">View all</button></div>` : ''}
  `;
}

async function renderList() {
  const notes = await loadNotes();
  const ph = await searchPlaceholder();
  const found = await runSearch(notes);
  if (found.kind === 'results') {
    const label = found.source === 'fallback'
      ? 'Cached results (server unreachable)'
      : 'Results';
    const body = `
      ${searchBox(ph)}
      ${downloadOfferHtml()}
      ${found.notes.length === 0 ? `<div class="empty">No matches.</div>` : `<div class="section-label">${label}</div>${found.notes.map(noteCard).join('')}`}
    `;
    root.innerHTML = shell(APP_NAME, body, { fab: true, extra: 'list' });
    bindSearch();
    return;
  }
  const hint = found.kind === 'hint' ? found.message : '';
  root.innerHTML = shell(APP_NAME, homeBody(notes, ph, hint), { fab: true, extra: 'list', mainClass: 'home-screen' });
  bindSearch();
}

async function renderAll(page) {
  const cached = await loadNotes();
  const ph = await searchPlaceholder();
  const found = await runSearch(cached);
  if (found.kind === 'results') {
    const body = `
      ${searchBox(ph)}
      ${downloadOfferHtml()}
      ${found.notes.length === 0 ? `<div class="empty">No matches.</div>` : `<div class="section-label">Results</div>${found.notes.map(noteCard).join('')}`}
    `;
    root.innerHTML = shell('All notes', body, { back: true, fab: true });
    bindSearch();
    return;
  }
  let notes = cached.slice().sort(byDateDesc);
  const pages = Math.max(1, Math.ceil(notes.length / ALL_PAGE_SIZE));
  page = Math.min(Math.max(0, page), pages - 1);
  const slice = notes.slice(page * ALL_PAGE_SIZE, (page + 1) * ALL_PAGE_SIZE);
  const hint = found.kind === 'hint' ? `<p class="muted search-hint">${esc(found.message)}</p>` : '';
  const body = `
    ${searchBox(ph)}
    ${downloadOfferHtml()}
    ${hint}
    ${notes.length === 0 ? `<div class="empty">No notes.</div>` : `<div class="section-label">All notes</div>${slice.map(noteCard).join('')}`}
    ${notes.length > ALL_PAGE_SIZE ? `<div class="pager">
      <button class="btn ghost" data-act="page-prev" ${page <= 0 ? 'disabled' : ''}>Prev</button>
      <span class="muted">Page ${page + 1} / ${pages}</span>
      <button class="btn ghost" data-act="page-next" ${page >= pages - 1 ? 'disabled' : ''}>Next</button>
    </div>` : ''}
  `;
  root.innerHTML = shell('All notes', body, { back: true, fab: true });
  root.dataset.page = String(page);
  bindSearch();
}

async function renderView(id) {
  let note;
  try {
    note = await sync.cacheOpenedNote(id);
  } catch (e) {
    root.innerHTML = shell('Note', `<div class="empty">${esc(e.message || 'Could not load note.')}</div>`, { back: true });
    return;
  }
  let filesHtml = '';
  if (!db.isLocalId(note.id)) {
    const canDl = filesOnline();
    let files = [];
    if (canDl) {
      try { files = await api.apiFetch('/note/' + note.id + '/files'); } catch { files = []; }
    }
    if (files.length) {
      const items = files.map((f) => `
        <li>
          <span class="fname">${esc(f.file_name)}</span>
          <button class="btn ghost" data-act="download-file" data-file-id="${esc(f.file_id_name)}" data-file-name="${esc(f.file_name)}" ${canDl ? '' : 'disabled'}>Download</button>
        </li>`).join('');
      filesHtml = `<div class="section-label">Attachments</div><ul class="files-list">${items}</ul>
        ${canDl ? '' : '<p class="muted">Downloads need a connection.</p>'}`;
    }
  }
  const openEdit = openInEdit.has(String(note.id));
  const body = `
    <article class="note-view">
      <div class="row-actions">
        <button class="btn solid" data-act="edit-note">Edit</button>
        <button class="btn ghost" data-act="toggle-pin">${note.pinned ? 'Unpin' : 'Pin'}</button>
        <button class="btn ghost" data-act="toggle-rel">${note.relevant === false ? 'Show on home' : 'Hide from home'}</button>
      </div>
      <label class="muted open-edit-toggle"><input type="checkbox" id="open-in-edit" ${openEdit ? 'checked' : ''}> Always open in editor</label>
      <h2 class="title">${esc(note.title || 'Untitled')}</h2>
      <div class="note-meta">${esc(note.date_mod || '')}${note.held ? ' · draft on this device' : (note.dirty ? ' · pending sync' : '')}${db.isLocalId(note.id) ? ' · not uploaded yet' : ''}</div>
      <div class="note-body">${renderMarkdown(note.text || '')}</div>
      ${filesHtml}
    </article>
  `;
  root.innerHTML = shell(note.title || 'Note', body, { back: true, editFab: true });
  root.dataset.noteId = String(note.id);
  startStaleWatch(note.id, 'view', note.v_hash);
}

async function renderEdit(id) {
  let note = { id: db.newLocalId(), title: '', text: '', pinned: false, relevant: true, note_type: 0, v_hash: '', base_hash: '' };
  if (id !== 'new') {
    try {
      note = await sync.cacheOpenedNote(id);
      note.base_hash = note.v_hash;
    } catch (e) {
      root.innerHTML = shell('Edit', `<div class="empty">${esc(e.message)}</div>`, { back: true });
      return;
    }
  }
  const openEdit = openInEdit.has(String(note.id));
  const saveLabel = saveMode === 'auto' ? 'Done' : 'Save';
  const body = `
    <div class="edit-form">
      <input class="edit-title" id="title" placeholder="Title" value="${esc(note.title)}">
      <textarea class="edit-body" id="body" placeholder="Write…">${esc(note.text)}</textarea>
      <div class="row-actions">
        <button class="btn solid" data-act="save">${saveLabel}</button>
        <button class="btn ghost" data-act="view-note">View note</button>
        <label class="muted"><input type="checkbox" id="pinned" ${note.pinned ? 'checked' : ''}> Pinned</label>
        <label class="muted"><input type="checkbox" id="relevant" ${note.relevant !== false ? 'checked' : ''}> Show on home</label>
        <label class="muted"><input type="checkbox" id="open-in-edit" ${openEdit ? 'checked' : ''}> Always open in editor</label>
      </div>
    </div>
  `;
  root.innerHTML = shell(id === 'new' ? 'New note' : 'Edit', body, { back: true, mainClass: 'edit-screen' });
  const state = {
    note,
    orig: {
      title: note.title || '',
      text: note.text || '',
      pinned: Boolean(note.pinned),
      relevant: note.relevant !== false
    }
  };
  root._edit = state;
  root._holdPush = false;
  root.dataset.noteId = String(note.id);
  let saveChain = Promise.resolve();
  const save = (andLeave, silent, localOnly) => {
    const job = async () => {
      const titleEl = root.querySelector('#title');
      const bodyEl = root.querySelector('#body');
      if (!titleEl || !bodyEl) return;
      const title = titleEl.value.trim();
      const text = bodyEl.value;
      const pinned = root.querySelector('#pinned').checked;
      const relevant = root.querySelector('#relevant').checked;
      const same = title === (state.orig.title || '').trim()
        && text === (state.orig.text || '')
        && pinned === Boolean(state.orig.pinned)
        && relevant === (state.orig.relevant !== false);
      if (same && !andLeave) return;
      if (same && andLeave && !state.note.dirty && !state.note.held) {
        const stay = openInEdit.has(String(state.note.id)) || await db.isOpenInEdit(state.note.id);
        if (stay) return;
        root._flushEdit = null;
        root._saveEdit = null;
        if (id === 'new') go('/');
        else go('/note/' + state.note.id);
        return;
      }
      const mode = await db.getSaveMode();
      const hold = Boolean(localOnly || (root._holdPush && !andLeave) || (mode === 'manual' && !andLeave));
      const stored = await sync.saveLocalEdit({
        id: state.note.id,
        title: title || 'Untitled',
        text,
        pinned,
        relevant,
        note_type: state.note.note_type || 0,
        v_hash: state.note.v_hash,
        base_hash: state.note.base_hash || state.note.v_hash
      }, { held: hold });
      state.note = stored;
      state.orig = { title: stored.title || '', text: stored.text || '', pinned: stored.pinned, relevant: stored.relevant !== false };
      root.dataset.noteId = String(stored.id);
      if (!hold && !db.isForceLocal() && online) {
        try {
          const { remap, conflicts } = await sync.pushDirty();
          const mine = (conflicts || []).filter((c) => String(c.fromId) === String(stored.id));
          if (mine.length) {
            toastConflicts(mine);
            if (mine[0].copy) {
              state.note = mine[0].copy;
              root.dataset.noteId = String(state.note.id);
            }
            if (andLeave) {
              root._flushEdit = null;
              root._saveEdit = null;
              go('/note/' + state.note.id);
            }
            return;
          }
          if (remap[stored.id]) {
            const next = remap[stored.id];
            if (String(stored.id) !== String(next.id) && parseHash().name === 'edit') {
              history.replaceState(null, '', '#/edit/' + next.id);
            }
            state.note = next;
          } else {
            const fresh = await db.getNote(stored.id);
            if (fresh) state.note = fresh;
          }
          state.note.base_hash = state.note.v_hash;
          root.dataset.noteId = String(state.note.id);
          await loadPrefs();
        } catch (e) {
          if (!(e instanceof api.NetworkError)) toast(e.message || 'Could not upload');
        }
      }
      if (!silent) toast(hold ? 'Saved on this device' : 'Saved');
      if (andLeave) {
        const stay = openInEdit.has(String(state.note.id)) || await db.isOpenInEdit(state.note.id);
        if (!stay) {
          root._flushEdit = null;
          root._saveEdit = null;
          go('/note/' + state.note.id);
        }
      }
    };
    const p = saveChain.then(job, job);
    saveChain = p.catch(() => {});
    return p;
  };
  const persistSoon = () => {
    clearTimeout(root._editTimer);
    root._editTimer = setTimeout(() => save(false, true), 800);
    paintStaleBanner();
  };
  root.querySelector('#body').addEventListener('input', persistSoon);
  root.querySelector('#title').addEventListener('input', persistSoon);
  root.querySelector('#pinned').addEventListener('change', persistSoon);
  root.querySelector('#relevant').addEventListener('change', persistSoon);
  root._flushEdit = (silent, localOnly) => save(false, silent, localOnly);
  root._saveEdit = () => {
    clearTimeout(root._editTimer);
    root._editTimer = null;
    return save(true);
  };
  startStaleWatch(state.note.id, 'edit', state.note.v_hash);
}

async function renderSettings() {
  const mode = await db.getSyncMode();
  const last = await db.getMeta('last_synced', 0);
  const lastStr = last ? new Date(last).toLocaleString() : 'never';
  const user = (await db.getMeta('username', '')) || '';
  const notes = await db.allNotes();
  const n = notes.length;
  const pending = notes.filter((x) => x.dirty).length;
  const ready = notesWithBody(notes);
  const searchLocal = await db.isSearchLocalOnly();
  const store = await storageInfo();
  const persistLabel = store.persistent
    ? 'Persistent — this browser should not auto-clear the cache'
    : 'Not persistent — the browser may clear the cache when storage is low';
  const body = `
    <div class="settings">
      <p class="muted">${esc(user)} · ${n} notes cached · ${ready} ready offline · ${pending} pending</p>
      <p class="muted">Last sync: ${esc(lastStr)}</p>
      <h2>This device</h2>
      <p class="muted">${esc(persistLabel)}</p>
      ${store.quota ? `<p class="muted">Storage used: ${esc(store.quota)}</p>` : ''}
      ${store.persistent ? '' : `<div class="row-actions"><button class="btn solid" data-act="request-persist">Keep data on this device</button></div>`}
      <h2>Saving</h2>
      <label><input type="radio" name="save-mode" value="auto" ${saveMode === 'auto' ? 'checked' : ''}>
        <span>Upload while typing<span class="hint">Writes locally as you type, then uploads. The button is Done.</span></span></label>
      <label><input type="radio" name="save-mode" value="manual" ${saveMode === 'manual' ? 'checked' : ''}>
        <span>Upload when I tap Save<span class="hint">Typing stays on this device until you Save or Sync now.</span></span></label>
      <h2>Notes cache</h2>
      <label><input type="radio" name="mode" value="local_some" ${mode === 'local_some' ? 'checked' : ''}>
        <span>Cache notes I open<span class="hint">Default. Offline you can reread what you already opened, and create new notes.</span></span></label>
      <label><input type="radio" name="mode" value="full_mirror" ${mode === 'full_mirror' ? 'checked' : ''}>
        <span>Keep a full copy<span class="hint">Download all notes and keep them in sync when you are online.</span></span></label>
      <label><input type="radio" name="mode" value="remote_only" ${mode === 'remote_only' ? 'checked' : ''}>
        <span>Do not store notes<span class="hint">Always fetch from the server. Offline reading will be empty except drafts.</span></span></label>
      <label><input type="checkbox" id="force-local" ${db.isForceLocal() ? 'checked' : ''}>
        <span>Use local copy only this session<span class="hint">Even if you are online, read/write the cache. Uploads wait until you turn this off.</span></span></label>
      <label><input type="checkbox" id="search-local" ${searchLocal ? 'checked' : ''}>
        <span>Search only locally<span class="hint">When off, search uses the server while you are online (3 or more characters).</span></span></label>
      <div class="row-actions">
        <button class="btn solid" data-act="sync-now">Sync now</button>
        <button class="btn ghost" data-act="download-all">Download all notes</button>
        <button class="btn ghost" data-act="clear-cache">Clear local notes</button>
      </div>
      <h2>Account</h2>
      <div class="row-actions">
        <a class="btn ghost" href="/">Full website</a>
        <button class="btn danger" data-act="logout">Sign out of app</button>
      </div>
    </div>
  `;
  root.innerHTML = shell('Settings', body, { back: true });
}

async function onAction(act, btn) {
  if (act === 'back') {
    history.length > 1 ? history.back() : go('/');
    return;
  }
  if (act === 'home') {
    go('/');
    return;
  }
  if (act === 'theme') {
    applyTheme(currentTheme() === 'dark' ? 'light' : 'dark');
    return;
  }
  if (act === 'settings') { go('/settings'); return; }
  if (act === 'clip-set') {
    await saveClipboardToServer();
    return;
  }
  if (act === 'clip-get') {
    await loadClipboardFromServer();
    return;
  }
  if (act === 'new') { go('/edit/new'); return; }
  if (act === 'view-all') { go('/all/0'); return; }
  if (act === 'page-prev' || act === 'page-next') {
    if (btn && btn.disabled) return;
    const page = parseInt(root.dataset.page || '0', 10) || 0;
    go('/all/' + (act === 'page-next' ? page + 1 : Math.max(0, page - 1)));
    return;
  }
  if (act === 'download-file') {
    if (!filesOnline()) {
      toast('Connect to download attachments');
      return;
    }
    const fileId = btn && btn.dataset.fileId;
    const fileName = (btn && btn.dataset.fileName) || 'download';
    if (!fileId) return;
    btn.disabled = true;
    try {
      toast('Downloading…');
      const { blob, filename } = await api.apiFetchBlob('/file/' + encodeURIComponent(fileId));
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = filename || fileName;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      toast(e.message || 'Download failed');
    } finally {
      btn.disabled = false;
    }
    return;
  }
  if (act === 'save' && root._saveEdit) { await root._saveEdit(); return; }
  if (act === 'edit-note') {
    go('/edit/' + root.dataset.noteId);
    return;
  }
  if (act === 'view-note') {
    if (root._flushEdit) {
      const manual = (await db.getSaveMode()) === 'manual';
      await root._flushEdit(true, manual || root._holdPush);
    }
    const id = (root._edit && root._edit.note && root._edit.note.id) || root.dataset.noteId;
    root._flushEdit = null;
    root._saveEdit = null;
    if (id) go('/note/' + id);
    return;
  }
  if (act === 'toggle-pin' || act === 'toggle-rel') {
    const id = coerceId(root.dataset.noteId);
    const note = await db.getNote(id) || await sync.cacheOpenedNote(id);
    if (act === 'toggle-pin') note.pinned = !note.pinned;
    if (act === 'toggle-rel') note.relevant = note.relevant === false;
    note.base_hash = note.v_hash;
    await sync.saveLocalEdit(note);
    if (online && !db.isForceLocal()) {
      try {
        const { conflicts } = await sync.pushDirty();
        toastConflicts(conflicts);
      } catch { /* queued */ }
    }
    await renderView(note.id);
    return;
  }
  if (act === 'sync-now') {
    try {
      toast('Syncing…');
      const r = await sync.runSync({ force: true, includeHeld: true });
      if (toastConflicts(r.conflicts)) { /* already told */ }
      else toast(r.skipped ? 'Skipped' : 'Synced');
    } catch (e) {
      toast(e.message || 'Sync failed');
    }
    await renderSettings();
    return;
  }
  if (act === 'download-all') {
    await db.setSyncMode('full_mirror');
    await db.setMeta('asked_full_download', true);
    downloadOffer = false;
    try {
      toast('Downloading…');
      const r = await sync.runSync({ full: true });
      if (!toastConflicts(r.conflicts)) toast((r.downloaded || 0) + ' notes updated');
    } catch (e) {
      toast(e.message || 'Download failed');
    }
    await route();
    return;
  }
  if (act === 'dismiss-download') {
    await db.setMeta('asked_full_download', true);
    downloadOffer = false;
    toast('You can download all notes later in Settings');
    await route();
    return;
  }
  if (act === 'request-persist') {
    const ok = await requestPersistentStorage();
    toast(ok ? 'This device will keep the app cache' : 'Browser declined; install the app and try again');
    await renderSettings();
    return;
  }
  if (act === 'clear-cache') {
    if (!confirm('Delete all cached notes on this device? Pending uploads will be lost.')) return;
    await db.clearNotes();
    toast('Cache cleared');
    await renderSettings();
    return;
  }
  if (act === 'logout') {
    await api.clearTokens();
    await db.clearNotes();
    go('/');
    renderLogin();
  }
}

root.addEventListener('click', (ev) => {
  const btn = ev.target.closest('[data-act]');
  if (!btn) return;
  ev.preventDefault();
  onAction(btn.dataset.act, btn);
});

root.addEventListener('change', async (ev) => {
  if (ev.target.name === 'mode') {
    await db.setSyncMode(ev.target.value);
    if (ev.target.value === 'full_mirror' || ev.target.value === 'remote_only') {
      await db.setMeta('asked_full_download', true);
      downloadOffer = false;
    }
    toast('Saved');
  }
  if (ev.target.name === 'save-mode') {
    await db.setSaveMode(ev.target.value);
    saveMode = ev.target.value === 'manual' ? 'manual' : 'auto';
    if (saveMode === 'auto') {
      await db.clearHeldFlags();
      toast('Will upload while typing');
      if (online && !db.isForceLocal()) {
        try { await sync.runSync({ includeHeld: true }); } catch { /* queued */ }
      }
    } else {
      toast('Will upload when you tap Save');
    }
  }
  if (ev.target.id === 'force-local') {
    db.setForceLocal(ev.target.checked);
    toast(ev.target.checked ? 'Local-only until you close the tab' : 'Will use the server again');
    await route();
  }
  if (ev.target.id === 'search-local') {
    await db.setSearchLocalOnly(ev.target.checked);
    toast(ev.target.checked ? 'Search uses the cache' : 'Search uses the server while online');
  }
  if (ev.target.id === 'open-in-edit') {
    const id = coerceId(root.dataset.noteId);
    if (id == null || id === 'new') return;
    await db.setOpenInEdit(id, ev.target.checked);
    await loadPrefs();
    toast(ev.target.checked ? 'Opens in editor from the list' : 'Opens in view from the list');
  }
});

async function refreshOnline({ reroute = false } = {}) {
  connecting = navigator.onLine && !db.isForceLocal();
  updateStatusBar();
  const reachable = navigator.onLine && !db.isForceLocal() && await api.ping();
  connecting = false;
  online = reachable;
  updateStatusBar();
  if (online && !db.isForceLocal()) {
    try {
      const r = await sync.runSync({ skipIds: skipEditIds() });
      toastConflicts(r.conflicts);
    } catch { /* stay quiet */ }
  }
  if (reroute) {
    const page = parseHash().name;
    if (page !== 'view' && page !== 'edit') await route();
  }
}

async function route() {
  applyTheme(currentTheme());
  if (root._editTimer) {
    clearTimeout(root._editTimer);
    root._editTimer = null;
  }
  if (root._flushEdit) {
    const flush = root._flushEdit;
    root._flushEdit = null;
    root._saveEdit = null;
    try {
      const manual = (await db.getSaveMode()) === 'manual';
      await flush(true, manual || root._holdPush);
    } catch { /* keep navigating */ }
  } else {
    root._saveEdit = null;
  }
  stopStaleWatch();
  closeClipModal();
  if (!(await requireAuth())) return;
  await loadPrefs();
  const r = parseHash();
  if (r.name === 'list' || r.name === 'all') await maybePrepareDownloadOffer();
  if (r.name === 'view') return renderView(r.id);
  if (r.name === 'edit') return renderEdit(r.id);
  if (r.name === 'settings') return renderSettings();
  if (r.name === 'all') return renderAll(r.page);
  await renderList();
}

window.addEventListener('hashchange', () => route());
window.addEventListener('online', async () => {
  await refreshOnline({ reroute: true });
});
window.addEventListener('offline', () => {
  connecting = false;
  online = false;
  stopStaleWatch();
  updateStatusBar();
  document.querySelectorAll('[data-act="download-file"], [data-act="clip-set"], [data-act="clip-get"]').forEach((el) => { el.disabled = true; });
});

async function onAppForeground() {
  if (Date.now() - lastFocusSync < 2000) return;
  lastFocusSync = Date.now();
  const page = parseHash().name;
  await refreshOnline({ reroute: page === 'list' || page === 'all' || page === 'settings' });
  if (staleWatchId) checkStale();
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') onAppForeground();
});
window.addEventListener('focus', () => onAppForeground());
window.addEventListener('pageshow', (ev) => {
  if (ev.persisted) onAppForeground();
});

registerServiceWorker();
applyTheme(currentTheme());
openDbAndStart();

async function openDbAndStart() {
  await db.openDb();
  online = false;
  connecting = true;
  requestPersistentStorage();
  await route();
  await refreshOnline({ reroute: true });
}
