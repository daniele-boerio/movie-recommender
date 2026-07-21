const BASE = '/api';

// Chiamato quando la sessione è irrecuperabile: l'AuthContext ci aggancia il logout.
let onSessionExpired = null;
export const setSessionExpiredHandler = (fn) => {
  onSessionExpired = fn;
};

// Su questi un 401 è una risposta legittima (credenziali sbagliate, sessione assente),
// non un access token scaduto: ritentare col refresh non avrebbe senso, e su /refresh
// stesso creerebbe un ciclo infinito.
const NO_REFRESH_RETRY = [
  '/auth/login',
  '/auth/refresh',
  '/auth/logout',
  '/auth/register',
  '/auth/register/request',
  '/auth/password-reset/request',
  '/auth/password-reset/confirm',
];

async function request(path, options = {}, allowRefresh = true) {
  const res = await fetch(`${BASE}${path}`, {
    // I cookie di sessione sono httpOnly: il browser li allega da solo, JS non li vede.
    // 'same-origin' è già il default di fetch, esplicitato per chiarezza.
    credentials: 'same-origin',
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });

  // L'access token dura 30 minuti, il refresh 90 giorni: senza questo rientro
  // l'utente verrebbe buttato fuori ogni mezz'ora pur avendo una sessione valida.
  if (res.status === 401 && allowRefresh && !NO_REFRESH_RETRY.includes(path)) {
    const refreshed = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'same-origin',
    });
    if (refreshed.ok) {
      return request(path, options, false); // un solo tentativo
    }
    onSessionExpired?.();
    throw new Error('Sessione scaduta');
  }

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Errore ${res.status}`);
  }
  return res.json();
}

// Scarica una risposta binaria (es. l'export CSV) e la salva come file. Stesso rientro
// sul 401 di `request`, ma qui il corpo è un blob, non JSON.
async function downloadBlob(path, filename, allowRefresh = true) {
  const res = await fetch(`${BASE}${path}`, { credentials: 'same-origin' });

  if (res.status === 401 && allowRefresh) {
    const refreshed = await fetch(`${BASE}/auth/refresh`, {
      method: 'POST',
      credentials: 'same-origin',
    });
    if (refreshed.ok) return downloadBlob(path, filename, false);
    onSessionExpired?.();
    throw new Error('Sessione scaduta');
  }
  if (!res.ok) throw new Error(`Errore ${res.status}`);

  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export const api = {
  // Auth
  requestCode: (email) =>
    request('/auth/register/request', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  register: (payload) =>
    request('/auth/register', { method: 'POST', body: JSON.stringify(payload) }),

  login: (identifier, password) =>
    request('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ identifier, password }),
    }),

  logout: () => request('/auth/logout', { method: 'POST' }),

  // Recupero password (utente non loggato)
  requestPasswordReset: (email) =>
    request('/auth/password-reset/request', {
      method: 'POST',
      body: JSON.stringify({ email }),
    }),

  confirmPasswordReset: (email, code, new_password) =>
    request('/auth/password-reset/confirm', {
      method: 'POST',
      body: JSON.stringify({ email, code, new_password }),
    }),

  me: () => request('/auth/me'),

  // Gestione account (pagina Impostazioni)
  changePassword: (current_password, new_password) =>
    request('/auth/change-password', {
      method: 'POST',
      body: JSON.stringify({ current_password, new_password }),
    }),

  requestEmailChange: (new_email, password) =>
    request('/auth/change-email/request', {
      method: 'POST',
      body: JSON.stringify({ new_email, password }),
    }),

  confirmEmailChange: (new_email, code) =>
    request('/auth/change-email/confirm', {
      method: 'POST',
      body: JSON.stringify({ new_email, code }),
    }),

  getSessions: () => request('/auth/sessions'),

  revokeOtherSessions: () =>
    request('/auth/sessions/revoke-others', { method: 'POST' }),

  deleteAccount: (password) =>
    request('/auth/account', { method: 'DELETE', body: JSON.stringify({ password }) }),

  // Search & discovery
  search: (q, mediaType = 'multi', page = 1) =>
    request(`/search?q=${encodeURIComponent(q)}&media_type=${mediaType}&page=${page}`),

  trending: (mediaType = 'all', page = 1) =>
    request(`/trending?media_type=${mediaType}&page=${page}`),

  details: (mediaType, id) =>
    request(`/details/${mediaType}/${id}`),

  person: (id) =>
    request(`/person/${id}`),

  tvSeason: (tmdbId, seasonNumber) =>
    request(`/tv/${tmdbId}/season/${seasonNumber}`),

  genres: (mediaType) =>
    request(`/genres/${mediaType}`),

  discover: (mediaType, params = {}) => {
    const qs = new URLSearchParams({ ...params }).toString();
    return request(`/discover/${mediaType}?${qs}`);
  },

  // Watched list
  getWatched: () =>
    request('/watched'),

  addWatched: (item) =>
    request('/watched', { method: 'POST', body: JSON.stringify(item) }),

  removeWatched: (tmdbId, mediaType) =>
    request(`/watched/${tmdbId}/${mediaType}`, { method: 'DELETE' }),

  updateRating: (tmdbId, mediaType, rating) =>
    request(`/watched/${tmdbId}/${mediaType}`, {
      method: 'PATCH',
      body: JSON.stringify({ rating }),
    }),

  // Patch parziale: recensione e/o data di visione (i campi assenti restano invariati)
  updateWatched: (tmdbId, mediaType, patch) =>
    request(`/watched/${tmdbId}/${mediaType}`, {
      method: 'PATCH',
      body: JSON.stringify(patch),
    }),

  // Watchlist "Da vedere" (stessa forma degli item di /watched)
  getWatchlist: () =>
    request('/watchlist'),

  addWatchlist: (item) =>
    request('/watchlist', { method: 'POST', body: JSON.stringify(item) }),

  removeWatchlist: (tmdbId, mediaType) =>
    request(`/watchlist/${tmdbId}/${mediaType}`, { method: 'DELETE' }),

  // Progresso episodi (serie TV / anime)
  getProgress: (tmdbId) =>
    request(`/progress/${tmdbId}`),

  markEpisode: (tmdbId, seasonNumber, episodeNumber) =>
    request(`/progress/${tmdbId}/episode`, {
      method: 'POST',
      body: JSON.stringify({ season_number: seasonNumber, episode_number: episodeNumber }),
    }),

  unmarkEpisode: (tmdbId, seasonNumber, episodeNumber) =>
    request(`/progress/${tmdbId}/episode/${seasonNumber}/${episodeNumber}`, { method: 'DELETE' }),

  markSeason: (tmdbId, seasonNumber, episodeNumbers) =>
    request(`/progress/${tmdbId}/season/${seasonNumber}`, {
      method: 'POST',
      body: JSON.stringify({ episode_numbers: episodeNumbers }),
    }),

  unmarkSeason: (tmdbId, seasonNumber) =>
    request(`/progress/${tmdbId}/season/${seasonNumber}`, { method: 'DELETE' }),

  // Statistiche personali
  getStats: () =>
    request('/stats'),

  // Calendario uscite (dai titoli in watchlist)
  getCalendar: () =>
    request('/calendar'),

  // Liste personalizzate
  getLists: () =>
    request('/lists'),

  createList: (name) =>
    request('/lists', { method: 'POST', body: JSON.stringify({ name }) }),

  getList: (id) =>
    request(`/lists/${id}`),

  renameList: (id, name) =>
    request(`/lists/${id}`, { method: 'PATCH', body: JSON.stringify({ name }) }),

  deleteList: (id) =>
    request(`/lists/${id}`, { method: 'DELETE' }),

  addToList: (id, item) =>
    request(`/lists/${id}/items`, { method: 'POST', body: JSON.stringify(item) }),

  removeFromList: (id, tmdbId, mediaType) =>
    request(`/lists/${id}/items/${tmdbId}/${mediaType}`, { method: 'DELETE' }),

  // Import CSV (batch di righe già normalizzate)
  importCsv: (items) =>
    request('/import/csv', { method: 'POST', body: JSON.stringify({ items }) }),

  // Export CSV (scarica un file, non JSON)
  exportCsv: () => downloadBlob('/import/export', 'watchnext-export.csv'),

  // Recommendations
  getRecommendations: (limit = 20) =>
    request(`/recommendations?limit=${limit}`),
};

// Image URL helper
export const posterUrl = (path, size = 'w342') =>
  path ? `https://image.tmdb.org/t/p/${size}${path}` : null;

export const backdropUrl = (path) =>
  path ? `https://image.tmdb.org/t/p/w1280${path}` : null;
