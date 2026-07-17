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

  me: () => request('/auth/me'),

  // Search & discovery
  search: (q, mediaType = 'multi', page = 1) =>
    request(`/search?q=${encodeURIComponent(q)}&media_type=${mediaType}&page=${page}`),

  trending: (mediaType = 'all', page = 1) =>
    request(`/trending?media_type=${mediaType}&page=${page}`),

  details: (mediaType, id) =>
    request(`/details/${mediaType}/${id}`),

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

  // Recommendations
  getRecommendations: (limit = 20) =>
    request(`/recommendations?limit=${limit}`),
};

// Image URL helper
export const posterUrl = (path, size = 'w342') =>
  path ? `https://image.tmdb.org/t/p/${size}${path}` : null;

export const backdropUrl = (path) =>
  path ? `https://image.tmdb.org/t/p/w1280${path}` : null;
