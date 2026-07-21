import { useState, useEffect, useCallback, createContext, useContext } from 'react';
import { Routes, Route, NavLink, Navigate } from 'react-router-dom';
import { Search, Film, Bookmark, BookmarkCheck, Sparkles, TrendingUp, BarChart3, CalendarDays, ListChecks, Users, Bell, Settings, LogOut, Menu, BookOpen } from 'lucide-react';
import { api } from './api';
import { useAuth } from './AuthContext';

import DiscoverPage from './pages/DiscoverPage';
import WatchedPage from './pages/WatchedPage';
import WatchlistPage from './pages/WatchlistPage';
import StatsPage from './pages/StatsPage';
import DiaryPage from './pages/DiaryPage';
import CalendarPage from './pages/CalendarPage';
import ListsPage from './pages/ListsPage';
import ListDetailPage from './pages/ListDetailPage';
import ImportPage from './pages/ImportPage';
import SettingsPage from './pages/SettingsPage';
import RecommendationsPage from './pages/RecommendationsPage';
import PersonPage from './pages/PersonPage';
import CommunityPage from './pages/CommunityPage';
import UserProfilePage from './pages/UserProfilePage';
import NotificationsPage from './pages/NotificationsPage';
import LoginPage from './pages/LoginPage';
import RegisterPage from './pages/RegisterPage';
import ForgotPasswordPage from './pages/ForgotPasswordPage';
import DetailModal from './components/DetailModal';
import Toast from './components/Toast';
import ThemeToggle from './components/ThemeToggle';

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
        <Route path="/forgot-password" element={<ForgotPasswordPage />} />
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
  const [notifUnread, setNotifUnread] = useState(0);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);

  // Contatore notifiche non lette: al mount e poi ogni 2 minuti. La pagina notifiche
  // lo azzera chiamando refreshNotifications dopo aver segnato tutto come letto.
  const refreshNotifications = useCallback(() => {
    api.getUnreadCount().then((d) => setNotifUnread(d.count)).catch(() => {});
  }, []);

  useEffect(() => {
    refreshNotifications();
    const t = setInterval(refreshNotifications, 120000);
    return () => clearInterval(t);
  }, [refreshNotifications]);

  // Ricarica entrambe le liste dal server. Serve al mount e dopo un import massivo.
  // Un titolo sta in una sola delle due (lo garantisce il vincolo UNIQUE lato DB).
  const reloadLists = useCallback(() => {
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

  useEffect(() => { reloadLists(); }, [reloadLists]);

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
    reloadLists,
    notifUnread,
    refreshNotifications,
    setSelectedItem,
    addToast,
  };

  const navLinks = [
    { to: '/', icon: TrendingUp, label: 'Scopri' },
    { to: '/search', icon: Search, label: 'Cerca' },
    { to: '/watched', icon: BookmarkCheck, label: 'Visti' },
    { to: '/diary', icon: BookOpen, label: 'Diario' },
    { to: '/watchlist', icon: Bookmark, label: 'Da vedere' },
    { to: '/lists', icon: ListChecks, label: 'Liste' },
    { to: '/calendar', icon: CalendarDays, label: 'In arrivo' },
    { to: '/community', icon: Users, label: 'Community' },
    { to: '/recommendations', icon: Sparkles, label: 'Per te' },
    { to: '/stats', icon: BarChart3, label: 'Statistiche' },
  ];

  return (
    <AppContext.Provider value={ctx}>
      <div className="app-layout">
        {/* Topbar (solo mobile) */}
        <header className="topbar">
          <button className="topbar-burger" onClick={() => setMobileNavOpen(true)} aria-label="Apri menu">
            <Menu size={22} />
          </button>
          <span className="topbar-logo">
            <Film size={18} style={{ verticalAlign: '-3px', marginRight: 5 }} />
            WatchNext
          </span>
          {notifUnread > 0 && <span className="topbar-notif">{notifUnread > 9 ? '9+' : notifUnread}</span>}
        </header>

        {/* Backdrop del drawer mobile */}
        {mobileNavOpen && <div className="sidebar-backdrop" onClick={() => setMobileNavOpen(false)} />}

        {/* Sidebar / drawer. Su mobile un click su un link la richiude. */}
        <nav
          className={`sidebar ${mobileNavOpen ? 'open' : ''}`}
          onClick={(e) => { if (e.target.closest('a')) setMobileNavOpen(false); }}
        >
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
              <NavLink to="/notifications" className="sidebar-logout sidebar-settings" title="Notifiche">
                <span className="notif-bell">
                  <Bell size={15} />
                  {notifUnread > 0 && <span className="notif-badge">{notifUnread > 9 ? '9+' : notifUnread}</span>}
                </span>
              </NavLink>
              <ThemeToggle />
              <NavLink to="/settings" className="sidebar-logout sidebar-settings" title="Impostazioni">
                <Settings size={15} />
              </NavLink>
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
            <Route path="/diary" element={<DiaryPage />} />
            <Route path="/watchlist" element={<WatchlistPage />} />
            <Route path="/stats" element={<StatsPage />} />
            <Route path="/calendar" element={<CalendarPage />} />
            <Route path="/lists" element={<ListsPage />} />
            <Route path="/lists/:id" element={<ListDetailPage />} />
            <Route path="/import" element={<ImportPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="/recommendations" element={<RecommendationsPage />} />
            <Route path="/person/:id" element={<PersonPage />} />
            <Route path="/community" element={<CommunityPage />} />
            <Route path="/u/:username" element={<UserProfilePage />} />
            <Route path="/notifications" element={<NotificationsPage />} />
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
