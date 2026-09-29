import * as db from './db.js';
import { apiFetch, ApiError, NetworkError, WRITE_MS } from './api.js';
import { previewText } from './markdown.js';

const DOWNLOAD_CONCURRENCY = 6;
export const FULL_SYNC_MS = 180000;
export const STALE_POLL_MS = 30000;

// Fields a client can change. A push only sends the ones it actually touched,
// so a pin toggle can never overwrite a body it does not have.
const EDIT_FIELDS = ['title', 'text', 'pinned', 'relevant', 'note_type'];
const MAX_SENT_OPS = 6;

let _syncing = false;
let _pushChain = Promise.resolve();

export function isSyncing() {
  return _syncing;
}

// Web Locks serialise across every tab and installed window on this origin.
// Without it two copies of the app push the same note and the loser gets a
// conflict it had no way to avoid. Not reentrant: never nest two of these.
function withSyncLock(fn) {
  if (navigator.locks && navigator.locks.request) {
    return navigator.locks.request('rn-sync', fn);
  }
  const p = _pushChain.then(fn, fn);
  _pushChain = p.catch(() => {});
  return p;
}

function normalize(note) {
  const id = note._id ?? note.id;
  return {
    id,
    title: note.title || '',
    text: note.text || '',
    pinned: Boolean(note.pinned),
    relevant: note.relevant !== false,
    date_mod: note.date_mod || '',
    v_hash: note.v_hash || '',
    active: note.active !== false,
    note_type: note.note_type || 0,
    dirty: false,
    pending: null,
    body_missing: false
  };
}

function editedFields(note) {
  return (Array.isArray(note.dirty_fields) && note.dirty_fields.length)
    ? note.dirty_fields
    : EDIT_FIELDS;
}

// The server trims titles and stores LF line endings, so compare the same way.
function comparable(note) {
  return [
    (note.title || '').trim(),
    (note.text || '').replace(/\r\n/g, '\n').replace(/\r/g, '\n'),
    String(Boolean(note.pinned)),
    String(note.relevant !== false),
    String(note.note_type || 0)
  ].join('\u001f');
}

// What the note would look like on the server once our edited fields land.
function applyEdits(serverNote, note) {
  const fields = editedFields(note);
  const merged = Object.assign({}, serverNote);
  if (fields.includes('title')) merged.title = note.title || 'Untitled';
  if (fields.includes('text') && !note.body_missing) merged.text = note.text || '';
  if (fields.includes('pinned')) merged.pinned = Boolean(note.pinned);
  if (fields.includes('relevant')) merged.relevant = note.relevant !== false;
  if (fields.includes('note_type')) merged.note_type = note.note_type || 0;
  return merged;
}

function updateBody(note) {
  const fields = editedFields(note);
  const body = {};
  if (fields.includes('title')) body.note_title = note.title || 'Untitled';
  // Never send a body we do not have: a metadata-only record would wipe it.
  if (fields.includes('text') && !note.body_missing) body.note_text = note.text || '';
  if (fields.includes('pinned')) body.pinned = note.pinned;
  if (fields.includes('relevant')) body.relevant = note.relevant;
  if (fields.includes('note_type')) body.note_type = note.note_type || 0;
  return body;
}

async function mapPool(items, limit, fn) {
  let i = 0;
  async function worker() {
    while (i < items.length) {
      const idx = i++;
      await fn(items[idx]);
    }
  }
  const n = Math.min(limit, items.length) || 0;
  await Promise.all(Array.from({ length: n }, worker));
}

export async function cacheOpenedNote(id) {
  if (db.isLocalId(id)) return db.getNote(id);
  const mode = await db.getSyncMode();
  if (mode === 'remote_only' && !db.isForceLocal()) {
    try {
      const remote = await apiFetch('/note/' + id);
      return normalize(remote);
    } catch (e) {
      if (e instanceof NetworkError) {
        const fallback = await db.getNote(id);
        if (fallback && (fallback.text || fallback.dirty)) return fallback;
        throw new Error('Note not available offline.');
      }
      throw e;
    }
  }
  const local = await db.getNote(id);
  if (db.isForceLocal()) {
    if (local && (local.text || local.dirty || db.isLocalId(id))) return local;
    throw new Error('Note not available offline.');
  }
  if (local && local.dirty) return local;
  const usableLocal = Boolean(local && (local.text || local.dirty));
  if (!navigator.onLine && usableLocal) return local;
  try {
    const hashRow = await apiFetch('/note/' + id + '/hash', { timeoutMs: 2500 });
    const serverHash = hashRow.v_hash || '';
    const localFresh = local && local.v_hash && local.v_hash === serverHash
      && local.text && !local.body_missing;
    if (localFresh) {
      return local;
    }
    const remote = normalize(await apiFetch('/note/' + id));
    if (mode !== 'remote_only') await db.saveNote(remote);
    return remote;
  } catch (e) {
    if (e instanceof NetworkError) {
      if (usableLocal) return local;
      throw new Error('Note not available offline.');
    }
    throw e;
  }
}

export async function saveLocalEdit(note, { held = false, fields = null } = {}) {
  const now = new Date().toISOString().slice(0, 19).replace('T', ' ');
  const prev = await db.getNote(note.id);
  const wasDirty = Boolean(prev && prev.dirty);

  // Accumulate across saves: two quick edits to different fields must both ship.
  const changed = new Set(fields || EDIT_FIELDS);
  if (wasDirty && Array.isArray(prev.dirty_fields)) {
    prev.dirty_fields.forEach((f) => changed.add(f));
  }

  const isNew = db.isLocalId(note.id);
  const stored = {
    id: note.id,
    title: note.title,
    text: note.text,
    pinned: Boolean(note.pinned),
    relevant: note.relevant !== false,
    date_mod: now,
    v_hash: note.v_hash || '',
    active: true,
    note_type: note.note_type || 0,
    dirty: true,
    held: Boolean(held),
    pending: isNew ? 'create' : 'update',
    // The base is the server state this edit started from; once dirty it must
    // not move, or a later push would claim to be based on its own output.
    base_hash: (wasDirty ? prev.base_hash : null) || note.base_hash || note.v_hash || '',
    body_missing: Boolean(prev && prev.body_missing && !changed.has('text')),
    dirty_fields: Array.from(changed),
    // A new op id per local change; retries of the same change reuse it.
    op_id: db.newOpId(),
    sent_ops: (prev && prev.sent_ops) || [],
    client_uuid: (prev && prev.client_uuid) || (isNew ? db.newClientUuid() : null),
    sync_blocked: null
  };
  await db.saveNote(stored);
  return stored;
}

export async function handleConflict(local, serverNote) {
  const copy = {
    id: db.newLocalId(),
    title: 'Conflict: ' + (local.title || 'Untitled'),
    text: local.text || '',
    pinned: false,
    relevant: true,
    date_mod: new Date().toISOString().slice(0, 19).replace('T', ' '),
    v_hash: '',
    active: true,
    note_type: local.note_type || 0,
    dirty: true,
    pending: 'create',
    base_hash: '',
    body_missing: false,
    dirty_fields: EDIT_FIELDS.slice(),
    op_id: db.newOpId(),
    sent_ops: [],
    client_uuid: db.newClientUuid(),
    sync_blocked: null
  };
  await db.saveNote(copy);
  const kept = normalize(serverNote);
  await db.saveNote(kept);
  return { note: kept, conflict: true, conflictTitle: copy.title, copy, fromId: local.id };
}

// Persist the op id before the request goes out, so a reload mid-flight can
// still tell that the server state came from us.
async function rememberSentOp(note, opId) {
  const fresh = (await db.getNote(note.id)) || note;
  const ops = (Array.isArray(fresh.sent_ops) ? fresh.sent_ops : [])
    .filter((x) => x !== opId)
    .concat(opId)
    .slice(-MAX_SENT_OPS);
  await db.saveNote(Object.assign({}, fresh, { sent_ops: ops }));
  return ops;
}

// Another window can edit the note while our request is in flight. Write the
// server's answer back without throwing that edit away.
async function adoptUpdate(pushed, saved) {
  const fresh = await db.getNote(pushed.id);
  if (fresh && fresh.dirty && fresh.op_id && fresh.op_id !== pushed.op_id) {
    const rebased = Object.assign({}, fresh, { v_hash: saved.v_hash, base_hash: saved.v_hash });
    await db.saveNote(rebased);
    return rebased;
  }
  await db.saveNote(saved);
  return saved;
}

async function adoptCreate(pushed, saved) {
  const fresh = await db.getNote(pushed.id);
  await db.deleteNote(pushed.id);
  if (fresh && fresh.dirty && fresh.op_id && fresh.op_id !== pushed.op_id) {
    const carried = Object.assign({}, fresh, {
      id: saved.id,
      pending: 'update',
      v_hash: saved.v_hash,
      base_hash: saved.v_hash,
      client_uuid: null,
      sent_ops: []
    });
    await db.saveNote(carried);
    return carried;
  }
  await db.saveNote(saved);
  return saved;
}

async function pushCreate(note) {
  let current = note;
  if (!current.client_uuid) {
    current = Object.assign({}, note, { client_uuid: db.newClientUuid() });
    await db.saveNote(current);
  }
  const created = await apiFetch('/notes', {
    method: 'POST',
    timeoutMs: WRITE_MS,
    body: {
      note_title: current.title || 'Untitled',
      note_text: current.text || '',
      pinned: current.pinned,
      relevant: current.relevant,
      note_type: current.note_type || 0,
      client_uuid: current.client_uuid
    }
  });
  return { note: await adoptCreate(current, normalize(created)) };
}

async function pushUpdate(note) {
  const opId = note.op_id || db.newOpId();
  const sentOps = await rememberSentOp(note, opId);
  const baseHash = note.base_hash || note.v_hash || '';
  const body = Object.assign(updateBody(note), { op_id: opId });
  if (baseHash) body.v_hash = baseHash;

  let saved;
  try {
    saved = normalize(await apiFetch('/note/' + note.id, {
      method: 'PUT', body, timeoutMs: WRITE_MS
    }));
  } catch (e) {
    if (!(e instanceof ApiError) || e.status !== 409) throw e;
    const serverRaw = e.data && e.data.note;
    if (!serverRaw || (serverRaw.id == null && serverRaw._id == null)) throw e;
    const server = normalize(serverRaw);

    // Our change is already there: an earlier attempt landed and only its
    // response was lost. Nothing to merge, nothing to warn about.
    if (comparable(server) === comparable(applyEdits(server, note))) {
      return { note: await adoptUpdate(note, server) };
    }

    // The server version is our own earlier write, so there is no other
    // author to conflict with. Rebase onto it and apply the change.
    if (serverRaw.op_id && sentOps.includes(serverRaw.op_id)) {
      const rebased = Object.assign(updateBody(note), { op_id: opId, v_hash: server.v_hash });
      saved = normalize(await apiFetch('/note/' + note.id, {
        method: 'PUT', body: rebased, timeoutMs: WRITE_MS
      }));
      return { note: await adoptUpdate(note, saved) };
    }

    return handleConflict(note, serverRaw);
  }
  return { note: await adoptUpdate(note, saved) };
}

function pushOne(note) {
  if (note.pending === 'create' || db.isLocalId(note.id)) return pushCreate(note);
  return pushUpdate(note);
}

// Park a note the server refuses, so one bad record cannot hold up every
// other pending upload. Editing it again, or an explicit sync, clears this.
async function blockNote(note, err) {
  const fresh = (await db.getNote(note.id)) || note;
  await db.saveNote(Object.assign({}, fresh, {
    sync_blocked: {
      status: (err && err.status) || 0,
      message: (err && err.message) || 'Upload rejected',
      at: Date.now()
    }
  }));
}

export async function clearSyncBlocks() {
  const notes = await db.allNotes();
  for (const n of notes) {
    if (!n.sync_blocked) continue;
    await db.saveNote(Object.assign({}, n, { sync_blocked: null }));
  }
}

async function pushDirtyInner({ includeHeld = false, skipIds = [] } = {}) {
  const skip = new Set((skipIds || []).map((id) => String(id)));
  const notes = (await db.allNotes()).filter((n) => n.dirty && (includeHeld || !n.held)
    && !skip.has(String(n.id)) && !n.sync_blocked);
  const remap = {};
  const conflicts = [];
  const blocked = [];
  let stopped = null;

  for (const note of notes) {
    let result = null;
    try {
      result = await pushOne(note);
    } catch (e) {
      if (e instanceof NetworkError) { stopped = 'offline'; break; }
      const status = (e instanceof ApiError) ? e.status : 0;
      if (status === 401 || status === 422) { stopped = 'auth'; break; }
      if (status >= 400 && status < 500) {
        await blockNote(note, e);
        blocked.push({ id: note.id, title: note.title || 'Untitled', message: e.message });
        continue;
      }
      // Server-side trouble is usually temporary: stay dirty, retry next run.
      continue;
    }
    if (result && result.note) {
      remap[note.id] = result.note;
      if (String(note.id) !== String(result.note.id)) {
        await db.remapOpenInEdit(note.id, result.note.id);
      }
    }
    if (result && result.conflict) conflicts.push(result);
  }
  return { remap, conflicts, blocked, stopped };
}

export function pushDirty(opts = {}) {
  return withSyncLock(() => pushDirtyInner(opts));
}

export async function pullMeta() {
  const meta = await apiFetch('/notes/meta');
  const existing = await db.allNotes();
  const byId = new Map(existing.map((n) => [String(n.id), n]));
  const serverIds = new Set();
  for (const item of meta) {
    const id = item._id ?? item.id;
    serverIds.add(String(id));
    const local = byId.get(String(id));
    if (local && local.dirty) continue;
    const hashMatch = local && local.v_hash === item.v_hash && local.text && !local.body_missing;
    await db.saveNote({
      id,
      title: item.title || '',
      text: hashMatch ? local.text : (local && local.text) || '',
      preview: item.preview || '',
      pinned: Boolean(item.pinned),
      relevant: item.relevant !== false,
      date_mod: item.date_mod || '',
      v_hash: hashMatch ? (item.v_hash || '') : ((local && local.v_hash) || ''),
      active: true,
      note_type: item.note_type || 0,
      todo: item.todo || null,
      dirty: false,
      pending: null,
      body_missing: !hashMatch
    });
  }
  for (const local of existing) {
    if (local.dirty || db.isLocalId(local.id)) continue;
    if (!serverIds.has(String(local.id))) await db.deleteNote(local.id);
  }
  return meta;
}

export async function downloadMissingBodies() {
  const notes = await db.allNotes();
  const need = notes.filter((n) => !db.isLocalId(n.id) && !n.dirty && (!n.text || n.body_missing));
  await mapPool(need, DOWNLOAD_CONCURRENCY, async (n) => {
    const remote = normalize(await apiFetch('/note/' + n.id));
    await db.saveNote(remote);
  });
  return need.length;
}

export async function hashDiffSync() {
  const hashes = await apiFetch('/notes/hashes');
  const existing = await db.allNotes();
  const byId = new Map(existing.map((n) => [String(n.id), n]));
  const toFetch = [];
  for (const row of hashes) {
    if (row.active === false) {
      const local = byId.get(String(row.id));
      if (local && !local.dirty) await db.deleteNote(row.id);
      continue;
    }
    const local = byId.get(String(row.id));
    if (local && local.dirty) continue;
    if (!local || local.body_missing || local.v_hash !== row.v_hash || !local.text) {
      toFetch.push(row.id);
    }
  }
  const activeIds = new Set(hashes.filter((h) => h.active !== false).map((h) => String(h.id)));
  for (const local of existing) {
    if (local.dirty || db.isLocalId(local.id)) continue;
    if (!activeIds.has(String(local.id))) await db.deleteNote(local.id);
  }
  await mapPool(toFetch, DOWNLOAD_CONCURRENCY, async (id) => {
    const remote = normalize(await apiFetch('/note/' + id));
    await db.saveNote(remote);
  });
  return toFetch.length;
}

export async function serverHash(id) {
  const row = await apiFetch('/note/' + id + '/hash');
  return row.v_hash || '';
}

export async function fetchNote(id) {
  const remote = normalize(await apiFetch('/note/' + id));
  await db.saveNote(remote);
  return remote;
}

export async function takeServerVersion(id) {
  const local = await db.getNote(id);
  const remote = normalize(await apiFetch('/note/' + id));
  if (local && local.dirty) {
    return handleConflict(local, remote);
  }
  await db.saveNote(remote);
  return { note: remote };
}

export async function runSync({ full = false, force = false, includeHeld = false, skipIds = [] } = {}) {
  if (_syncing) return { skipped: true, conflicts: [], blocked: [] };
  if (db.isForceLocal()) return { skipped: true, reason: 'local', conflicts: [], blocked: [] };
  _syncing = true;
  try {
    if (force) await clearSyncBlocks();
    // Only the push is locked. Downloading can take a while and holding the
    // lock across it would stall a save the user is waiting on.
    const { conflicts, blocked, stopped } = await pushDirty({ includeHeld, skipIds });
    if (stopped) return { skipped: true, reason: stopped, conflicts, blocked, downloaded: 0 };

    const mode = await db.getSyncMode();
    if (full || mode === 'full_mirror') {
      if (!full && !force && mode === 'full_mirror') {
        const last = (await db.getMeta('last_full_sync', 0)) || 0;
        if (Date.now() - last < FULL_SYNC_MS) {
          return { skipped: true, reason: 'recent', conflicts, blocked, downloaded: 0 };
        }
      }
      const n = await hashDiffSync();
      await db.setMeta('last_synced', Date.now());
      await db.setMeta('last_full_sync', Date.now());
      return { downloaded: n, conflicts, blocked };
    }
    if (mode === 'local_some') {
      await pullMeta();
      await db.setMeta('last_synced', Date.now());
      return { downloaded: 0, conflicts, blocked };
    }
    await db.setMeta('last_synced', Date.now());
    return { downloaded: 0, conflicts, blocked };
  } finally {
    _syncing = false;
  }
}

export function listPreview(note) {
  return previewText(note.preview || note.text, 100);
}
