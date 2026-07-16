import { useEffect, useState } from 'react';
import { X, BookmarkPlus, BookmarkCheck, Star, ExternalLink } from 'lucide-react';
import { api, posterUrl, backdropUrl } from '../api';
import { useApp } from '../App';
import StarRating from './StarRating';

export default function DetailModal({ item, onClose }) {
  const { isWatched, toggleWatched, watchedMap, updateRating } = useApp();
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);

  const tmdbId = item.tmdb_id || item.id;
  const mediaType = item.media_type;
  const watched = isWatched(tmdbId, mediaType);
  const watchedData = watchedMap[`${tmdbId}-${mediaType}`];
  const currentRating = watchedData?.rating;

  useEffect(() => {
    setLoading(true);
    api.details(mediaType, tmdbId)
      .then(setDetails)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [tmdbId, mediaType]);

  useEffect(() => {
    const handler = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onClose]);

  const title = details?.title || details?.name || item.title || item.name || '';
  const overview = details?.overview || item.overview || '';
  const backdrop = backdropUrl(details?.backdrop_path || item.backdrop_path);
  const poster = posterUrl(details?.poster_path || item.poster_path, 'w342');
  const date = details?.release_date || details?.first_air_date || '';
  const year = date ? date.slice(0, 4) : '';
  const runtime = details?.runtime;
  const seasons = details?.number_of_seasons;
  const genres = details?.genres || [];
  const vote = details?.vote_average;
  const cast = details?.credits?.cast?.slice(0, 6) || [];

  const handleToggle = () => {
    toggleWatched({
      ...item,
      id: tmdbId,
      tmdb_id: tmdbId,
      title: title,
      genre_ids: details?.genres?.map((g) => g.id) || item.genre_ids || [],
    });
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Backdrop */}
        <div className="modal-backdrop">
          {backdrop && <img src={backdrop} alt="" />}
          <div className="modal-backdrop-gradient" />
          <button className="modal-close" onClick={onClose}>
            <X size={20} />
          </button>
        </div>

        {loading ? (
          <div className="spinner" style={{ padding: 40 }} />
        ) : (
          <div className="modal-body">
            {/* Header */}
            <div className="modal-header">
              {poster && <img className="modal-poster" src={poster} alt={title} />}
              <div className="modal-title-block">
                <h2 className="modal-title">{title}</h2>
                <div className="modal-badges">
                  {year && <span className="modal-badge">{year}</span>}
                  {runtime && (
                    <span className="modal-badge">{runtime} min</span>
                  )}
                  {seasons && (
                    <span className="modal-badge">
                      {seasons} stagion{seasons === 1 ? 'e' : 'i'}
                    </span>
                  )}
                  {vote && (
                    <span className="modal-badge" style={{ color: 'var(--accent)' }}>
                      <Star size={12} fill="currentColor" style={{ verticalAlign: '-1px' }} />{' '}
                      {vote.toFixed(1)}
                    </span>
                  )}
                  {genres.map((g) => (
                    <span key={g.id} className="modal-badge">{g.name}</span>
                  ))}
                </div>
              </div>
            </div>

            {/* Overview */}
            {overview && <p className="modal-overview">{overview}</p>}

            {/* Cast */}
            {cast.length > 0 && (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 20 }}>
                <strong style={{ color: 'var(--text-primary)' }}>Cast:</strong>{' '}
                {cast.map((c) => c.name).join(', ')}
              </p>
            )}

            {/* Actions */}
            <div className="modal-actions">
              <button
                className={`btn ${watched ? 'btn-danger' : 'btn-primary'}`}
                onClick={handleToggle}
              >
                {watched ? (
                  <>
                    <BookmarkCheck size={18} /> Rimuovi dalla lista
                  </>
                ) : (
                  <>
                    <BookmarkPlus size={18} /> Ho visto questo
                  </>
                )}
              </button>

              <a
                href={`https://www.themoviedb.org/${mediaType}/${tmdbId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary"
              >
                <ExternalLink size={16} /> TMDB
              </a>
            </div>

            {/* Personal rating */}
            {watched && (
              <div style={{ marginBottom: 24 }}>
                <p style={{
                  fontSize: '0.85rem',
                  fontWeight: 600,
                  marginBottom: 8,
                  color: 'var(--text-secondary)',
                }}>
                  Il tuo voto:
                </p>
                <StarRating
                  value={currentRating || 0}
                  onChange={(r) => updateRating(tmdbId, mediaType, r)}
                />
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
