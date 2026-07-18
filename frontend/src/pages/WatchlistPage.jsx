import { useState, useMemo } from 'react';
import { Bookmark, Search } from 'lucide-react';
import { useApp } from '../App';
import MediaCard from '../components/MediaCard';

export default function WatchlistPage() {
  const { watchlistMap } = useApp();
  const [filter, setFilter] = useState('all');
  const [sortBy, setSortBy] = useState('added'); // added | title
  const [searchQ, setSearchQ] = useState('');

  const items = useMemo(() => {
    let list = Object.values(watchlistMap);

    if (filter !== 'all') {
      list = list.filter((it) => it.media_type === filter);
    }

    if (searchQ.trim()) {
      const q = searchQ.toLowerCase();
      list = list.filter((it) => it.title?.toLowerCase().includes(q));
    }

    if (sortBy === 'title') {
      list.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    }
    // "added" → ordine di default della mappa (desc per added_at)

    return list;
  }, [watchlistMap, filter, sortBy, searchQ]);

  const totalMovies = Object.values(watchlistMap).filter((it) => it.media_type === 'movie').length;
  const totalTv = Object.values(watchlistMap).filter((it) => it.media_type === 'tv').length;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Da vedere</h1>
        <p className="page-subtitle">
          {totalMovies} film · {totalTv} serie TV
        </p>
      </div>

      {Object.keys(watchlistMap).length === 0 ? (
        <div className="empty-state">
          <Bookmark className="empty-state-icon" />
          <h3>Nessun titolo da vedere</h3>
          <p>Aggiungi film e serie che vuoi guardare dal dettaglio di un titolo, con il bottone "Da vedere"</p>
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
