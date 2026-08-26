const CACHE = 'razor-pwa-v10';
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

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE).then((cache) => cache.addAll(PRECACHE)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil((async () => {
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);
  if (event.request.method !== 'GET') return;
  if (url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/api/') || url.pathname === '/health') return;

  if (url.pathname.startsWith('/app/')) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE);
      if (url.pathname === '/app/sw.js') {
        try {
          return await fetch(event.request);
        } catch {
          return cache.match(event.request);
        }
      }
      const cached = await cache.match(event.request);
      const networked = fetch(event.request).then((res) => {
        if (res && res.ok) cache.put(event.request, res.clone());
        return res;
      }).catch(() => null);
      if (cached) {
        networked.catch(() => {});
        return cached;
      }
      const fresh = await networked;
      if (fresh) return fresh;
      if (url.pathname.startsWith('/app/assets/')) {
        return new Response('Offline', { status: 503 });
      }
      return (await cache.match('/app/')) || new Response('Offline', { status: 503 });
    })());
  }
});
