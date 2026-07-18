import { useState, useEffect, useRef } from 'react';
import { Search, TrendingUp, SlidersHorizontal, X } from 'lucide-react';
import { api } from '../api';
import MediaCard from '../components/MediaCard';

const SORTS = [
  { key: 'popularity.desc', label: 'Più popolari' },
  { key: 'vote_average.desc', label: 'Voto più alto' },
  { key: 'date.desc', label: 'Più recenti' },
];

const VOTE_OPTIONS = [0, 5, 6, 7, 8, 9];

export default function DiscoverPage({ searchMode = false }) {
  const [query, setQuery] = useState('');
  const [mediaFilter, setMediaFilter] = useState('all');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const searchTimeout = useRef(null);

  // Filtri avanzati
  const [showFilters, setShowFilters] = useState(false);
  const [genresByType, setGenresByType] = useState({ movie: [], tv: [] });
  const [selectedGenres, setSelectedGenres] = useState([]);
  const [yearFrom, setYearFrom] = useState('');
  const [yearTo, setYearTo] = useState('');
  const [voteMin, setVoteMin] = useState(0);
  const [sortBy, setSortBy] = useState('popularity.desc');

  // discover vuole un tipo concreto: "Tutti" ripiega su film, "Anime" è tv giapponese.
  const effectiveType = mediaFilter === 'anime' ? 'tv' : mediaFilter === 'all' ? 'movie' : mediaFilter;
  const genresForType = effectiveType === 'tv' ? genresByType.tv : genresByType.movie;

  const filtersActive =
    selectedGenres.length > 0 || !!yearFrom || !!yearTo || voteMin > 0 || sortBy !== 'popularity.desc';

  const isAnime = (it) => (it.genre_ids || []).includes(16) && it.original_language === 'ja';
  const yearOf = (it) => {
    const d = it.release_date || it.first_air_date || '';
    return d ? parseInt(d.slice(0, 4), 10) : null;
  };
  const genreName = (id) => {
    const all = [...(genresByType.movie || []), ...(genresByType.tv || [])];
    return all.find((g) => g.id === id)?.name || `#${id}`;
  };

  // Carica i generi una volta sola (film + serie).
  useEffect(() => {
    Promise.all([api.genres('movie'), api.genres('tv')])
      .then(([m, t]) => setGenresByType({ movie: m.genres || [], tv: t.genres || [] }))
      .catch(() => {});
  }, []);

  // Un solo effetto orchestra tutto: query (con debounce), tipo, o filtri.
  useEffect(() => {
    clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(() => load(1, false), query.trim() ? 400 : 0);
    return () => clearTimeout(searchTimeout.current);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [query, mediaFilter, selectedGenres, yearFrom, yearTo, voteMin, sortBy]);

  // I filtri genere/anno/voto applicati lato client (sui risultati di una ricerca testuale).
  const applyClientFilters = (list) => {
    let out = list;
    if (selectedGenres.length) {
      out = out.filter((it) => (it.genre_ids || []).some((g) => selectedGenres.includes(g)));
    }
    if (yearFrom) out = out.filter((it) => { const y = yearOf(it); return y != null && y >= +yearFrom; });
    if (yearTo) out = out.filter((it) => { const y = yearOf(it); return y != null && y <= +yearTo; });
    if (voteMin > 0) out = out.filter((it) => (it.vote_average || 0) >= voteMin);
    return clientSort(out);
  };

  const clientSort = (list) => {
    const arr = [...list];
    if (sortBy === 'vote_average.desc') arr.sort((a, b) => (b.vote_average || 0) - (a.vote_average || 0));
    else if (sortBy === 'date.desc') arr.sort((a, b) => (yearOf(b) || 0) - (yearOf(a) || 0));
    else arr.sort((a, b) => (b.popularity || 0) - (a.popularity || 0));
    return arr;
  };

  const buildDiscoverParams = (type, p) => {
    const params = {
      sort_by: sortBy === 'date.desc'
        ? `${type === 'tv' ? 'first_air_date' : 'primary_release_date'}.desc`
        : sortBy,
      page: p,
    };
    const genres = [...selectedGenres];
    if (mediaFilter === 'anime') {
      params.with_original_language = 'ja';
      if (!genres.includes(16)) genres.push(16);
    }
    if (genres.length) params.with_genres = genres.join('|'); // '|' = OR su TMDB
    if (yearFrom) params.year_from = +yearFrom;
    if (yearTo) params.year_to = +yearTo;
    if (voteMin > 0) params.vote_min = voteMin;
    return params;
  };

  async function load(p = 1, append = false) {
    setLoading(true);
    try {
      let list = [];
      let total = 1;

      if (query.trim()) {
        // Ricerca testuale: TMDB non filtra, quindi i filtri li applichiamo noi.
        const type = mediaFilter === 'all' ? 'multi' : mediaFilter === 'anime' ? 'tv' : mediaFilter;
        const data = await api.search(query, type, p);
        let raw = data.results || [];
        if (mediaFilter === 'anime') raw = raw.filter(isAnime);
        list = applyClientFilters(raw);
        total = data.total_pages || 1;
      } else if (filtersActive) {
        const data = await api.discover(effectiveType, buildDiscoverParams(effectiveType, p));
        list = data.results || [];
        total = data.total_pages || 1;
      } else if (searchMode) {
        // Cerca senza testo e senza filtri: niente da mostrare.
        setResults([]);
        setTotalPages(1);
        setLoading(false);
        return;
      } else if (mediaFilter === 'anime') {
        const data = await api.discover('tv', {
          with_genres: 16, with_original_language: 'ja', sort_by: 'popularity.desc', page: p,
        });
        list = data.results || [];
        total = data.total_pages || 1;
      } else {
        const data = await api.trending(mediaFilter === 'all' ? 'all' : mediaFilter, p);
        list = data.results || [];
        total = data.total_pages || 1;
      }

      setResults((prev) => (append ? [...prev, ...list] : list));
      setTotalPages(total);
      setPage(p);
    } catch {
      if (!append) setResults([]);
    } finally {
      setLoading(false);
    }
  }

  const toggleGenre = (id) =>
    setSelectedGenres((prev) => (prev.includes(id) ? prev.filter((g) => g !== id) : [...prev, id]));

  const resetFilters = () => {
    setSelectedGenres([]);
    setYearFrom('');
    setYearTo('');
    setVoteMin(0);
    setSortBy('popularity.desc');
  };

  const changeMedia = (key) => {
    setMediaFilter(key);
    setSelectedGenres([]); // gli id genere di film e serie sono diversi
  };

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">{searchMode ? 'Cerca' : 'Scopri'}</h1>
        <p className="page-subtitle">
          {searchMode
            ? 'Trova film, serie TV e anime da aggiungere alla tua lista'
            : 'I titoli più popolari — o filtra per trovare qualcosa di preciso'}
        </p>
      </div>

      {/* Search bar */}
      <div className="search-bar">
        <Search className="search-icon" />
        <input
          type="text"
          placeholder="Cerca film, serie TV o anime..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus={searchMode}
        />
      </div>

      {/* Tabs + toggle filtri */}
      <div className="discover-controls">
        <div className="filter-tabs">
          {[
            { key: 'all', label: 'Tutti' },
            { key: 'movie', label: 'Film' },
            { key: 'tv', label: 'Serie TV' },
            { key: 'anime', label: 'Anime' },
          ].map((tab) => (
            <button
              key={tab.key}
              className={`filter-tab ${mediaFilter === tab.key ? 'active' : ''}`}
              onClick={() => changeMedia(tab.key)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        <button
          className={`btn btn-secondary filter-toggle ${filtersActive ? 'has-active' : ''}`}
          onClick={() => setShowFilters((s) => !s)}
        >
          <SlidersHorizontal size={15} />
          Filtri{filtersActive ? ` · ${selectedGenres.length + (yearFrom || yearTo ? 1 : 0) + (voteMin > 0 ? 1 : 0)}` : ''}
        </button>
      </div>

      {/* Pannello filtri */}
      {showFilters && (
        <div className="filter-panel">
          <div className="filter-field">
            <label>Generi{mediaFilter === 'all' ? ' (film)' : ''}</label>
            <div className="genre-chips">
              {genresForType.map((g) => (
                <button
                  key={g.id}
                  className={`genre-chip ${selectedGenres.includes(g.id) ? 'selected' : ''}`}
                  onClick={() => toggleGenre(g.id)}
                >
                  {g.name}
                </button>
              ))}
            </div>
          </div>

          <div className="filter-row">
            <div className="filter-field">
              <label>Anno</label>
              <div className="year-range">
                <input type="number" placeholder="da" min="1900" max="2100"
                  value={yearFrom} onChange={(e) => setYearFrom(e.target.value)} />
                <span>–</span>
                <input type="number" placeholder="a" min="1900" max="2100"
                  value={yearTo} onChange={(e) => setYearTo(e.target.value)} />
              </div>
            </div>

            <div className="filter-field">
              <label>Voto minimo</label>
              <select value={voteMin} onChange={(e) => setVoteMin(+e.target.value)} className="filter-select">
                {VOTE_OPTIONS.map((v) => (
                  <option key={v} value={v}>{v === 0 ? 'Qualsiasi' : `${v}+`}</option>
                ))}
              </select>
            </div>

            <div className="filter-field">
              <label>Ordina per</label>
              <select value={sortBy} onChange={(e) => setSortBy(e.target.value)} className="filter-select">
                {SORTS.map((s) => (
                  <option key={s.key} value={s.key}>{s.label}</option>
                ))}
              </select>
            </div>
          </div>

          {filtersActive && (
            <button className="filter-reset" onClick={resetFilters}>
              <X size={14} /> Azzera filtri
            </button>
          )}
        </div>
      )}

      {/* Chip filtri attivi */}
      {filtersActive && (
        <div className="active-filters">
          {selectedGenres.map((id) => (
            <button key={id} className="active-chip" onClick={() => toggleGenre(id)}>
              {genreName(id)} <X size={12} />
            </button>
          ))}
          {(yearFrom || yearTo) && (
            <button className="active-chip" onClick={() => { setYearFrom(''); setYearTo(''); }}>
              {yearFrom || '…'}–{yearTo || '…'} <X size={12} />
            </button>
          )}
          {voteMin > 0 && (
            <button className="active-chip" onClick={() => setVoteMin(0)}>
              Voto {voteMin}+ <X size={12} />
            </button>
          )}
          {sortBy !== 'popularity.desc' && (
            <button className="active-chip" onClick={() => setSortBy('popularity.desc')}>
              {SORTS.find((s) => s.key === sortBy)?.label} <X size={12} />
            </button>
          )}
        </div>
      )}

      {/* Results */}
      {loading && results.length === 0 ? (
        <div className="spinner" />
      ) : results.length === 0 ? (
        <div className="empty-state">
          {query || filtersActive ? (
            <>
              <Search className="empty-state-icon" />
              <h3>Nessun risultato</h3>
              <p>Prova a cambiare ricerca o filtri</p>
            </>
          ) : (
            <>
              <TrendingUp className="empty-state-icon" />
              <h3>Cerca qualcosa</h3>
              <p>Digita il titolo di un film, una serie TV o un anime</p>
            </>
          )}
        </div>
      ) : (
        <>
          <div className="media-grid">
            {results.map((item) => (
              <MediaCard key={`${item.id}-${item.media_type}`} item={item} />
            ))}
          </div>

          {page < totalPages && (
            <div style={{ textAlign: 'center', marginTop: 32 }}>
              <button className="btn btn-secondary" onClick={() => load(page + 1, true)} disabled={loading}>
                {loading ? 'Carico…' : 'Carica altri risultati'}
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}
