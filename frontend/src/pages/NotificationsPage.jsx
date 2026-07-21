import { useEffect, useState } from 'react';
import { Bell, Tv } from 'lucide-react';
import { api, posterUrl } from '../api';
import { useApp } from '../App';

const relTime = (iso) => {
  if (!iso) return '';
  const days = Math.floor((Date.now() - new Date(iso).getTime()) / 86400000);
  if (days <= 0) return 'oggi';
  if (days === 1) return 'ieri';
  if (days < 30) return `${days} giorni fa`;
  const months = Math.floor(days / 30);
  return months === 1 ? '1 mese fa' : `${months} mesi fa`;
};

export default function NotificationsPage() {
  const { setSelectedItem, refreshNotifications } = useApp();
  const [items, setItems] = useState(null);

  useEffect(() => {
    api.getNotifications()
      .then(setItems)
      .catch(() => setItems([]));
    // Aprendo la pagina le consideriamo lette: azzera il badge.
    api.markNotificationsRead().then(refreshNotifications).catch(() => {});
  }, [refreshNotifications]);

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Notifiche</h1>
        <p className="page-subtitle">Nuovi episodi delle serie che segui</p>
      </div>

      {items === null ? (
        <div className="spinner" />
      ) : items.length === 0 ? (
        <div className="empty-state">
          <Bell className="empty-state-icon" />
          <h3>Nessuna notifica</h3>
          <p>
            Aggiungi serie in corso alla tua lista o ai visti: ti avviseremo quando esce
            un nuovo episodio.
          </p>
        </div>
      ) : (
        <div className="notif-list">
          {items.map((n) => (
            <button
              className={`notif-row ${n.read ? '' : 'unread'}`}
              key={n.id}
              onClick={() =>
                n.tmdb_id &&
                setSelectedItem({ id: n.tmdb_id, tmdb_id: n.tmdb_id, media_type: n.media_type, title: n.title, poster_path: n.poster_path })
              }
            >
              {posterUrl(n.poster_path, 'w92') ? (
                <img className="notif-poster" src={posterUrl(n.poster_path, 'w92')} alt="" />
              ) : (
                <div className="notif-poster notif-poster-empty"><Tv size={18} /></div>
              )}
              <div className="notif-info">
                <div className="notif-title">{n.title}</div>
                <div className="notif-body">{n.body}</div>
                <div className="notif-time">{relTime(n.created_at)}</div>
              </div>
              {!n.read && <span className="notif-dot" />}
            </button>
          ))}
        </div>
      )}
    </>
  );
}
