import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Users, Search, UserPlus, UserCheck, Star } from 'lucide-react';
import { api, posterUrl } from '../api';
import { useApp } from '../App';

// "2026-07-20T…" → "oggi" / "ieri" / "N giorni fa"
const relTime = (iso) => {
  if (!iso) return '';
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (days <= 0) return 'oggi';
  if (days === 1) return 'ieri';
  if (days < 30) return `${days} giorni fa`;
  const months = Math.floor(days / 30);
  return months === 1 ? '1 mese fa' : `${months} mesi fa`;
};

export default function CommunityPage() {
  const { addToast, setSelectedItem } = useApp();
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const [following, setFollowing] = useState([]);
  const [feed, setFeed] = useState([]);

  const loadFollowing = () => api.getFollowing().then(setFollowing).catch(() => setFollowing([]));

  useEffect(() => {
    loadFollowing();
    api.getFeed().then(setFeed).catch(() => setFeed([]));
  }, []);

  // Ricerca "as you type" con un piccolo debounce: da 2 caratteri in su.
  useEffect(() => {
    const term = q.trim();
    if (term.length < 2) { setResults([]); return; }
    const t = setTimeout(() => {
      api.searchUsers(term).then(setResults).catch(() => setResults([]));
    }, 250);
    return () => clearTimeout(t);
  }, [q]);

  const toggleFollow = async (u) => {
    try {
      if (u.is_following) {
        await api.unfollowUser(u.username);
      } else {
        await api.followUser(u.username);
      }
      setResults((rs) =>
        rs.map((r) => (r.id === u.id ? { ...r, is_following: !u.is_following } : r))
      );
      loadFollowing();
    } catch {
      addToast('Errore');
    }
  };

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Community</h1>
        <p className="page-subtitle">Cerca altri utenti e segui i loro gusti</p>
      </div>

      <div className="search-bar" style={{ maxWidth: 480 }}>
        <Search className="search-icon" />
        <input
          type="text"
          placeholder="Cerca per username…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          autoFocus
        />
      </div>

      {results.length > 0 && (
        <div className="user-list">
          {results.map((u) => (
            <div className="user-row" key={u.id}>
              <Link to={`/u/${u.username}`} className="user-row-name">
                <Users size={16} /> {u.username}
              </Link>
              <button
                className={`btn ${u.is_following ? 'btn-secondary' : 'btn-primary'}`}
                onClick={() => toggleFollow(u)}
              >
                {u.is_following ? (
                  <><UserCheck size={15} /> Segui già</>
                ) : (
                  <><UserPlus size={15} /> Segui</>
                )}
              </button>
            </div>
          ))}
        </div>
      )}

      {feed.length > 0 && (
        <>
          <h2 className="section-title" style={{ marginTop: 32 }}>Attività recente</h2>
          <div className="feed-list">
            {feed.map((ev, i) => (
              <button
                className="feed-row"
                key={`${ev.username}-${ev.tmdb_id}-${ev.media_type}-${i}`}
                onClick={() => setSelectedItem({ ...ev, id: ev.tmdb_id })}
              >
                {posterUrl(ev.poster_path, 'w92') ? (
                  <img className="feed-poster" src={posterUrl(ev.poster_path, 'w92')} alt="" />
                ) : (
                  <div className="feed-poster feed-poster-empty" />
                )}
                <div className="feed-info">
                  <div className="feed-text">
                    <strong>{ev.username}</strong> ha visto <strong>{ev.title}</strong>
                  </div>
                  <div className="feed-meta">
                    {ev.rating != null && (
                      <span className="feed-rating"><Star size={12} fill="currentColor" /> {ev.rating}</span>
                    )}
                    <span>{relTime(ev.added_at)}</span>
                  </div>
                </div>
              </button>
            ))}
          </div>
        </>
      )}

      <h2 className="section-title" style={{ marginTop: 32 }}>Chi segui</h2>
      {following.length === 0 ? (
        <p className="stats-empty">Non segui ancora nessuno. Cerca qualcuno qui sopra.</p>
      ) : (
        <div className="user-list">
          {following.map((u) => (
            <div className="user-row" key={u.id}>
              <Link to={`/u/${u.username}`} className="user-row-name">
                <Users size={16} /> {u.username}
              </Link>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
