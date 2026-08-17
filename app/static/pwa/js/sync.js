import * as db from './db.js';
import { apiFetch, ApiError, NetworkError } from './api.js';
import { previewText } from './markdown.js';

const DOWNLOAD_CONCURRENCY = 6;

let _syncing = false;

export function isSyncing() {
  return _syncing;
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
    pending: null
  };
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
  try {
    const hashRow = await apiFetch('/note/' + id + '/hash');
    const serverHash = hashRow.v_hash || '';
    if (local && local.v_hash && local.v_hash === serverHash && !local.dirty && local.text) {
      return local;
    }
    const remote = normalize(await apiFetch('/note/' + id));
    if (local && local.dirty && local.v_hash !== remote.v_hash) {
      return local;
    }
    if (mode !== 'remote_only') await db.saveNote(remote);
    return remote;
  } catch (e) {
    if (e instanceof NetworkError) {
      if (local && (local.text || local.dirty)) return local;
      throw new Error('Note not available offline.');
    }
    throw e;
  }
}

export async function saveLocalEdit(note) {
  const now = new Date().toISOString().slice(0, 19).replace('T', ' ');
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
    pending: db.isLocalId(note.id) ? 'create' : 'update',
    base_hash: note.base_hash || note.v_hash || ''
  };
  await db.saveNote(stored);
  return stored;
}

async function handleConflict(local, serverNote) {
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
    base_hash: ''
  };
  await db.saveNote(copy);
  const kept = normalize(serverNote);
  await db.saveNote(kept);
  return kept;
}

async function pushOne(note) {
  if (note.pending === 'create' || db.isLocalId(note.id)) {
    const created = await apiFetch('/notes', {
      method: 'POST',
      body: {
        note_title: note.title || 'Untitled',
        note_text: note.text || '',
        pinned: note.pinned,
        relevant: note.relevant,
        note_type: note.note_type || 0
      }
    });
    const saved = normalize(created);
    await db.deleteNote(note.id);
    await db.saveNote(saved);
    return saved;
  }
  try {
    const updated = await apiFetch('/note/' + note.id, {
      method: 'PUT',
      body: {
        note_title: note.title || 'Untitled',
        note_text: note.text || '',
        pinned: note.pinned,
        relevant: note.relevant,
        note_type: note.note_type || 0,
        v_hash: note.base_hash || note.v_hash || undefined
      }
    });
    const saved = normalize(updated);
    await db.saveNote(saved);
    return saved;
  } catch (e) {
    if (e instanceof ApiError && e.status === 409 && e.data && e.data.note) {
      return handleConflict(note, e.data.note);
    }
    throw e;
  }
}

export async function pushDirty() {
  const notes = (await db.allNotes()).filter((n) => n.dirty);
  const remap = {};
  for (const note of notes) {
    const saved = await pushOne(note);
    if (saved) remap[note.id] = saved;
  }
  return remap;
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
    const hashMatch = local && local.v_hash === item.v_hash && local.text;
    await db.saveNote({
      id,
      title: item.title || '',
      text: hashMatch ? local.text : (local && local.text) || '',
      preview: item.preview || '',
      pinned: Boolean(item.pinned),
      relevant: item.relevant !== false,
      date_mod: item.date_mod || '',
      v_hash: item.v_hash || '',
      active: true,
      note_type: item.note_type || 0,
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
    if (!local || local.v_hash !== row.v_hash || !local.text) {
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

export async function runSync({ full = false } = {}) {
  if (_syncing) return { skipped: true };
  if (db.isForceLocal()) return { skipped: true, reason: 'local' };
  _syncing = true;
  try {
    await pushDirty();
    const mode = await db.getSyncMode();
    if (full || mode === 'full_mirror') {
      const n = await hashDiffSync();
      await db.setMeta('last_synced', Date.now());
      return { downloaded: n };
    }
    if (mode === 'local_some') {
      await pullMeta();
      await db.setMeta('last_synced', Date.now());
      return { downloaded: 0 };
    }
    await db.setMeta('last_synced', Date.now());
    return { downloaded: 0 };
  } finally {
    _syncing = false;
  }
}

export function listPreview(note) {
  return previewText(note.preview || note.text, 100);
}
