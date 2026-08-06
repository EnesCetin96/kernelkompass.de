const CACHE_NAME = "kernelkompass-linux-v12";
const ASSETS = [
  "./",
  "./index.html",
  "./impressum.html",
  "./verify-email.html",
  "./reset-password.html",
  "./manifest.json",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/apple-touch-icon.png",
  "./exam-data-mc-p0.js",
  "./exam-data-mc-p1-p4.js",
  "./exam-data-mc-p5-p9.js",
  "./exam-data-mc-app.js",
  "./exam-data-scenarios.js",
  "./sections/p0.html",
  "./sections/p1.html",
  "./sections/p2.html",
  "./sections/p3.html",
  "./sections/p4.html",
  "./sections/p5.html",
  "./sections/p6.html",
  "./sections/p7.html",
  "./sections/p8.html",
  "./sections/p9.html",
  "./sections/app.html",
  "./sections/ex.html",
  "./sections/exam.html"
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((keys) =>
      Promise.all(keys.filter((k) => k !== CACHE_NAME).map((k) => caches.delete(k)))
    )
  );
  self.clients.claim();
});

// Cache-first for our own files, network-first fallback for anything else (e.g. Google Fonts).
// For same-origin requests, if something isn't already in the ASSETS list above (e.g. a file
// added after this service worker version was last bumped), we still fetch it from the network
// and store it in the cache for next time — this used to only apply to cross-origin requests,
// which meant any same-origin file missing from ASSETS was NEVER cached and broke offline use.
self.addEventListener("fetch", (event) => {
  const url = new URL(event.request.url);
  if (url.origin === self.location.origin) {
    event.respondWith(
      caches.match(event.request).then((cached) => {
        if (cached) return cached;
        return fetch(event.request).then((res) => {
          const resClone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, resClone));
          return res;
        });
      })
    );
  } else {
    event.respondWith(
      fetch(event.request)
        .then((res) => {
          const resClone = res.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, resClone));
          return res;
        })
        .catch(() => caches.match(event.request))
    );
  }
});
