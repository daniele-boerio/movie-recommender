import { useState, useEffect } from 'react';
import { Sparkles, RefreshCw } from 'lucide-react';
import { api } from '../api';
import { useApp } from '../App';
import MediaCard from '../components/MediaCard';

export default function RecommendationsPage() {
  const { watchedMap } = useApp();
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [filter, setFilter] = useState('all');

  const watchedCount = Object.keys(watchedMap).length;

  async function loadRecs() {
    if (watchedCount === 0) return;
    setLoading(true);
    try {
      const data = await api.getRecommendations(40);
      setResults(data.results || []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadRecs();
  }, [watchedCount]);

  const filtered = filter === 'all'
    ? results
    : results.filter((r) => r.media_type === filter);

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
          <div style={{ display: 'flex', gap: 12, marginBottom: 24, alignItems: 'center', flexWrap: 'wrap' }}>
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

            <button
              className="btn btn-secondary"
              onClick={loadRecs}
              disabled={loading}
            >
              <RefreshCw size={16} className={loading ? 'spinning' : ''} />
              Aggiorna
            </button>
          </div>

          {loading ? (
            <div className="spinner" />
          ) : filtered.length === 0 ? (
            <div className="empty-state">
              <Sparkles className="empty-state-icon" />
              <h3>Nessun consiglio al momento</h3>
              <p>Aggiungi più titoli alla tua lista per migliorare i consigli</p>
            </div>
          ) : (
            <div className="media-grid">
              {filtered.map((item) => (
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
