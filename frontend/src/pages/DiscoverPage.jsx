import { useState, useEffect, useRef } from 'react';
import { Search, TrendingUp } from 'lucide-react';
import { api } from '../api';
import MediaCard from '../components/MediaCard';

export default function DiscoverPage({ searchMode = false }) {
  const [query, setQuery] = useState('');
  const [mediaFilter, setMediaFilter] = useState('all');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const searchTimeout = useRef(null);

  // Load trending on mount (discover mode)
  useEffect(() => {
    if (!searchMode && !query) {
      loadTrending();
    }
  }, [mediaFilter]);

  // Debounced search
  useEffect(() => {
    if (!query.trim()) {
      if (!searchMode) loadTrending();
      else {
        setResults([]);
        setTotalPages(1);
      }
      return;
    }

    clearTimeout(searchTimeout.current);
    searchTimeout.current = setTimeout(() => {
      doSearch(query, 1);
    }, 400);

    return () => clearTimeout(searchTimeout.current);
  }, [query, mediaFilter]);

  // Anime = serie TV con genere Animazione (16) e lingua originale giapponese.
  // TMDB non li classifica a parte, quindi li ricaviamo così.
  const isAnime = (it) =>
    (it.genre_ids || []).includes(16) && it.original_language === 'ja';

  async function loadTrending() {
    setLoading(true);
    try {
      let data;
      if (mediaFilter === 'anime') {
        data = await api.discover('tv', {
          with_genres: 16,
          with_original_language: 'ja',
          sort_by: 'popularity.desc',
          page: 1,
        });
      } else {
        data = await api.trending(mediaFilter === 'all' ? 'all' : mediaFilter, 1);
      }
      setResults(data.results || []);
      setTotalPages(data.total_pages || 1);
      setPage(1);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  async function doSearch(q, p = 1) {
    setLoading(true);
    try {
      let data;
      if (mediaFilter === 'anime') {
        // La ricerca TMDB non filtra gli anime: cerchiamo tra le serie e teniamo
        // solo quelle che rispondono all'euristica anime.
        data = await api.search(q, 'tv', p);
        data = { ...data, results: (data.results || []).filter(isAnime) };
      } else {
        data = await api.search(q, mediaFilter === 'all' ? 'multi' : mediaFilter, p);
      }
      setResults(data.results || []);
      setTotalPages(data.total_pages || 1);
      setPage(p);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  function loadMore() {
    if (page >= totalPages) return;
    const nextPage = page + 1;
    if (query.trim()) {
      doSearch(query, nextPage);
    }
  }

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">
          {searchMode ? 'Cerca' : 'Scopri'}
        </h1>
        <p className="page-subtitle">
          {searchMode
            ? 'Trova film e serie TV da aggiungere alla tua lista'
            : 'I titoli più popolari di questa settimana'}
        </p>
      </div>

      {/* Search bar */}
      <div className="search-bar">
        <Search className="search-icon" />
        <input
          type="text"
          placeholder="Cerca film o serie TV..."
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          autoFocus={searchMode}
        />
      </div>

      {/* Filter tabs */}
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
            onClick={() => setMediaFilter(tab.key)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Results */}
      {loading ? (
        <div className="spinner" />
      ) : results.length === 0 ? (
        <div className="empty-state">
          {query ? (
            <>
              <Search className="empty-state-icon" />
              <h3>Nessun risultato</h3>
              <p>Prova con un altro termine di ricerca</p>
            </>
          ) : (
            <>
              <TrendingUp className="empty-state-icon" />
              <h3>Cerca qualcosa</h3>
              <p>Digita il titolo di un film o una serie TV</p>
            </>
          )}
        </div>
      ) : (
        <>
          <div className="media-grid">
            {results.map((item) => (
              <MediaCard
                key={`${item.id}-${item.media_type}`}
                item={item}
              />
            ))}
          </div>

          {page < totalPages && query && (
            <div style={{ textAlign: 'center', marginTop: 32 }}>
              <button className="btn btn-secondary" onClick={loadMore}>
                Carica altri risultati
              </button>
            </div>
          )}
        </>
      )}
    </>
  );
}
