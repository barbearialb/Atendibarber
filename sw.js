// sw.js - Service Worker Simples e Eficaz

/**
 * Evento de Instalação:
 * Disparado quando o Service Worker é instalado.
 * self.skipWaiting() força o novo service worker a se ativar imediatamente.
 */
self.addEventListener('install', event => {
  console.log('Service Worker: Instalando...');
  self.skipWaiting();
});

/**
 * Evento de Ativação:
 * Disparado quando o Service Worker é ativado.
 * self.clients.claim() permite que ele controle a página imediatamente.
 */
self.addEventListener('activate', event => {
  console.log('Service Worker: Ativando...');
  return self.clients.claim();
});

/**
 * Evento Fetch:
 * Disparado para cada requisição de rede. Esta é a parte mais importante.
 * A simples presença deste evento faz com que o navegador trate o site como um PWA
 * e respeite as regras do manifest.json (como a tela cheia).
 * event.respondWith(fetch(event.request)) simplesmente repassa a requisição para a internet,
 * garantindo que seu app Streamlit, que é dinâmico, sempre carregue os dados mais recentes.
 */
self.addEventListener('fetch', event => {
  event.respondWith(fetch(event.request));
});
