// NBA Daily - Service Worker
const CACHE_NAME = "nba-daily-v1";

self.addEventListener("install", (e) => {
    self.skipWaiting();
});

self.addEventListener("fetch", (e) => {
    e.respondWith(
        fetch(e.request).catch(() => caches.match(e.request))
    );
});
