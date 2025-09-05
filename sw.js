// sw.js - Service Worker Padronizado e Eficaz

self.addEventListener('install', event => {
  console.log('Service Worker: Instalando...');
  self.skipWaiting();
});

self.addEventListener('activate', event => {
  console.log('Service Worker: Ativando...');
  return self.clients.claim();
});

self.addEventListener('fetch', event => {
  // Apenas responde com a requisição da rede. Essencial para o PWA funcionar.
  event.respondWith(fetch(event.request));
});
