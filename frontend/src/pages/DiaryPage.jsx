import { useMemo } from 'react';
import { BookOpen, Star } from 'lucide-react';
import { posterUrl } from '../api';
import { useApp } from '../App';

// "2026-07-01" → "1 lug 2026"; se manca, usa la data ISO di added_at.
const MESI = ['gen', 'feb', 'mar', 'apr', 'mag', 'giu', 'lug', 'ago', 'set', 'ott', 'nov', 'dic'];
const fmt = (it) => {
  const raw = it.watched_on || (it.added_at ? it.added_at.slice(0, 10) : '');
  if (!raw) return '';
  const [y, m, d] = raw.split('-');
  return `${parseInt(d, 10)} ${MESI[parseInt(m, 10) - 1]} ${y}`;
};

export default function DiaryPage() {
  const { watchedMap, setSelectedItem } = useApp();

  // Entrano nel diario i titoli con una data di visione o una recensione; gli altri
  // visti "nudi" restano nella pagina Visti. Ordine cronologico decrescente.
  const entries = useMemo(() => {
    const key = (it) => it.watched_on || it.added_at || '';
    return Object.values(watchedMap)
      .filter((it) => it.watched_on || it.review)
      .sort((a, b) => key(b).localeCompare(key(a)));
  }, [watchedMap]);

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Diario</h1>
        <p className="page-subtitle">Cosa hai visto, quando, e cosa ne pensavi</p>
      </div>

      {entries.length === 0 ? (
        <div className="empty-state">
          <BookOpen className="empty-state-icon" />
          <h3>Il diario è vuoto</h3>
          <p>
            Apri un titolo che hai visto e aggiungi una data di visione o una recensione:
            comparirà qui in ordine di tempo.
          </p>
        </div>
      ) : (
        <div className="diary-list">
          {entries.map((it) => (
            <div className="diary-entry" key={`${it.tmdb_id}-${it.media_type}`}>
              <div className="diary-date">{fmt(it)}</div>
              <button
                className="diary-card"
                onClick={() => setSelectedItem({ ...it, id: it.tmdb_id })}
              >
                {posterUrl(it.poster_path, 'w92') ? (
                  <img className="diary-poster" src={posterUrl(it.poster_path, 'w92')} alt="" />
                ) : (
                  <div className="diary-poster diary-poster-empty" />
                )}
                <div className="diary-body">
                  <div className="diary-title">
                    {it.title}
                    {it.rating != null && (
                      <span className="diary-rating"><Star size={12} fill="currentColor" /> {it.rating}/10</span>
                    )}
                  </div>
                  {it.review && <p className="diary-review-text">{it.review}</p>}
                </div>
              </button>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
