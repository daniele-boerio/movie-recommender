import { useState } from 'react';
import { ListPlus, Plus, Check } from 'lucide-react';
import { api } from '../api';
import { useApp } from '../App';

// Menu "aggiungi a lista": pannello inline (non absolute) così non viene tagliato dentro
// il modal, che ha overflow. `item` porta i campi minimi da salvare nella lista.
export default function AddToListMenu({ item }) {
  const { addToast } = useApp();
  const [open, setOpen] = useState(false);
  const [lists, setLists] = useState(null);
  const [newName, setNewName] = useState('');
  const [added, setAdded] = useState({}); // id lista → true, per il segno di spunta

  const payload = {
    tmdb_id: item.tmdb_id,
    media_type: item.media_type,
    title: item.title,
    poster_path: item.poster_path ?? null,
    vote_average: item.vote_average ?? null,
    release_date: item.release_date ?? null,
  };

  const load = () => api.getLists().then(setLists).catch(() => setLists([]));

  const toggle = () => {
    if (!open && lists === null) load();
    setOpen((o) => !o);
  };

  const addTo = async (list) => {
    try {
      await api.addToList(list.id, payload);
      setAdded((a) => ({ ...a, [list.id]: true }));
      addToast(`Aggiunto a “${list.name}”`);
    } catch (err) {
      // 409 = già presente: lo trattiamo come "ok, c'è già".
      setAdded((a) => ({ ...a, [list.id]: true }));
      addToast(err.message?.includes('Già') ? `Già in “${list.name}”` : 'Errore');
    }
  };

  const createAndAdd = async (e) => {
    e.preventDefault();
    const name = newName.trim();
    if (!name) return;
    try {
      const list = await api.createList(name);
      setNewName('');
      await load();
      await addTo(list);
    } catch {
      addToast('Errore nella creazione della lista');
    }
  };

  return (
    <div className="addlist">
      <button className="btn btn-secondary" onClick={toggle}>
        <ListPlus size={16} /> Aggiungi a lista
      </button>

      {open && (
        <div className="addlist-panel">
          {lists === null ? (
            <div className="spinner" style={{ margin: '12px auto' }} />
          ) : (
            <>
              {lists.length > 0 && (
                <div className="addlist-items">
                  {lists.map((l) => (
                    <button key={l.id} className="addlist-row" onClick={() => addTo(l)}>
                      <span>{l.name}</span>
                      {added[l.id] ? <Check size={15} className="addlist-check" /> : <Plus size={15} />}
                    </button>
                  ))}
                </div>
              )}
              <form className="addlist-new" onSubmit={createAndAdd}>
                <input
                  className="auth-input"
                  placeholder="Nuova lista…"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                  maxLength={100}
                />
                <button className="btn btn-primary" type="submit" disabled={!newName.trim()}>
                  <Plus size={15} /> Crea
                </button>
              </form>
            </>
          )}
        </div>
      )}
    </div>
  );
}
