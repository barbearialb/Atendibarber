// sw.js - Service Worker Padronizado e Eficaz
self.addEventListener('install', event => {
  self.skipWaiting();
});
self.addEventListener('activate', event => {
  return self.clients.claim();
});
self.addEventListener('fetch', event => {
  event.respondWith(fetch(event.request));
});
