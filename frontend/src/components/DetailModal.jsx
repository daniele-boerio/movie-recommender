import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { X, Bookmark, BookmarkPlus, BookmarkCheck, Star, ExternalLink, Play, Tv } from 'lucide-react';
import { api, posterUrl, backdropUrl } from '../api';
import { useApp } from '../App';
import StarRating from './StarRating';
import EpisodeTracker from './EpisodeTracker';
import AddToListMenu from './AddToListMenu';

export default function DetailModal({ item, onClose }) {
  const { isWatched, isInWatchlist, toggleWatched, toggleWatchlist, watchedMap, updateRating, reloadLists, addToast } = useApp();
  const navigate = useNavigate();
  const [details, setDetails] = useState(null);
  const [loading, setLoading] = useState(true);
  const [showTrailer, setShowTrailer] = useState(false);
  const [review, setReview] = useState('');
  const [watchedOn, setWatchedOn] = useState('');
  const [savingDiary, setSavingDiary] = useState(false);

  const tmdbId = item.tmdb_id || item.id;
  const mediaType = item.media_type;
  const watched = isWatched(tmdbId, mediaType);
  const inWatchlist = isInWatchlist(tmdbId, mediaType);
  const watchedData = watchedMap[`${tmdbId}-${mediaType}`];
  const currentRating = watchedData?.rating;

  useEffect(() => {
    setLoading(true);
    setShowTrailer(false);
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

  // Sincronizza il diario locale all'apertura di un titolo. Non dipende da watchedMap
  // di proposito: dopo il salvataggio non vogliamo che un reload sovrascriva l'input.
  useEffect(() => {
    const wd = watchedMap[`${tmdbId}-${mediaType}`];
    setReview(wd?.review || '');
    setWatchedOn(wd?.watched_on || '');
  }, [tmdbId, mediaType]); // eslint-disable-line react-hooks/exhaustive-deps

  const saveDiary = async () => {
    setSavingDiary(true);
    try {
      await api.updateWatched(tmdbId, mediaType, {
        review: review.trim(),
        watched_on: watchedOn || null,
      });
      addToast('Diario salvato');
      reloadLists();
    } catch {
      addToast('Errore nel salvataggio');
    } finally {
      setSavingDiary(false);
    }
  };

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

  // Trailer: preferiamo un trailer YouTube ufficiale, poi uno qualsiasi, poi un video.
  const videos = details?.videos?.results || [];
  const trailer =
    videos.find((v) => v.site === 'YouTube' && v.type === 'Trailer' && v.official) ||
    videos.find((v) => v.site === 'YouTube' && v.type === 'Trailer') ||
    videos.find((v) => v.site === 'YouTube');

  // "Dove guardarlo": disponibilità italiana. flatrate = incluso nell'abbonamento.
  const providersIT = details?.['watch/providers']?.results?.IT;
  const flatrate = providersIT?.flatrate || [];
  const justwatchLink = providersIT?.link;

  // Stesso item arricchito per entrambe le azioni: al momento del click abbiamo i
  // dettagli TMDB (generi in chiaro), che l'item della card magari non aveva.
  const enrichedItem = () => ({
    ...item,
    id: tmdbId,
    tmdb_id: tmdbId,
    title: title,
    genre_ids: details?.genres?.map((g) => g.id) || item.genre_ids || [],
  });

  const handleToggle = () => toggleWatched(enrichedItem());
  const handleToggleWatchlist = () => toggleWatchlist(enrichedItem());

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

            {/* Cast (nomi cliccabili → scheda persona) */}
            {cast.length > 0 && (
              <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', marginBottom: 20 }}>
                <strong style={{ color: 'var(--text-primary)' }}>Cast:</strong>{' '}
                {cast.map((c, i) => (
                  <span key={c.id}>
                    <button
                      className="cast-link"
                      onClick={() => { onClose(); navigate(`/person/${c.id}`); }}
                    >
                      {c.name}
                    </button>
                    {i < cast.length - 1 ? ', ' : ''}
                  </span>
                ))}
              </p>
            )}

            {/* Dove guardarlo (streaming in Italia) */}
            {flatrate.length > 0 && (
              <div className="watch-providers">
                <div className="watch-providers-head">
                  <Tv size={15} /> Dove guardarlo
                </div>
                <div className="watch-providers-logos">
                  {flatrate.map((p) => (
                    <img
                      key={p.provider_id}
                      className="provider-logo"
                      src={posterUrl(p.logo_path, 'w92')}
                      alt={p.provider_name}
                      title={p.provider_name}
                    />
                  ))}
                </div>
                {justwatchLink && (
                  <a
                    className="watch-providers-src"
                    href={justwatchLink}
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    Dati JustWatch
                  </a>
                )}
              </div>
            )}

            {/* Trailer (embed YouTube on demand) */}
            {trailer && showTrailer && (
              <div className="trailer-embed">
                <iframe
                  src={`https://www.youtube-nocookie.com/embed/${trailer.key}`}
                  title="Trailer"
                  allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
                  allowFullScreen
                />
              </div>
            )}

            {/* Actions */}
            <div className="modal-actions">
              {watched ? (
                <button className="btn btn-danger" onClick={handleToggle}>
                  <BookmarkCheck size={18} /> Rimuovi dai visti
                </button>
              ) : (
                <>
                  <button className="btn btn-primary" onClick={handleToggle}>
                    <BookmarkPlus size={18} /> Ho visto questo
                  </button>
                  <button className="btn btn-secondary" onClick={handleToggleWatchlist}>
                    {inWatchlist ? (
                      <>
                        <BookmarkCheck size={18} /> Rimuovi da “Da vedere”
                      </>
                    ) : (
                      <>
                        <Bookmark size={18} /> Da vedere
                      </>
                    )}
                  </button>
                </>
              )}

              {trailer && (
                <button
                  className="btn btn-secondary"
                  onClick={() => setShowTrailer((s) => !s)}
                >
                  <Play size={16} /> {showTrailer ? 'Nascondi trailer' : 'Trailer'}
                </button>
              )}

              <a
                href={`https://www.themoviedb.org/${mediaType}/${tmdbId}`}
                target="_blank"
                rel="noopener noreferrer"
                className="btn btn-secondary"
              >
                <ExternalLink size={16} /> TMDB
              </a>
            </div>

            {/* Aggiungi a una lista personalizzata */}
            <AddToListMenu
              item={{
                tmdb_id: tmdbId,
                media_type: mediaType,
                title,
                poster_path: details?.poster_path || item.poster_path,
                vote_average: vote,
                release_date: date,
              }}
            />

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

            {/* Diario personale: quando l'ho visto + recensione */}
            {watched && (
              <div className="diary-box">
                <div className="diary-field">
                  <label className="diary-label" htmlFor="watched-on">Visto il</label>
                  <input
                    id="watched-on"
                    type="date"
                    className="diary-date"
                    value={watchedOn}
                    onChange={(e) => setWatchedOn(e.target.value)}
                  />
                </div>
                <label className="diary-label" htmlFor="review">La tua recensione</label>
                <textarea
                  id="review"
                  className="diary-review"
                  value={review}
                  onChange={(e) => setReview(e.target.value)}
                  placeholder="Cosa ne pensi? (appunti, sensazioni, con chi l'hai visto…)"
                  rows={3}
                />
                <button className="btn btn-secondary diary-save" onClick={saveDiary} disabled={savingDiary}>
                  {savingDiary ? 'Salvataggio…' : 'Salva nel diario'}
                </button>
              </div>
            )}

            {/* Episodi (serie TV e anime) */}
            {mediaType === 'tv' && details && (
              <EpisodeTracker
                tmdbId={tmdbId}
                seasons={details.seasons}
                watched={watched}
                onMarkSeriesWatched={handleToggle}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
}
