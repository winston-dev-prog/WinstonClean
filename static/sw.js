const CACHE_NAME = 'win-cache';
const PRECACHE_URLS = [
  '/', 
  '/index.html', 
  '/manifest.json',
  '/sw.js'
];

// při instalaci cache statiku
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => cache.addAll(PRECACHE_URLS))
      .then(() => self.skipWaiting())
  );
});

// aktivace bez současných cache
self.addEventListener('activate', event => {
  event.waitUntil(self.clients.claim());
});

// jen GET requests z cache, POSTy projdou skrz
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  // bypassuj všechno, co není GET, nebo je /chat
  if (event.request.method !== 'GET' || url.pathname === '/chat') {
    return;
  }
  event.respondWith(
    caches.match(event.request)
      .then(cached => cached || fetch(event.request))
  );
});
