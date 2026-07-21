import { useState, useMemo } from 'react';
import { Link } from 'react-router-dom';
import { BookmarkCheck, Search, Upload } from 'lucide-react';
import { useApp } from '../App';
import MediaCard from '../components/MediaCard';

export default function WatchedPage() {
  const { watchedMap } = useApp();
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('added'); // added | rating | title
  const [searchQ, setSearchQ] = useState('');

  const items = useMemo(() => {
    let list = Object.values(watchedMap);

    // Filter by type
    if (filter !== 'all') {
      list = list.filter((it) => it.media_type === filter);
    }

    // Search
    if (searchQ.trim()) {
      const q = searchQ.toLowerCase();
      list = list.filter((it) => it.title?.toLowerCase().includes(q));
    }

    // Sort
    if (sortBy === 'rating') {
      list.sort((a, b) => (b.rating || 0) - (a.rating || 0));
    } else if (sortBy === 'title') {
      list.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    }
    // "added" → default order from watchedMap (desc by added_at)

    return list;
  }, [watchedMap, filter, sortBy, searchQ]);

  const totalMovies = Object.values(watchedMap).filter((it) => it.media_type === 'movie').length;
  const totalTv = Object.values(watchedMap).filter((it) => it.media_type === 'tv').length;

  return (
    <>
      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
        <div>
          <h1 className="page-title">I miei visti</h1>
          <p className="page-subtitle">
            {totalMovies} film · {totalTv} serie TV
          </p>
        </div>
        <Link to="/import" className="btn btn-secondary">
          <Upload size={15} /> Importa CSV
        </Link>
      </div>

      {Object.keys(watchedMap).length === 0 ? (
        <div className="empty-state">
          <BookmarkCheck className="empty-state-icon" />
          <h3>La tua lista è vuota</h3>
          <p>Vai alla sezione Scopri o Cerca per aggiungere film e serie TV che hai già visto</p>
          <Link to="/import" className="btn btn-secondary" style={{ marginTop: 16 }}>
            <Upload size={15} /> Importa da CSV
          </Link>
        </div>
      ) : (
        <>
          {/* Controls */}
          <div style={{ display: 'flex', gap: 12, marginBottom: 24, flexWrap: 'wrap', alignItems: 'center' }}>
            <div className="search-bar" style={{ marginBottom: 0, maxWidth: 320 }}>
              <Search className="search-icon" />
              <input
                type="text"
                placeholder="Filtra per titolo..."
                value={searchQ}
                onChange={(e) => setSearchQ(e.target.value)}
              />
            </div>

            <div className="filter-tabs">
              {[
                { key: 'all', label: 'Tutti' },
                { key: 'movie', label: 'Film' },
                { key: 'tv', label: 'Serie' },
              ].map((tab) => (
                <button
                  key={tab.key}
                  className={`filter-tab ${filter === tab.key ? 'active' : ''}`}
                  onClick={() => setFilter(tab.key)}
                >
                  {tab.label}
                </button>
              ))}
            </div>

            <select
              value={sortBy}
              onChange={(e) => setSortBy(e.target.value)}
              style={{
                padding: '8px 12px',
                background: 'var(--bg-surface)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--text-primary)',
                fontSize: '0.85rem',
              }}
            >
              <option value="added">Ultimi aggiunti</option>
              <option value="rating">Mio voto</option>
              <option value="title">Titolo A-Z</option>
            </select>
          </div>

          {items.length === 0 ? (
            <div className="empty-state">
              <Search className="empty-state-icon" />
              <h3>Nessun risultato</h3>
              <p>Prova a cambiare i filtri</p>
            </div>
          ) : (
            <div className="media-grid">
              {items.map((item) => (
                <MediaCard
                  key={`${item.tmdb_id}-${item.media_type}`}
                  item={{ ...item, id: item.tmdb_id }}
                />
              ))}
            </div>
          )}
        </>
      )}
    </>
  );
}
