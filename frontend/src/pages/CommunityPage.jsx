import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Users, Search, UserPlus, UserCheck } from 'lucide-react';
import { api } from '../api';
import { useApp } from '../App';

export default function CommunityPage() {
  const { addToast } = useApp();
  const [q, setQ] = useState('');
  const [results, setResults] = useState([]);
  const [following, setFollowing] = useState([]);

  const loadFollowing = () => api.getFollowing().then(setFollowing).catch(() => setFollowing([]));

  useEffect(() => { loadFollowing(); }, []);

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
