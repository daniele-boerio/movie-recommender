import { useState, useEffect } from 'react';
import { Sparkles, RefreshCw, SlidersHorizontal, X } from 'lucide-react';
import { api } from '../api';
import { useApp } from '../App';
import MediaCard from '../components/MediaCard';

const VOTE_OPTIONS = [0, 6, 7, 8];
const STORAGE_KEY = 'recFilters';

const DEFAULTS = {
  mediaType: 'all',
  excludedGenres: [],
  excludeAnime: false,
  minVote: 0,
  yearFrom: '',
  yearTo: '',
};

// I filtri sopravvivono al reload: chi non vuole i cartoni animati non li vuole nemmeno domani.
function storedFilters() {
  try {
    return { ...DEFAULTS, ...JSON.parse(localStorage.getItem(STORAGE_KEY) || '{}') };
  } catch {
    return DEFAULTS; /* localStorage non disponibile: pazienza */
  }
}

export default function RecommendationsPage() {
  const { watchedMap } = useApp();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [genres, setGenres] = useState([]);
  const [showFilters, setShowFilters] = useState(false);
  const [filters, setFilters] = useState(storedFilters);

  const watchedCount = Object.keys(watchedMap).length;
  const set = (patch) => setFilters((f) => ({ ...f, ...patch }));

  const filtersActive =
    filters.mediaType !== 'all' ||
    filters.excludedGenres.length > 0 ||
    filters.excludeAnime ||
    filters.minVote > 0 ||
    !!filters.yearFrom ||
    !!filters.yearTo;

  const genreName = (id) => genres.find((g) => g.id === id)?.name || `#${id}`;

  // Generi di film e serie in un elenco solo: qui si escludono, non si scopre.
  useEffect(() => {
    Promise.all([api.genres('movie'), api.genres('tv')])
      .then(([m, t]) => {
        const byId = new Map();
        for (const g of [...(m.genres || []), ...(t.genres || [])]) byId.set(g.id, g);
        setGenres([...byId.values()].sort((a, b) => a.name.localeCompare(b.name)));
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(filters));
    } catch {
      /* localStorage non disponibile: i filtri restano solo per questa sessione */
    }
  }, [filters]);

  async function loadRecs() {
    if (watchedCount === 0) return;
    setLoading(true);
    try {
      // I filtri vanno al backend, non applicati qui: devono togliere i candidati *prima*
      // della classifica, altrimenti restano i buchi lasciati dai titoli scartati.
      const data = await api.getRecommendations(40, {
        media_type: filters.mediaType !== 'all' ? filters.mediaType : '',
        exclude_genres: filters.excludedGenres.join(','),
        exclude_anime: filters.excludeAnime,
        min_vote: filters.minVote || '',
        year_from: filters.yearFrom,
        year_to: filters.yearTo,
      });
      setResults(data.results || []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  // Debounce: cliccare tre generi di fila non deve far ricalcolare tre volte.
  useEffect(() => {
    const t = setTimeout(loadRecs, 300);
    return () => clearTimeout(t);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [watchedCount, filters]);

  const toggleGenre = (id) =>
    set({
      excludedGenres: filters.excludedGenres.includes(id)
        ? filters.excludedGenres.filter((g) => g !== id)
        : [...filters.excludedGenres, id],
    });

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Per te</h1>
        <p className="page-subtitle">
          Consigli personalizzati basati sui {watchedCount} titoli nella tua lista
        </p>
      </div>

      {watchedCount === 0 ? (
        <div className="empty-state">
          <Sparkles className="empty-state-icon" />
          <h3>Aggiungi qualcosa alla lista</h3>
          <p>
            Quando avrai aggiunto film o serie TV alla tua lista,
            qui troverai i consigli personalizzati
          </p>
        </div>
      ) : (
        <>
          <div className="discover-controls">
            <div className="filter-tabs">
              {[
                { key: 'all', label: 'Tutti' },
                { key: 'movie', label: 'Film' },
                { key: 'tv', label: 'Serie' },
              ].map((tab) => (
                <button
                  key={tab.key}
                  className={`filter-tab ${filters.mediaType === tab.key ? 'active' : ''}`}
                  onClick={() => set({ mediaType: tab.key })}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <div style={{ display: 'flex', gap: 12 }}>
              <button
                className={`btn btn-secondary filter-toggle ${filtersActive ? 'has-active' : ''}`}
                onClick={() => setShowFilters((s) => !s)}
              >
                <SlidersHorizontal size={15} />
                Filtri
              </button>
              <button className="btn btn-secondary" onClick={loadRecs} disabled={loading}>
                <RefreshCw size={16} className={loading ? 'spinning' : ''} />
                Aggiorna
              </button>
            </div>
          </div>

          {showFilters && (
            <div className="filter-panel">
              <div className="filter-field">
                <label>Escludi generi</label>
                <div className="genre-chips">
                  {genres.map((g) => (
                    <button
                      key={g.id}
                      className={`genre-chip ${filters.excludedGenres.includes(g.id) ? 'excluded' : ''}`}
                      onClick={() => toggleGenre(g.id)}
                    >
                      {g.name}
                    </button>
                  ))}
                </div>
              </div>

              <div className="filter-row">
                <div className="filter-field">
                  <label>Escludi anche</label>
                  <div className="genre-chips">
                    <button
                      className={`genre-chip ${filters.excludeAnime ? 'excluded' : ''}`}
                      onClick={() => set({ excludeAnime: !filters.excludeAnime })}
                    >
                      Anime
                    </button>
                  </div>
                </div>

                <div className="filter-field">
                  <label>Voto minimo</label>
                  <select
                    value={filters.minVote}
                    onChange={(e) => set({ minVote: +e.target.value })}
                    className="filter-select"
                  >
                    {VOTE_OPTIONS.map((v) => (
                      <option key={v} value={v}>{v === 0 ? 'Qualsiasi' : `${v}+`}</option>
                    ))}
                  </select>
                </div>

                <div className="filter-field">
                  <label>Anno di uscita</label>
                  <div className="year-range">
                    <input type="number" placeholder="da" min="1900" max="2100"
                      value={filters.yearFrom} onChange={(e) => set({ yearFrom: e.target.value })} />
                    <span>–</span>
                    <input type="number" placeholder="a" min="1900" max="2100"
                      value={filters.yearTo} onChange={(e) => set({ yearTo: e.target.value })} />
                  </div>
                </div>
              </div>

              {filtersActive && (
                <button className="filter-reset" onClick={() => setFilters(DEFAULTS)}>
                  <X size={14} /> Azzera filtri
                </button>
              )}
            </div>
          )}

          {/* Cosa sto escludendo, senza dover riaprire il pannello */}
          {filtersActive && (
            <div className="active-filters">
              {filters.excludedGenres.map((id) => (
                <button key={id} className="active-chip excluded" onClick={() => toggleGenre(id)}>
                  No {genreName(id).toLowerCase()} <X size={12} />
                </button>
              ))}
              {filters.excludeAnime && (
                <button className="active-chip excluded" onClick={() => set({ excludeAnime: false })}>
                  No anime <X size={12} />
                </button>
              )}
              {filters.minVote > 0 && (
                <button className="active-chip" onClick={() => set({ minVote: 0 })}>
                  Voto {filters.minVote}+ <X size={12} />
                </button>
              )}
              {(filters.yearFrom || filters.yearTo) && (
                <button className="active-chip" onClick={() => set({ yearFrom: '', yearTo: '' })}>
                  {filters.yearFrom || '…'}–{filters.yearTo || '…'} <X size={12} />
                </button>
              )}
            </div>
          )}

          {loading ? (
            <div className="spinner" />
          ) : results.length === 0 ? (
            <div className="empty-state">
              <Sparkles className="empty-state-icon" />
              <h3>Nessun consiglio al momento</h3>
              <p>
                {filtersActive
                  ? 'I filtri hanno scartato tutto: prova ad allentarli'
                  : 'Aggiungi più titoli alla tua lista per migliorare i consigli'}
              </p>
            </div>
          ) : (
            <div className="media-grid">
              {results.map((item) => (
                <MediaCard
                  key={`${item.tmdb_id}-${item.media_type}`}
                  item={{ ...item, id: item.tmdb_id }}
                  showReason
                />
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
