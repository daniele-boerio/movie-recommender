import { useEffect, useMemo, useState } from 'react';
import { ChevronDown, ChevronRight, Check } from 'lucide-react';
import { api } from '../api';
import { useApp } from '../App';

// Chiave compatta di un episodio nel Set del progresso: "stagione-episodio".
const key = (s, e) => `${s}-${e}`;

export default function EpisodeTracker({ tmdbId, seasons, watched, onMarkSeriesWatched }) {
  const { addToast } = useApp();
  const [watchedSet, setWatchedSet] = useState(() => new Set());
  const [openSeason, setOpenSeason] = useState(null);
  const [episodes, setEpisodes] = useState({});     // season_number -> [episodi TMDB]
  const [loadingSeason, setLoadingSeason] = useState(null);

  // Escludiamo gli "Speciali" (stagione 0) e le stagioni ancora senza episodi.
  const realSeasons = useMemo(
    () => (seasons || []).filter((s) => s.season_number >= 1 && s.episode_count > 0),
    [seasons]
  );

  const totalEpisodes = useMemo(
    () => realSeasons.reduce((sum, s) => sum + (s.episode_count || 0), 0),
    [realSeasons]
  );

  useEffect(() => {
    let alive = true;
    api.getProgress(tmdbId)
      .then((rows) => {
        if (alive) setWatchedSet(new Set(rows.map((r) => key(r.season_number, r.episode_number))));
      })
      .catch(() => {});
    return () => { alive = false; };
  }, [tmdbId]);

  if (!realSeasons.length) return null;

  const watchedCount = watchedSet.size;
  const pct = totalEpisodes ? Math.min(100, (watchedCount / totalEpisodes) * 100) : 0;
  const complete = totalEpisodes > 0 && watchedCount >= totalEpisodes;

  const seasonWatched = (sn) => {
    let c = 0;
    watchedSet.forEach((k) => { if (k.startsWith(`${sn}-`)) c++; });
    return c;
  };

  const toggleSeasonOpen = async (s) => {
    const sn = s.season_number;
    if (openSeason === sn) { setOpenSeason(null); return; }
    setOpenSeason(sn);
    if (!episodes[sn]) {
      setLoadingSeason(sn);
      try {
        const data = await api.tvSeason(tmdbId, sn);
        setEpisodes((prev) => ({ ...prev, [sn]: data.episodes || [] }));
      } catch {
        setEpisodes((prev) => ({ ...prev, [sn]: [] }));
      } finally {
        setLoadingSeason(null);
      }
    }
  };

  const toggleEpisode = async (sn, ep) => {
    const k = key(sn, ep);
    const on = watchedSet.has(k);
    // Update ottimistico: la UI risponde subito, la rete conferma dopo.
    setWatchedSet((prev) => {
      const next = new Set(prev);
      on ? next.delete(k) : next.add(k);
      return next;
    });
    try {
      if (on) await api.unmarkEpisode(tmdbId, sn, ep);
      else await api.markEpisode(tmdbId, sn, ep);
    } catch {
      setWatchedSet((prev) => {
        const next = new Set(prev);
        on ? next.add(k) : next.delete(k);
        return next;
      });
      addToast('Errore nel salvataggio', 'error');
    }
  };

  const toggleSeason = async (s) => {
    const sn = s.season_number;
    const nums = Array.from({ length: s.episode_count }, (_, i) => i + 1);
    const allOn = nums.every((n) => watchedSet.has(key(sn, n)));
    const snapshot = new Set(watchedSet);

    setWatchedSet((prev) => {
      const next = new Set(prev);
      nums.forEach((n) => (allOn ? next.delete(key(sn, n)) : next.add(key(sn, n))));
      return next;
    });
    try {
      if (allOn) {
        await api.unmarkSeason(tmdbId, sn);
        addToast(`Stagione ${sn}: episodi tolti`);
      } else {
        await api.markSeason(tmdbId, sn, nums);
        addToast(`Stagione ${sn} segnata come vista ✓`);
      }
    } catch {
      setWatchedSet(snapshot);
      addToast('Errore nel salvataggio', 'error');
    }
  };

  return (
    <div className="ep-tracker">
      <div className="ep-tracker-head">
        <span className="ep-tracker-title">Episodi visti</span>
        <span className="ep-progress-label">{Math.min(watchedCount, totalEpisodes)}/{totalEpisodes}</span>
      </div>
      <div className="ep-progress-bar">
        <div className="ep-progress-fill" style={{ width: `${pct}%` }} />
      </div>

      {complete && !watched && (
        <button className="btn btn-primary ep-complete-btn" onClick={onMarkSeriesWatched}>
          <Check size={16} /> Hai visto tutto — segna la serie come vista
        </button>
      )}

      <div className="ep-seasons">
        {realSeasons.map((s) => {
          const sn = s.season_number;
          const sw = seasonWatched(sn);
          const seasonComplete = sw >= s.episode_count;
          const open = openSeason === sn;
          return (
            <div className="ep-season" key={sn}>
              <div className="ep-season-head">
                <button className="ep-season-toggle" onClick={() => toggleSeasonOpen(s)}>
                  {open ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
                  <span className="ep-season-name">{s.name || `Stagione ${sn}`}</span>
                  <span className={`ep-season-count ${seasonComplete ? 'done' : ''}`}>
                    {sw}/{s.episode_count}
                  </span>
                </button>
                <button className="ep-season-mark" onClick={() => toggleSeason(s)}>
                  {seasonComplete ? 'Azzera' : 'Segna tutta'}
                </button>
              </div>

              {open && (
                <div className="ep-list">
                  {loadingSeason === sn ? (
                    <div className="ep-loading">Carico gli episodi…</div>
                  ) : (episodes[sn] || []).length === 0 ? (
                    <div className="ep-loading">Nessun episodio disponibile</div>
                  ) : (
                    (episodes[sn] || []).map((ep) => {
                      const on = watchedSet.has(key(sn, ep.episode_number));
                      return (
                        <button
                          key={ep.id || key(sn, ep.episode_number)}
                          className={`ep-row ${on ? 'on' : ''}`}
                          onClick={() => toggleEpisode(sn, ep.episode_number)}
                        >
                          <span className="ep-check">{on && <Check size={13} />}</span>
                          <span className="ep-num">{ep.episode_number}</span>
                          <span className="ep-name">{ep.name}</span>
                        </button>
                      );
                    })
                  )}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
