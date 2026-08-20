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

function iconBtn(action, label, text) {
  return `<button class="icon-btn" data-act="${action}" aria-label="${esc(label)}">${text}</button>`;
}

function statusClass() {
  if (db.isForceLocal()) return 'local';
  if (sync.isSyncing()) return 'syncing';
  if (!online) return 'offline';
  return '';
}

function statusText() {
  if (db.isForceLocal()) return 'Local only (this session)';
  if (sync.isSyncing()) return 'Syncing…';
  if (!online) return 'Offline';
  return 'Online';
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
  const badges = [
    n.pinned ? '<span class="badge">Pinned</span>' : '',
    n.note_type === 1 ? '<span class="badge">Task</span>' : '',
    n.dirty ? '<span class="badge">Pending</span>' : ''
  ].join('');
  return `<a class="${cls.join(' ')}" href="#/note/${encodeURIComponent(n.id)}">
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
  const body = `
    <article class="note-view">
      <div class="row-actions">
        <button class="btn solid" data-act="edit-note">Edit</button>
        <button class="btn ghost" data-act="toggle-pin">${note.pinned ? 'Unpin' : 'Pin'}</button>
        <button class="btn ghost" data-act="toggle-rel">${note.relevant === false ? 'Show on home' : 'Hide from home'}</button>
      </div>
      <h2 class="title">${esc(note.title || 'Untitled')}</h2>
      <div class="note-meta">${esc(note.date_mod || '')}${note.dirty ? ' · pending sync' : ''}${db.isLocalId(note.id) ? ' · not uploaded yet' : ''}</div>
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
  const body = `
    <div class="edit-form">
      <input class="edit-title" id="title" placeholder="Title" value="${esc(note.title)}">
      <textarea class="edit-body" id="body" placeholder="Write…">${esc(note.text)}</textarea>
      <div class="row-actions">
        <button class="btn solid" data-act="save">Save</button>
        <label class="muted"><input type="checkbox" id="pinned" ${note.pinned ? 'checked' : ''}> Pinned</label>
        <label class="muted"><input type="checkbox" id="relevant" ${note.relevant !== false ? 'checked' : ''}> Show on home</label>
      </div>
    </div>
  `;
  root.innerHTML = shell(id === 'new' ? 'New note' : 'Edit', body, { back: true, mainClass: 'edit-screen' });
  const state = { note };
  root._edit = state;
  root._holdPush = false;
  const save = async (andLeave, silent, localOnly) => {
    const titleEl = root.querySelector('#title');
    const bodyEl = root.querySelector('#body');
    if (!titleEl || !bodyEl) return;
    const title = titleEl.value.trim() || 'Untitled';
    const text = bodyEl.value;
    const pinned = root.querySelector('#pinned').checked;
    const relevant = root.querySelector('#relevant').checked;
    const stored = await sync.saveLocalEdit({
      id: state.note.id,
      title,
      text,
      pinned,
      relevant,
      note_type: state.note.note_type || 0,
      v_hash: state.note.v_hash,
      base_hash: state.note.base_hash || state.note.v_hash
    });
    state.note = stored;
    if (!localOnly && root._holdPush && !andLeave) localOnly = true;
    if (!localOnly && !db.isForceLocal() && online) {
      try {
        const { remap, conflicts } = await sync.pushDirty();
        const mine = (conflicts || []).filter((c) => String(c.fromId) === String(stored.id));
        if (mine.length) {
          toastConflicts(mine);
          if (mine[0].copy) state.note = mine[0].copy;
          if (andLeave) go('/note/' + state.note.id);
          return;
        }
        if (remap[stored.id]) state.note = remap[stored.id];
        else {
          const fresh = await db.getNote(stored.id);
          if (fresh) state.note = fresh;
        }
      } catch (e) {
        if (!(e instanceof api.NetworkError)) toast(e.message || 'Could not upload');
      }
    }
    if (!silent) toast('Saved');
    if (andLeave) go('/note/' + state.note.id);
  };
  let t;
  root.querySelector('#body').addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => save(false), 800);
    paintStaleBanner();
  });
  root.querySelector('#title').addEventListener('input', () => {
    clearTimeout(t);
    t = setTimeout(() => save(false), 800);
    paintStaleBanner();
  });
  root._flushEdit = (silent, localOnly) => save(false, silent, localOnly);
  root._saveEdit = () => save(true);
  startStaleWatch(state.note.id, 'edit', state.note.v_hash);
}

async function renderSettings() {
  const mode = await db.getSyncMode();
  const last = await db.getMeta('last_synced', 0);
  const lastStr = last ? new Date(last).toLocaleString() : 'never';
  const user = (await db.getMeta('username', '')) || '';
  const n = (await db.allNotes()).length;
  const pending = (await db.allNotes()).filter((x) => x.dirty).length;
  const searchLocal = await db.isSearchLocalOnly();
  const body = `
    <div class="settings">
      <p class="muted">${esc(user)} · ${n} notes cached · ${pending} pending</p>
      <p class="muted">Last sync: ${esc(lastStr)}</p>
      <h2>On this device</h2>
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
      const r = await sync.runSync({ force: true });
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
    try {
      toast('Downloading…');
      const r = await sync.runSync({ full: true });
      if (!toastConflicts(r.conflicts)) toast((r.downloaded || 0) + ' notes updated');
    } catch (e) {
      toast(e.message || 'Download failed');
    }
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
    toast('Saved');
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
});

async function refreshOnline() {
  online = navigator.onLine && (db.isForceLocal() ? false : await api.ping());
  if (online && !db.isForceLocal()) {
    try {
      const r = await sync.runSync();
      toastConflicts(r.conflicts);
    } catch { /* stay quiet */ }
  }
}

async function route() {
  applyTheme(currentTheme());
  const r = parseHash();
  stopStaleWatch();
  if (!(await requireAuth())) return;
  if (r.name === 'view') return renderView(r.id);
  if (r.name === 'edit') return renderEdit(r.id);
  if (r.name === 'settings') return renderSettings();
  if (r.name === 'all') return renderAll(r.page);
  await renderList();
}

window.addEventListener('hashchange', () => route());
window.addEventListener('online', async () => {
  await refreshOnline();
  await route();
});
window.addEventListener('offline', () => {
  online = false;
  stopStaleWatch();
  const bar = document.querySelector('.status-bar');
  if (bar) {
    bar.className = 'status-bar offline';
    bar.lastElementChild.textContent = 'Offline';
  }
  document.querySelectorAll('[data-act="download-file"]').forEach((el) => { el.disabled = true; });
});

async function onAppForeground() {
  if (Date.now() - lastFocusSync < 2000) return;
  lastFocusSync = Date.now();
  if (online && !db.isForceLocal()) {
    try {
      const r = await sync.runSync();
      toastConflicts(r.conflicts);
    } catch { /* quiet */ }
  }
  if (staleWatchId) checkStale();
}

document.addEventListener('visibilitychange', () => {
  if (document.visibilityState === 'visible') onAppForeground();
});
window.addEventListener('focus', () => onAppForeground());

if ('serviceWorker' in navigator) {
  navigator.serviceWorker.register('/app/sw.js', { scope: '/app/' }).catch(() => {});
}

applyTheme(currentTheme());
openDbAndStart();

async function openDbAndStart() {
  await db.openDb();
  online = navigator.onLine;
  try {
    if (navigator.onLine && !db.isForceLocal()) online = await api.ping();
  } catch {
    online = false;
  }
  await route();
  if (online && !db.isForceLocal()) {
    try {
      const r = await sync.runSync();
      toastConflicts(r.conflicts);
      await route();
    } catch { /* first paint already done */ }
  }
}
