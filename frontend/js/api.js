// Ajusta esto a la URL real del backend en producción
const API_BASE = window.DCPI_API_BASE || '/api';

const DcpiApi = (() => {
  async function request(path, options = {}) {
    const headers = { ...(options.headers || {}) };
    if (options.auth) {
      if (DcpiTelegram.isTelegram) {
        headers['X-Telegram-Init-Data'] = DcpiTelegram.getInitData();
      } else {
        headers['X-Guest-Id'] = DcpiTelegram.getGuestId();
      }
    }
    if (options.body) headers['Content-Type'] = 'application/json';

    const res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers,
      body: options.body ? JSON.stringify(options.body) : undefined,
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ error: 'Error desconocido' }));
      throw new Error(err.error || `Error ${res.status}`);
    }
    return res.status === 204 ? null : res.json();
  }

  const search = (q) => request(`/search?q=${encodeURIComponent(q)}`);
  const getFeed = (seed, offset, limit = 10) => {
    const params = new URLSearchParams({ offset, limit });
    if (seed) params.set('seed', seed);
    return request(`/feed?${params.toString()}`);
  };
  const getTrack = (id) => request(`/track/${id}`);
  const getLyrics = (id) => request(`/lyrics/${id}`);
  const getQualities = (id) => request(`/download/${id}/qualities`);
  const streamUrl = (id) => `${API_BASE}/stream/${id}`;
  const downloadUrl = (id, format, quality) => `${API_BASE}/download/${id}?format=${format}&quality=${quality}`;

  const getHistory = () => request('/history', { auth: true });
  const addHistory = (track) => request('/history', { method: 'POST', auth: true, body: track });
  const clearHistory = () => request('/history', { method: 'DELETE', auth: true });

  const getFavorites = () => request('/favorites', { auth: true });
  const addFavorite = (track) => request('/favorites', { method: 'POST', auth: true, body: track });
  const removeFavorite = (trackId) => request(`/favorites/${trackId}`, { method: 'DELETE', auth: true });

  return {
    search, getFeed, getTrack, getLyrics, getQualities, streamUrl, downloadUrl,
    getHistory, addHistory, clearHistory,
    getFavorites, addFavorite, removeFavorite,
  };
})();
