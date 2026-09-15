const SHELL = 'razor-pwa-shell';
const NEXT = 'razor-pwa-shell-next';
const PRECACHE = [
  '/app/',
  '/app/assets/css/app.css',
  '/app/assets/js/app.js',
  '/app/assets/js/api.js',
  '/app/assets/js/db.js',
  '/app/assets/js/sync.js',
  '/app/assets/js/markdown.js',
  '/app/icon.ico',
  '/app/manifest.webmanifest'
];

const FALLBACK_HTML = `<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Razor Notes</title>
  <style>
    body { font-family: system-ui, sans-serif; margin: 0; min-height: 100vh;
      display: flex; align-items: center; justify-content: center;
      background: #fff8d6; color: #1a1a1a; padding: 1.5rem; }
    main { max-width: 26rem; }
    h1 { font-size: 1.2rem; margin: 0 0 .6rem; }
    p { line-height: 1.45; color: #5c5744; }
    button { font: inherit; padding: .5rem .9rem; border: 0; border-radius: 8px;
      background: #212529; color: #fff; cursor: pointer; }
  </style>
</head>
<body>
  <main>
    <h1>Offline cache missing</h1>
    <p>This app needs a connection once to restore itself. Your notes on the server are safe. Connect, then reload.</p>
    <button type="button" onclick="location.reload()">Retry</button>
  </main>
</body>
</html>`;

function fallbackResponse() {
  return new Response(FALLBACK_HTML, {
    status: 200,
    headers: { 'Content-Type': 'text/html; charset=utf-8', 'Cache-Control': 'no-store' }
  });
}

async function putOk(cache, url) {
  try {
    const res = await fetch(url, { cache: 'reload', credentials: 'same-origin' });
    if (res && res.ok) {
      await cache.put(url, res.clone());
      return true;
    }
  } catch { /* keep whatever we already have */ }
  return false;
}

async function copyMissing(fromName, toCache) {
  const src = await caches.open(fromName);
  const keys = await src.keys();
  await Promise.all(keys.map(async (req) => {
    const already = await toCache.match(req, { ignoreSearch: true });
    if (already) return;
    const res = await src.match(req);
    if (res) await toCache.put(req, res);
  }));
}

async function copyAll(fromName, toCache) {
  try {
    const src = await caches.open(fromName);
    const keys = await src.keys();
    await Promise.all(keys.map(async (req) => {
      const res = await src.match(req);
      if (res) await toCache.put(req, res);
    }));
  } catch { /* source cache may not exist */ }
}

self.addEventListener('install', (event) => {
  event.waitUntil((async () => {
    const next = await caches.open(NEXT);
    await Promise.all(PRECACHE.map((url) => putOk(next, url)));
    const names = await caches.keys();
    if (names.includes(SHELL)) await copyMissing(SHELL, next);
    for (const name of names) {
      if (name === SHELL || name === NEXT) continue;
      if (!name.startsWith('razor-pwa')) continue;
      await copyMissing(name, next);
    }
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const shell = await caches.open(SHELL);
    const names = await caches.keys();
    if (names.includes(NEXT)) await copyAll(NEXT, shell);
    for (const name of names) {
      if (name === SHELL || name === NEXT) continue;
      if (!name.startsWith('razor-pwa')) continue;
      await copyMissing(name, shell);
      await caches.delete(name);
    }
    await caches.delete(NEXT);
    await self.clients.claim();
  })());
});

async function matchShell(cache) {
  return (await cache.match('/app/', { ignoreSearch: true }))
    || (await cache.match('/app', { ignoreSearch: true }));
}

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/') || url.pathname === '/health') return;

  if (url.pathname !== '/app' && !url.pathname.startsWith('/app/')) return;

  event.respondWith((async () => {
    const cache = await caches.open(SHELL);
    if (url.pathname === '/app/sw.js') {
      try {
        return await fetch(event.request);
      } catch {
        return (await cache.match(event.request)) || fallbackResponse();
      }
    }

    const cached = await cache.match(event.request, { ignoreSearch: true });
    const networked = fetch(event.request).then((res) => {
      if (res && res.ok && (res.type === 'basic' || res.type === 'cors')) {
        cache.put(event.request, res.clone());
      }
      return res;
    }).catch(() => null);

    if (cached) {
      networked.catch(() => {});
      return cached;
    }

    const fresh = await networked;
    if (fresh) return fresh;

    const navigate = event.request.mode === 'navigate'
      || url.pathname === '/app' || url.pathname === '/app/'
      || !url.pathname.startsWith('/app/assets/');
    if (navigate) {
      const shell = await matchShell(cache);
      if (shell) return shell;
      return fallbackResponse();
    }
    return new Response('Offline', { status: 503, statusText: 'Offline' });
  })());
});
