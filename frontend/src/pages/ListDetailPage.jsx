import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Trash2, Pencil, Check, X } from 'lucide-react';
import { api } from '../api';
import { useApp } from '../App';
import MediaCard from '../components/MediaCard';

export default function ListDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { addToast } = useApp();
  const [list, setList] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState('');

  const load = () =>
    api.getList(id)
      .then((l) => { setList(l); setName(l.name); })
      .catch(() => setNotFound(true));

  useEffect(() => { load(); }, [id]);

  const saveName = async () => {
    const n = name.trim();
    if (!n) return;
    try {
      await api.renameList(id, n);
      setList((l) => ({ ...l, name: n }));
      setEditing(false);
    } catch {
      addToast('Errore nel rinominare');
    }
  };

  const removeItem = async (item) => {
    try {
      await api.removeFromList(id, item.tmdb_id, item.media_type);
      setList((l) => ({
        ...l,
        items: l.items.filter(
          (it) => !(it.tmdb_id === item.tmdb_id && it.media_type === item.media_type)
        ),
      }));
    } catch {
      addToast('Errore nella rimozione');
    }
  };

  const removeList = async () => {
    try {
      await api.deleteList(id);
      addToast('Lista eliminata');
      navigate('/lists');
    } catch {
      addToast('Errore nell\'eliminazione');
    }
  };

  if (notFound) {
    return (
      <div className="empty-state">
        <h3>Lista non trovata</h3>
        <button className="btn btn-secondary" onClick={() => navigate('/lists')}>Torna alle liste</button>
      </div>
    );
  }
  if (!list) return <div className="spinner" />;

  return (
    <>
      <button className="back-btn" onClick={() => navigate('/lists')}>
        <ArrowLeft size={16} /> Le mie liste
      </button>

      <div className="page-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 16, flexWrap: 'wrap' }}>
        <div style={{ flex: 1, minWidth: 240 }}>
          {editing ? (
            <div className="list-rename">
              <input
                className="auth-input"
                value={name}
                onChange={(e) => setName(e.target.value)}
                maxLength={100}
                autoFocus
              />
              <button className="btn btn-primary" onClick={saveName}><Check size={15} /></button>
              <button className="btn btn-secondary" onClick={() => { setEditing(false); setName(list.name); }}><X size={15} /></button>
            </div>
          ) : (
            <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              {list.name}
              <button className="icon-btn" title="Rinomina" onClick={() => setEditing(true)}>
                <Pencil size={16} />
              </button>
            </h1>
          )}
          <p className="page-subtitle">{list.items.length} titol{list.items.length === 1 ? 'o' : 'i'}</p>
        </div>
        <button className="btn btn-danger" onClick={removeList}>
          <Trash2 size={15} /> Elimina lista
        </button>
      </div>

      {list.items.length === 0 ? (
        <div className="empty-state">
          <h3>Lista vuota</h3>
          <p>Apri il dettaglio di un film o serie e usa "Aggiungi a lista".</p>
        </div>
      ) : (
        <div className="media-grid">
          {list.items.map((item) => (
            <div className="list-item-wrap" key={`${item.tmdb_id}-${item.media_type}`}>
              <button
                className="list-remove"
                title="Rimuovi dalla lista"
                onClick={(e) => { e.stopPropagation(); removeItem(item); }}
              >
                <X size={15} />
              </button>
              <MediaCard item={{ ...item, id: item.tmdb_id }} />
            </div>
          ))}
        </div>
      )}
    </>
  );
}
