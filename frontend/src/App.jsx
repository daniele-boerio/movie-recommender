import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Search, Film, Bookmark, BookmarkCheck, Sparkles, TrendingUp, LogOut } from 'lucide-react';
import { api } from './api';
import { useAuth } from './AuthContext';

import DiscoverPage from './pages/DiscoverPage';
import WatchedPage from './pages/WatchedPage';
import WatchlistPage from './pages/WatchlistPage';
import RecommendationsPage from './pages/RecommendationsPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import DetailModal from './components/DetailModal';
import Toast from './components/Toast';

// ── Global context ──
const AppContext = createContext();
export const useApp = () => useContext(AppContext);

export default function App() {
  const { user, loading } = useAuth();

  // I cookie sono httpOnly: sapere se la sessione è viva richiede un giro sul server.
  // Senza questa attesa comparirebbe il login per un istante a ogni ricarica.
  if (loading) {
    return (
      <div className="auth-layout">
        <div className="spinner" />
      </div>
    );
  }

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    );
  }

  // key={user.id}: cambiando utente React rimonta tutto, quindi watchedMap non può
  // sopravvivere da una sessione all'altra e mostrare la lista di qualcun altro.
  return <AuthenticatedApp key={user.id} />;
}

function AuthenticatedApp() {
  const { user, logout } = useAuth();
  const [watchedMap, setWatchedMap] = useState({}); // key: `${tmdb_id}-${media_type}`
  const [watchlistMap, setWatchlistMap] = useState({}); // "Da vedere", stessa chiave
  const [selectedItem, setSelectedItem] = useState(null);
  const [toasts, setToasts] = useState([]);

  // Load both lists on mount. Un titolo sta in una sola delle due (lo garantisce il
  // vincolo UNIQUE lato DB), quindi le due mappe non si sovrappongono mai.
  useEffect(() => {
    const toMap = (items) => {
      const map = {};
      items.forEach((it) => {
        map[`${it.tmdb_id}-${it.media_type}`] = it;
      });
      return map;
    };
    api.getWatched().then((items) => setWatchedMap(toMap(items))).catch(() => {});
    api.getWatchlist().then((items) => setWatchlistMap(toMap(items))).catch(() => {});
  }, []);

  const isWatched = useCallback(
    (tmdbId, mediaType) => !!watchedMap[`${tmdbId}-${mediaType}`],
    [watchedMap]
  );

  const isInWatchlist = useCallback(
    (tmdbId, mediaType) => !!watchlistMap[`${tmdbId}-${mediaType}`],
    [watchlistMap]
  );

  const addToast = useCallback((message, type = 'success') => {
    const id = Date.now();
    setToasts((prev) => [...prev, { id, message, type }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((t) => t.id !== id));
    }, 3000);
  }, []);

  const toggleWatched = useCallback(async (item) => {
    const key = `${item.tmdb_id || item.id}-${item.media_type}`;
    const tmdbId = item.tmdb_id || item.id;

    if (watchedMap[key]) {
      try {
        await api.removeWatched(tmdbId, item.media_type);
        setWatchedMap((prev) => {
          const next = { ...prev };
          delete next[key];
          return next;
        });
        addToast('Rimosso dalla lista');
      } catch {
        addToast('Errore nella rimozione', 'error');
      }
    } else {
      const payload = {
        tmdb_id: tmdbId,
        media_type: item.media_type,
        title: item.title || item.name || '',
        poster_path: item.poster_path || null,
        vote_average: item.vote_average || null,
        overview: item.overview || null,
        genre_ids: JSON.stringify(item.genre_ids || []),
        release_date: item.release_date || item.first_air_date || null,
        rating: null,
      };
      const wasInWatchlist = !!watchlistMap[key];
      try {
        await api.addWatched(payload);
        setWatchedMap((prev) => ({ ...prev, [key]: payload }));
        // Se era tra i "da vedere", il backend l'ha spostato: togliamolo di lì anche qui.
        if (wasInWatchlist) {
          setWatchlistMap((prev) => {
            const next = { ...prev };
            delete next[key];
            return next;
          });
        }
        addToast(wasInWatchlist ? 'Segnato come visto ✓' : 'Aggiunto ai visti ✓');
      } catch (e) {
        if (e.message.includes('409') || e.message.includes('Già')) {
          addToast('Già nella lista', 'error');
        } else {
          addToast('Errore', 'error');
        }
      }
    }
  }, [watchedMap, watchlistMap, addToast]);

  const toggleWatchlist = useCallback(async (item) => {
    const key = `${item.tmdb_id || item.id}-${item.media_type}`;
    const tmdbId = item.tmdb_id || item.id;

    if (watchlistMap[key]) {
      try {
        await api.removeWatchlist(tmdbId, item.media_type);
        setWatchlistMap((prev) => {
          const next = { ...prev };
          delete next[key];
          return next;
        });
        addToast('Rimosso da "Da vedere"');
      } catch {
        addToast('Errore nella rimozione', 'error');
      }
    } else {
      const payload = {
        tmdb_id: tmdbId,
        media_type: item.media_type,
        title: item.title || item.name || '',
        poster_path: item.poster_path || null,
        vote_average: item.vote_average || null,
        overview: item.overview || null,
        genre_ids: JSON.stringify(item.genre_ids || []),
        release_date: item.release_date || item.first_air_date || null,
        rating: null,
      };
      try {
        await api.addWatchlist(payload);
        setWatchlistMap((prev) => ({ ...prev, [key]: payload }));
        addToast('Aggiunto a "Da vedere" ✓');
      } catch (e) {
        // Il backend rifiuta con 409 se il titolo è già nei visti.
        if (e.message.includes('visti')) {
          addToast('È già nei tuoi visti', 'error');
        } else if (e.message.includes('409') || e.message.includes('Già')) {
          addToast('Già in "Da vedere"', 'error');
        } else {
          addToast('Errore', 'error');
        }
      }
    }
  }, [watchlistMap, addToast]);

  const updateRating = useCallback(async (tmdbId, mediaType, rating) => {
    try {
      await api.updateRating(tmdbId, mediaType, rating);
      const key = `${tmdbId}-${mediaType}`;
      setWatchedMap((prev) => ({
        ...prev,
        [key]: { ...prev[key], rating },
      }));
    } catch {
      addToast('Errore nell\'aggiornamento', 'error');
    }
  }, [addToast]);

  const ctx = {
    watchedMap,
    watchlistMap,
    isWatched,
    isInWatchlist,
    toggleWatched,
    toggleWatchlist,
    updateRating,
    setSelectedItem,
    addToast,
  };

  const navLinks = [
    { to: '/', icon: TrendingUp, label: 'Scopri' },
    { to: '/search', icon: Search, label: 'Cerca' },
    { to: '/watched', icon: BookmarkCheck, label: 'Visti' },
    { to: '/watchlist', icon: Bookmark, label: 'Da vedere' },
    { to: '/recommendations', icon: Sparkles, label: 'Per te' },
  ];

  return (
    <AppContext.Provider value={ctx}>
      <div className="app-layout">
        {/* Sidebar */}
        <nav className="sidebar">
          <div className="sidebar-logo">
            <Film size={20} style={{ display: 'inline', verticalAlign: '-3px', marginRight: 6 }} />
            WatchNext
          </div>
          <div className="sidebar-nav">
            {navLinks.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) =>
                  `sidebar-link ${isActive ? 'active' : ''}`
                }
              >
                <Icon />
                <span>{label}</span>
              </NavLink>
            ))}
          </div>
          <div className="sidebar-footer">
            <div className="sidebar-user">
              <span className="sidebar-username" title={user.email}>{user.username}</span>
              <button className="sidebar-logout" onClick={logout} title="Esci">
                <LogOut size={15} />
              </button>
            </div>
            Powered by TMDB
          </div>
        </nav>

        {/* Main */}
        <main className="main-content">
          <Routes>
            <Route path="/" element={<DiscoverPage />} />
            <Route path="/search" element={<DiscoverPage searchMode />} />
            <Route path="/watched" element={<WatchedPage />} />
            <Route path="/watchlist" element={<WatchlistPage />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            {/* Già autenticati: /login e /register non hanno più senso */}
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>

      {/* Detail modal */}
      {selectedItem && (
        <DetailModal
          item={selectedItem}
          onClose={() => setSelectedItem(null)}
        />
      )}

      {/* Toasts */}
      <Toast toasts={toasts} />
    </AppContext.Provider>
  );
}
