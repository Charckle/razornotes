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
