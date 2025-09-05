// sw.js - Service Worker Básico e Robusto
self.addEventListener('install', event => {
  console.log('Service Worker: Instalando...');
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  console.log('Service Worker: Ativando...');
  return self.clients.claim();
});

self.addEventListener('fetch', event => {
  event.respondWith(fetch(event.request));
});
