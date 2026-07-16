import { Star, Check } from 'lucide-react';
import { posterUrl } from '../api';
import { useApp } from '../App';

export default function MediaCard({ item, showReason }) {
  const { isWatched, setSelectedItem } = useApp();
  const title = item.title || item.name || '';
  const date = item.release_date || item.first_air_date || '';
  const year = date ? date.slice(0, 4) : '';
  const rating = item.vote_average ? item.vote_average.toFixed(1) : null;
  const watched = isWatched(item.tmdb_id || item.id, item.media_type);
  const poster = posterUrl(item.poster_path);

  return (
    <div
      className="media-card"
      onClick={() => setSelectedItem(item)}
      role="button"
      tabIndex={0}
    >
      {watched && (
        <div className="watched-badge">
          <Check />
        </div>
      )}
      {poster ? (
        <img
          className="media-card-poster"
          src={poster}
          alt={title}
          loading="lazy"
        />
      ) : (
        <div
          className="media-card-poster"
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            color: 'var(--text-muted)',
            fontSize: '0.8rem',
            padding: 12,
            textAlign: 'center',
          }}
        >
          {title}
        </div>
      )}
      <div className="media-card-info">
        <div className="media-card-title">{title}</div>
        <div className="media-card-meta">
          {rating && (
            <span className="media-card-rating">
              <Star size={12} fill="currentColor" />
              {rating}
            </span>
          )}
          {year && <span>{year}</span>}
          <span className="media-card-type">
            {item.media_type === 'tv' ? 'Serie' : 'Film'}
          </span>
        </div>
        {showReason && item.recommended_by && item.recommended_by.length > 0 && (
          <div className="rec-reason">
            Perché hai visto <span>{item.recommended_by.slice(0, 2).join(', ')}</span>
          </div>
        )}
      </div>
    </div>
  );
}
