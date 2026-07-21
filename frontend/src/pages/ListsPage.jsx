import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ListChecks, Plus } from 'lucide-react';
import { api, posterUrl } from '../api';
import { useApp } from '../App';

export default function ListsPage() {
  const { addToast } = useApp();
  const navigate = useNavigate();
  const [lists, setLists] = useState(null);
  const [newName, setNewName] = useState('');
  const [creating, setCreating] = useState(false);

  const load = () => api.getLists().then(setLists).catch(() => setLists([]));

  useEffect(() => { load(); }, []);

  const create = async (e) => {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    setCreating(true);
    try {
      const l = await api.createList(name);
      setNewName('');
      await load();
      navigate(`/lists/${l.id}`);
    } catch {
      addToast('Errore nella creazione della lista');
    } finally {
      setCreating(false);
    }
  };

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Le mie liste</h1>
        <p className="page-subtitle">Raccolte tematiche di film e serie</p>
      </div>

      <form className="list-create" onSubmit={create}>
        <input
          className="auth-input"
          placeholder="Nome della lista (es. Film di Natale)"
          value={newName}
          onChange={(e) => setNewName(e.target.value)}
          maxLength={100}
        />
        <button className="btn btn-primary" type="submit" disabled={creating || !newName.trim()}>
          <Plus size={16} /> Crea lista
        </button>
      </form>

      {lists === null ? (
        <div className="spinner" />
      ) : lists.length === 0 ? (
        <div className="empty-state">
          <ListChecks className="empty-state-icon" />
          <h3>Nessuna lista</h3>
          <p>Crea la tua prima raccolta qui sopra, poi aggiungi titoli dal loro dettaglio.</p>
        </div>
      ) : (
        <div className="list-grid">
          {lists.map((l) => (
            <button className="list-card" key={l.id} onClick={() => navigate(`/lists/${l.id}`)}>
              <div className="list-card-covers">
                {l.preview.length > 0 ? (
                  l.preview.map((p, i) => (
                    <img key={i} src={posterUrl(p, 'w185')} alt="" />
                  ))
                ) : (
                  <div className="list-card-empty"><ListChecks size={28} /></div>
                )}
              </div>
              <div className="list-card-name">{l.name}</div>
              <div className="list-card-count">{l.count} titol{l.count === 1 ? 'o' : 'i'}</div>
            </button>
          ))}
        </div>
      )}
    </>
  );
}
