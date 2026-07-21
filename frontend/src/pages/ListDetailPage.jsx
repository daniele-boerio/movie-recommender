import { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, Trash2, Pencil, Check, X, UserPlus, LogOut, Users } from 'lucide-react';
import { api } from '../api';
import { useApp } from '../App';
import { useAuth } from '../AuthContext';
import MediaCard from '../components/MediaCard';

export default function ListDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { addToast } = useApp();
  const { user } = useAuth();
  const [list, setList] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [editing, setEditing] = useState(false);
  const [name, setName] = useState('');
  const [invite, setInvite] = useState('');

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

  const addMember = async (e) => {
    e.preventDefault();
    const u = invite.trim();
    if (!u) return;
    try {
      await api.addListMember(id, u);
      setInvite('');
      addToast(`Invitato ${u}`);
      load();
    } catch (err) {
      addToast(err.message || 'Errore');
    }
  };

  const removeMember = async (memberId) => {
    try {
      await api.removeListMember(id, memberId);
      load();
    } catch {
      addToast('Errore');
    }
  };

  const leave = async () => {
    try {
      await api.removeListMember(id, user.id);
      addToast('Hai lasciato la lista');
      navigate('/lists');
    } catch {
      addToast('Errore');
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

  const shared = list.is_owner ? list.members.length > 0 : true;

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
              {list.is_owner && (
                <button className="icon-btn" title="Rinomina" onClick={() => setEditing(true)}>
                  <Pencil size={16} />
                </button>
              )}
            </h1>
          )}
          <p className="page-subtitle">
            {list.items.length} titol{list.items.length === 1 ? 'o' : 'i'}
            {!list.is_owner && ` · di ${list.owner}`}
          </p>
        </div>
        {list.is_owner ? (
          <button className="btn btn-danger" onClick={removeList}>
            <Trash2 size={15} /> Elimina lista
          </button>
        ) : (
          <button className="btn btn-secondary" onClick={leave}>
            <LogOut size={15} /> Lascia la lista
          </button>
        )}
      </div>

      {/* Membri della lista condivisa */}
      {(shared || list.is_owner) && (
        <div className="members-box">
          <div className="members-head"><Users size={15} /> Condivisa</div>
          <div className="members-chips">
            <span className="member-chip owner">{list.owner} (proprietario)</span>
            {list.members.map((m) => (
              <span className="member-chip" key={m.id}>
                {m.username}
                {list.is_owner && (
                  <button className="member-remove" title="Rimuovi" onClick={() => removeMember(m.id)}>
                    <X size={12} />
                  </button>
                )}
              </span>
            ))}
          </div>
          {list.is_owner && (
            <form className="members-invite" onSubmit={addMember}>
              <input
                className="auth-input"
                placeholder="Invita per username…"
                value={invite}
                onChange={(e) => setInvite(e.target.value)}
              />
              <button className="btn btn-secondary" type="submit" disabled={!invite.trim()}>
                <UserPlus size={15} /> Invita
              </button>
            </form>
          )}
        </div>
      )}

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
