/* Service worker minimale per WatchNext (PWA installabile + shell offline).
   - Navigazioni: network-first, con fallback alla shell quando si è offline. La shell in
     cache si aggiorna a ogni navigazione riuscita (prima restava quella dell'installazione).
   - /api/*: mai dalla cache, i dati devono essere freschi.
   - Asset statici (nomi con hash): cache-first. Si mettono in cache solo risposte OK, e a
     ogni nuova versione dell'app si buttano gli asset che l'index.html non usa più: prima
     ogni deploy lasciava nel browser i file della versione precedente, per sempre. */
const CACHE = 'watchnext-v2';
const SHELL = ['/', '/index.html', '/icon-192.png', '/icon-512.png', '/manifest.webmanifest'];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE).then((c) => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// Tiene in cache solo gli /assets/ citati dall'index.html appena scaricato.
async function pruneAssets(html) {
  const used = new Set(html.match(/\/assets\/[^"'\s)]+/g) || []);
  const cache = await caches.open(CACHE);
  const keys = await cache.keys();
  await Promise.all(
    keys
      .filter((req) => {
        const path = new URL(req.url).pathname;
        return path.startsWith('/assets/') && !used.has(path);
      })
      .map((req) => cache.delete(req))
  );
}

async function handleNavigate(request) {
  try {
    const res = await fetch(request);
    if (res.ok && (res.headers.get('content-type') || '').includes('text/html')) {
      const copy = res.clone();
      copy.text().then(async (html) => {
        const cache = await caches.open(CACHE);
        await cache.put('/index.html', new Response(html, { headers: { 'Content-Type': 'text/html' } }));
        await pruneAssets(html);
      }).catch(() => {});
    }
    return res;
  } catch {
    return (await caches.match('/index.html')) || Response.error();
  }
}

self.addEventListener('fetch', (e) => {
  const { request } = e;
  if (request.method !== 'GET') return;

  const url = new URL(request.url);
  if (url.origin !== self.location.origin) return; // solo same-origin
  if (url.pathname.startsWith('/api/')) return;     // API sempre dalla rete

  if (request.mode === 'navigate') {
    e.respondWith(handleNavigate(request));
    return;
  }

  e.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached;
      return fetch(request).then((res) => {
        if (res.ok) {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(request, copy));
        }
        return res;
      });
    })
  );
});
