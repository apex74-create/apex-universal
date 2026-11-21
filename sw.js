// Apex Universal - storefront service worker (scope: /)
// Network-first for pages, cache-first for icons: the store shell opens offline.
const CACHE = 'apex-universal-store-v1';
self.addEventListener('install', e => { self.skipWaiting(); });
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(
    keys.filter(k => k.startsWith('apex-universal-store-') && k !== CACHE).map(k => caches.delete(k))
  )).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);
  if (e.request.method !== 'GET' || url.origin !== self.location.origin) return;
  if (url.pathname.startsWith('/faces/')) return; // the faces worker owns that scope
  e.respondWith(
    fetch(e.request).then(res => {
      if (res && res.ok) { const c = res.clone(); caches.open(CACHE).then(cache => cache.put(e.request, c)); }
      return res;
    }).catch(() => caches.open(CACHE).then(cache => cache.match(e.request)))
  );
});
