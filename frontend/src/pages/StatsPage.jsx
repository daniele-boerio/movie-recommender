import { useEffect, useMemo, useState } from 'react';
import { BarChart3, Film, Tv, Star, Trophy } from 'lucide-react';
import { api, posterUrl } from '../api';
import { useApp } from '../App';

const MONTHS_IT = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];

export default function StatsPage() {
  const { setSelectedItem } = useApp();
  const [stats, setStats] = useState(null);
  const [genresMap, setGenresMap] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([api.getStats(), api.genres('movie'), api.genres('tv')])
      .then(([s, m, t]) => {
        setStats(s);
        const map = {};
        [...(m.genres || []), ...(t.genres || [])].forEach((g) => { map[g.id] = g.name; });
        setGenresMap(map);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const maxGenre = useMemo(
    () => Math.max(1, ...(stats?.genres || []).map((g) => g.count)),
    [stats]
  );
  const maxMonth = useMemo(
    () => Math.max(1, ...(stats?.timeline || []).map((t) => t.count)),
    [stats]
  );
  const maxRatingBar = useMemo(
    () => Math.max(1, ...(stats?.rating_distribution || []).map((r) => r.count)),
    [stats]
  );
  const maxDecade = useMemo(
    () => Math.max(1, ...(stats?.decades || []).map((d) => d.count)),
    [stats]
  );

  if (loading) return <div className="spinner" />;
  if (!stats) return null;

  const { total, avg_rating, rated_count, top_rated, genres, timeline, rating_distribution, decades } = stats;

  if (total.all === 0) {
    return (
      <>
        <div className="page-header">
          <h1 className="page-title">Statistiche</h1>
        </div>
        <div className="empty-state">
          <BarChart3 className="empty-state-icon" />
          <h3>Ancora nessun dato</h3>
          <p>Segna qualche film o serie come visto per vedere qui le tue statistiche</p>
        </div>
      </>
    );
  }

  const monthLabel = (ym) => {
    const [, m] = ym.split('-');
    return MONTHS_IT[parseInt(m, 10) - 1] || '';
  };
  const genreName = (id) => genresMap[id] || `#${id}`;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Statistiche</h1>
        <p className="page-subtitle">Uno sguardo ai tuoi gusti</p>
      </div>

      {/* Tiles */}
      <div className="stats-tiles">
        <div className="stat-tile">
          <Film className="stat-tile-icon" />
          <div className="stat-tile-value">{total.movie}</div>
          <div className="stat-tile-label">Film visti</div>
        </div>
        <div className="stat-tile">
          <Tv className="stat-tile-icon" />
          <div className="stat-tile-value">{total.tv}</div>
          <div className="stat-tile-label">Serie viste</div>
        </div>
        <div className="stat-tile">
          <BarChart3 className="stat-tile-icon" />
          <div className="stat-tile-value">{total.all}</div>
          <div className="stat-tile-label">Totale titoli</div>
        </div>
        <div className="stat-tile">
          <Star className="stat-tile-icon" />
          <div className="stat-tile-value">{avg_rating != null ? avg_rating : '—'}</div>
          <div className="stat-tile-label">
            Voto medio{rated_count ? ` · ${rated_count} votati` : ''}
          </div>
        </div>
      </div>

      <div className="stats-grid">
        {/* Generi */}
        <div className="stats-card">
          <h3 className="stats-card-title">Generi più visti</h3>
          {genres.length === 0 ? (
            <p className="stats-empty">Nessun genere registrato.</p>
          ) : (
            <div className="bar-list">
              {genres.map((g) => (
                <div className="bar-row" key={g.genre_id}>
                  <span className="bar-label" title={genreName(g.genre_id)}>{genreName(g.genre_id)}</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${(g.count / maxGenre) * 100}%` }} />
                  </div>
                  <span className="bar-value">{g.count}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Top rated */}
        {top_rated && (
          <div className="stats-card">
            <h3 className="stats-card-title">Il tuo preferito</h3>
            <button
              className="top-rated"
              onClick={() => setSelectedItem({ ...top_rated, id: top_rated.tmdb_id })}
            >
              {posterUrl(top_rated.poster_path) ? (
                <img className="top-rated-poster" src={posterUrl(top_rated.poster_path)} alt={top_rated.title} />
              ) : (
                <div className="top-rated-poster top-rated-noposter">{top_rated.title}</div>
              )}
              <div className="top-rated-info">
                <Trophy size={18} className="top-rated-trophy" />
                <div className="top-rated-title">{top_rated.title}</div>
                <div className="top-rated-rating">
                  <Star size={14} fill="currentColor" /> {top_rated.rating}/10
                </div>
              </div>
            </button>
          </div>
        )}
      </div>

      {/* Timeline */}
      <div className="stats-card">
        <h3 className="stats-card-title">Aggiunte negli ultimi 12 mesi</h3>
        <div className="timeline">
          {timeline.map((t) => (
            <div className="timeline-col" key={t.month} title={`${t.count} nel mese`}>
              <div className="timeline-bar-wrap">
                <div
                  className="timeline-bar"
                  style={{ height: `${(t.count / maxMonth) * 100}%` }}
                />
              </div>
              <span className="timeline-count">{t.count || ''}</span>
              <span className="timeline-label">{monthLabel(t.month)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="stats-grid">
        {/* Distribuzione dei voti personali */}
        {rated_count > 0 && (
          <div className="stats-card">
            <h3 className="stats-card-title">Come voti</h3>
            <div className="timeline">
              {(rating_distribution || []).map((r) => (
                <div className="timeline-col" key={r.rating} title={`${r.count} titoli con voto ${r.rating}`}>
                  <div className="timeline-bar-wrap">
                    <div
                      className="timeline-bar"
                      style={{ height: `${(r.count / maxRatingBar) * 100}%` }}
                    />
                  </div>
                  <span className="timeline-count">{r.count || ''}</span>
                  <span className="timeline-label">{r.rating}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Decenni d'uscita */}
        {decades && decades.length > 0 && (
          <div className="stats-card">
            <h3 className="stats-card-title">Da che epoca guardi</h3>
            <div className="bar-list">
              {decades.map((d) => (
                <div className="bar-row" key={d.decade}>
                  <span className="bar-label">{d.decade}s</span>
                  <div className="bar-track">
                    <div className="bar-fill" style={{ width: `${(d.count / maxDecade) * 100}%` }} />
                  </div>
                  <span className="bar-value">{d.count}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </>
  );
}
