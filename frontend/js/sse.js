// sse.js — EventSource com fallback automático para polling de versão.

const POLL_INTERVAL_MS = 30000;
const SSE_RETRY_MS = 8000;

export function connectLive(onVersion) {
  let source = null;
  let pollTimer = null;
  let retryTimer = null;
  let stopped = false;

  function startPolling() {
    if (pollTimer || stopped) return;
    pollTimer = setInterval(async () => {
      try {
        const resp = await fetch('/api/live/version', { credentials: 'same-origin' });
        if (resp.ok) {
          const data = await resp.json();
          onVersion(data.v);
        }
      } catch { /* offline: tenta no próximo tick */ }
    }, POLL_INTERVAL_MS);
  }

  function stopPolling() {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
  }

  function open() {
    if (stopped) return;
    source = new EventSource('/api/live/sse');
    source.onmessage = (event) => {
      stopPolling();
      try {
        const data = JSON.parse(event.data);
        if (typeof data.v === 'number') onVersion(data.v);
      } catch { /* evento de ping/formato inesperado: ignora */ }
    };
    source.onerror = () => {
      source.close();
      source = null;
      startPolling(); // degrada para polling e tenta SSE de novo depois
      if (!stopped) retryTimer = setTimeout(open, SSE_RETRY_MS);
    };
  }

  open();

  return function disconnect() {
    stopped = true;
    if (source) source.close();
    if (retryTimer) clearTimeout(retryTimer);
    stopPolling();
  };
}
