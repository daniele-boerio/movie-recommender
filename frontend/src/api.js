const BASE = '/api';

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Errore ${res.status}`);
  }
  return res.json();
}

export const api = {
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
