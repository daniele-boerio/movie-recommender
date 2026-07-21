import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Film, Tv, Star, UserPlus, UserCheck } from 'lucide-react';
import { api } from '../api';
import { useApp } from '../App';
import MediaCard from '../components/MediaCard';

export default function UserProfilePage() {
  const { username } = useParams();
  const navigate = useNavigate();
  const { addToast } = useApp();
  const [profile, setProfile] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    setProfile(null);
    setNotFound(false);
    window.scrollTo(0, 0);
    api.getProfile(username)
      .then(setProfile)
      .catch(() => setNotFound(true));
  }, [username]);

  const toggleFollow = async () => {
    setBusy(true);
    try {
      if (profile.is_following) {
        await api.unfollowUser(username);
        setProfile((p) => ({ ...p, is_following: false, followers: p.followers - 1 }));
      } else {
        await api.followUser(username);
        setProfile((p) => ({ ...p, is_following: true, followers: p.followers + 1 }));
      }
    } catch {
      addToast('Errore');
    } finally {
      setBusy(false);
    }
  };

  if (notFound) {
    return (
      <div className="empty-state">
        <h3>Utente non trovato</h3>
        <button className="btn btn-secondary" onClick={() => navigate('/community')}>
          Torna alla community
        </button>
      </div>
    );
  }
  if (!profile) return <div className="spinner" />;

  const { stats } = profile;

  return (
    <>
      <button className="back-btn" onClick={() => navigate('/community')}>
        <ArrowLeft size={16} /> Community
      </button>

      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <h1 className="page-title">{profile.username}</h1>
          <p className="page-subtitle">
            {profile.followers} follower · {profile.following} seguiti
          </p>
          {profile.compatibility && (
            <div className="compat">
              {profile.compatibility.common === 0 ? (
                <span className="compat-none">Nessun voto in comune per l'affinità</span>
              ) : (
                <>
                  <span className="compat-score">{profile.compatibility.score}%</span>
                  <span className="compat-label">
                    affinità di gusti · {profile.compatibility.common} titol
                    {profile.compatibility.common === 1 ? 'o' : 'i'} votat
                    {profile.compatibility.common === 1 ? 'o' : 'i'} in comune
                  </span>
                </>
              )}
            </div>
          )}
        </div>
        {!profile.is_self && (
          <button
            className={`btn ${profile.is_following ? 'btn-secondary' : 'btn-primary'}`}
            onClick={toggleFollow}
            disabled={busy}
          >
            {profile.is_following ? (
              <><UserCheck size={16} /> Segui già</>
            ) : (
              <><UserPlus size={16} /> Segui</>
            )}
          </button>
        )}
      </div>

      <div className="stats-tiles">
        <div className="stat-tile">
          <Film className="stat-tile-icon" />
          <div className="stat-tile-value">{stats.movie}</div>
          <div className="stat-tile-label">Film visti</div>
        </div>
        <div className="stat-tile">
          <Tv className="stat-tile-icon" />
          <div className="stat-tile-value">{stats.tv}</div>
          <div className="stat-tile-label">Serie viste</div>
        </div>
        <div className="stat-tile">
          <Star className="stat-tile-icon" />
          <div className="stat-tile-value">{stats.avg_rating != null ? stats.avg_rating : '—'}</div>
          <div className="stat-tile-label">Voto medio</div>
        </div>
      </div>

      <h2 className="section-title">Visti di recente</h2>
      {profile.watched.length === 0 ? (
        <p className="stats-empty">Non ha ancora segnato nessun titolo come visto.</p>
      ) : (
        <div className="media-grid">
          {profile.watched.map((item) => (
            <MediaCard
              key={`${item.tmdb_id}-${item.media_type}`}
              item={{ ...item, id: item.tmdb_id }}
              personalRating={item.rating}
            />
          ))}
        </div>
      )}
    </>
  );
}
