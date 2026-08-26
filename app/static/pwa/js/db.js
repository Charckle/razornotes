const DB_NAME = 'razor-pwa';
const DB_VER = 1;

let _db = null;

function idbReq(req) {
  return new Promise((resolve, reject) => {
    req.onsuccess = () => resolve(req.result);
    req.onerror = () => reject(req.error);
  });
}

export function openDb() {
  if (_db) return Promise.resolve(_db);
  return new Promise((resolve, reject) => {
    const req = indexedDB.open(DB_NAME, DB_VER);
    req.onupgradeneeded = () => {
      const db = req.result;
      if (!db.objectStoreNames.contains('meta')) db.createObjectStore('meta');
      if (!db.objectStoreNames.contains('notes')) db.createObjectStore('notes', { keyPath: 'id' });
      if (!db.objectStoreNames.contains('queue')) {
        db.createObjectStore('queue', { keyPath: 'qid', autoIncrement: true });
      }
    };
    req.onsuccess = () => {
      _db = req.result;
      _db.onversionchange = () => { _db.close(); _db = null; };
      resolve(_db);
    };
    req.onerror = () => reject(req.error);
  });
}

export async function getMeta(key, fallback = null) {
  const db = await openDb();
  const val = await idbReq(db.transaction('meta').objectStore('meta').get(key));
  return val === undefined ? fallback : val;
}

export async function setMeta(key, value) {
  const db = await openDb();
  const tx = db.transaction('meta', 'readwrite');
  tx.objectStore('meta').put(value, key);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function deleteMeta(key) {
  const db = await openDb();
  const tx = db.transaction('meta', 'readwrite');
  tx.objectStore('meta').delete(key);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function getNote(id) {
  const db = await openDb();
  return idbReq(db.transaction('notes').objectStore('notes').get(id));
}

export async function saveNote(note) {
  const db = await openDb();
  const tx = db.transaction('notes', 'readwrite');
  tx.objectStore('notes').put(note);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function deleteNote(id) {
  const db = await openDb();
  const tx = db.transaction('notes', 'readwrite');
  tx.objectStore('notes').delete(id);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function allNotes() {
  const db = await openDb();
  const rows = await idbReq(db.transaction('notes').objectStore('notes').getAll());
  return rows || [];
}

export async function enqueue(item) {
  const db = await openDb();
  const tx = db.transaction('queue', 'readwrite');
  tx.objectStore('queue').add(item);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function allQueue() {
  const db = await openDb();
  return (await idbReq(db.transaction('queue').objectStore('queue').getAll())) || [];
}

export async function deleteQueueItem(qid) {
  const db = await openDb();
  const tx = db.transaction('queue', 'readwrite');
  tx.objectStore('queue').delete(qid);
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function clearNotes() {
  const db = await openDb();
  const tx = db.transaction('notes', 'readwrite');
  tx.objectStore('notes').clear();
  return new Promise((resolve, reject) => {
    tx.oncomplete = () => resolve();
    tx.onerror = () => reject(tx.error);
  });
}

export async function pendingCount() {
  const q = await allQueue();
  const notes = await allNotes();
  const dirty = notes.filter((n) => n.dirty).length;
  return q.length + dirty;
}

export function isLocalId(id) {
  return typeof id === 'string' && id.startsWith('l');
}

export function newLocalId() {
  return 'l' + Date.now().toString(36) + Math.random().toString(36).slice(2, 8);
}

export async function getSyncMode() {
  return (await getMeta('sync_mode', 'local_some')) || 'local_some';
}

export async function setSyncMode(mode) {
  await setMeta('sync_mode', mode);
}

export function isForceLocal() {
  return sessionStorage.getItem('rn-force-local') === '1';
}

export function setForceLocal(on) {
  if (on) sessionStorage.setItem('rn-force-local', '1');
  else sessionStorage.removeItem('rn-force-local');
}

export async function isSearchLocalOnly() {
  return Boolean(await getMeta('search_local_only', false));
}

export async function setSearchLocalOnly(on) {
  await setMeta('search_local_only', Boolean(on));
}

export async function getSaveMode() {
  const m = await getMeta('save_mode', 'auto');
  return m === 'manual' ? 'manual' : 'auto';
}

export async function setSaveMode(mode) {
  await setMeta('save_mode', mode === 'manual' ? 'manual' : 'auto');
}

async function openInEditMap() {
  return Object.assign({}, (await getMeta('open_in_edit', {})) || {});
}

export async function openInEditIds() {
  const map = await openInEditMap();
  return new Set(Object.keys(map).filter((k) => map[k]));
}

export async function isOpenInEdit(id) {
  if (id == null || id === 'new') return false;
  const map = await openInEditMap();
  return Boolean(map[String(id)]);
}

export async function setOpenInEdit(id, on) {
  if (id == null || id === 'new') return;
  const map = await openInEditMap();
  const key = String(id);
  if (on) map[key] = true;
  else delete map[key];
  await setMeta('open_in_edit', map);
}

export async function remapOpenInEdit(fromId, toId) {
  if (fromId == null || toId == null) return;
  const map = await openInEditMap();
  const from = String(fromId);
  const to = String(toId);
  if (!map[from]) return;
  delete map[from];
  if (to && to !== 'new') map[to] = true;
  await setMeta('open_in_edit', map);
}

export async function clearHeldFlags() {
  const notes = await allNotes();
  for (const n of notes) {
    if (!n.held) continue;
    n.held = false;
    await saveNote(n);
  }
}
