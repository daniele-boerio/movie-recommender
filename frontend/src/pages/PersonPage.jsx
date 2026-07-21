import { useEffect, useMemo, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ArrowLeft, User } from 'lucide-react';
import { api, posterUrl } from '../api';
import MediaCard from '../components/MediaCard';

export default function PersonPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [person, setPerson] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    window.scrollTo(0, 0);
    api.person(id)
      .then(setPerson)
      .catch(() => setPerson(null))
      .finally(() => setLoading(false));
  }, [id]);

  // Tutti i lavori (recitazione + troupe), senza doppioni, dai più popolari. Un titolo
  // può comparire sia in cast sia in crew (es. attore-regista): lo teniamo una volta.
  const credits = useMemo(() => {
    if (!person?.combined_credits) return [];
    const all = [
      ...(person.combined_credits.cast || []),
      ...(person.combined_credits.crew || []),
    ];
    const byKey = new Map();
    for (const c of all) {
      if (c.media_type !== 'movie' && c.media_type !== 'tv') continue;
      const key = `${c.id}-${c.media_type}`;
      if (!byKey.has(key)) byKey.set(key, c);
    }
    return [...byKey.values()].sort((a, b) => (b.popularity || 0) - (a.popularity || 0));
  }, [person]);

  if (loading) return <div className="spinner" />;
  if (!person) {
    return (
      <div className="empty-state">
        <User className="empty-state-icon" />
        <h3>Persona non trovata</h3>
      </div>
    );
  }

  const photo = posterUrl(person.profile_path, 'w342');
  const dept = person.known_for_department === 'Directing' ? 'Regia' : 'Recitazione';

  return (
    <>
      <button className="back-btn" onClick={() => navigate(-1)}>
        <ArrowLeft size={16} /> Indietro
      </button>

      <div className="person-header">
        {photo ? (
          <img className="person-photo" src={photo} alt={person.name} />
        ) : (
          <div className="person-photo person-photo-empty"><User size={40} /></div>
        )}
        <div className="person-info">
          <h1 className="page-title">{person.name}</h1>
          <p className="page-subtitle">
            {dept}
            {person.birthday ? ` · nato/a il ${person.birthday}` : ''}
            {person.place_of_birth ? ` · ${person.place_of_birth}` : ''}
          </p>
          {person.biography && <p className="person-bio">{person.biography}</p>}
        </div>
      </div>

      <h2 className="section-title">Filmografia</h2>
      {credits.length === 0 ? (
        <p className="stats-empty">Nessun titolo disponibile.</p>
      ) : (
        <div className="media-grid">
          {credits.map((c) => (
            <MediaCard
              key={`${c.id}-${c.media_type}`}
              item={{ ...c, id: c.id, tmdb_id: c.id }}
            />
          ))}
        </div>
      )}
    </>
  );
}
