import { useEffect, useMemo, useState } from 'react';
import { CalendarDays, Film, Tv } from 'lucide-react';
import { api, posterUrl } from '../api';
import { useApp } from '../App';

const MONTHS_IT = [
  'Gennaio', 'Febbraio', 'Marzo', 'Aprile', 'Maggio', 'Giugno',
  'Luglio', 'Agosto', 'Settembre', 'Ottobre', 'Novembre', 'Dicembre',
];

// "2026-08-01" → { day: "1", weekday: "sab" }
const fmtDay = (iso) => {
  const d = new Date(iso + 'T00:00:00');
  return {
    day: d.getDate(),
    weekday: d.toLocaleDateString('it-IT', { weekday: 'short' }),
  };
};

export default function CalendarPage() {
  const { setSelectedItem } = useApp();
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.getCalendar()
      .then((d) => setEvents(d.events || []))
      .catch(() => setEvents([]))
      .finally(() => setLoading(false));
  }, []);

  // Raggruppa per "mese anno", mantenendo l'ordine cronologico già dato dal backend.
  const groups = useMemo(() => {
    const out = [];
    for (const ev of events) {
      const [y, m] = ev.date.split('-');
      const key = `${y}-${m}`;
      let g = out.find((x) => x.key === key);
      if (!g) {
        g = { key, label: `${MONTHS_IT[parseInt(m, 10) - 1]} ${y}`, items: [] };
        out.push(g);
      }
      g.items.push(ev);
    }
    return out;
  }, [events]);

  if (loading) return <div className="spinner" />;

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">In arrivo</h1>
        <p className="page-subtitle">
          Uscite e nuovi episodi dei titoli nella tua lista "Da vedere"
        </p>
      </div>

      {events.length === 0 ? (
        <div className="empty-state">
          <CalendarDays className="empty-state-icon" />
          <h3>Niente in programma</h3>
          <p>
            Aggiungi film in uscita o serie in corso alla tua watchlist: le prossime date
            compariranno qui.
          </p>
        </div>
      ) : (
        groups.map((g) => (
          <div className="cal-group" key={g.key}>
            <h2 className="cal-month">{g.label}</h2>
            <div className="cal-list">
              {g.items.map((ev) => {
                const d = fmtDay(ev.date);
                return (
                  <button
                    className="cal-row"
                    key={`${ev.tmdb_id}-${ev.media_type}-${ev.date}`}
                    onClick={() => setSelectedItem({ ...ev, id: ev.tmdb_id })}
                  >
                    <div className="cal-date">
                      <span className="cal-date-day">{d.day}</span>
                      <span className="cal-date-wd">{d.weekday}</span>
                    </div>
                    {posterUrl(ev.poster_path, 'w92') ? (
                      <img className="cal-poster" src={posterUrl(ev.poster_path, 'w92')} alt="" />
                    ) : (
                      <div className="cal-poster cal-poster-empty" />
                    )}
                    <div className="cal-info">
                      <div className="cal-title">{ev.title}</div>
                      <div className="cal-label">
                        {ev.media_type === 'tv' ? <Tv size={13} /> : <Film size={13} />}
                        {ev.label}
                      </div>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        ))
      )}
    </>
  );
}
