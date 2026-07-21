import { useEffect, useState } from 'react';
import {
  Mail,
  KeyRound,
  MonitorSmartphone,
  Trash2,
  ShieldAlert,
  Check,
} from 'lucide-react';
import { api } from '../api';
import { useApp } from '../App';
import { useAuth } from '../AuthContext';

// Data leggibile dal timestamp ISO delle sessioni.
const fmtDate = (iso) => {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleString('it-IT', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  } catch {
    return iso;
  }
};

export default function SettingsPage() {
  const { user, logout, refreshUser } = useAuth();
  const { addToast } = useApp();

  return (
    <>
      <div className="page-header">
        <h1 className="page-title">Impostazioni</h1>
        <p className="page-subtitle">Gestisci il tuo account e la sicurezza</p>
      </div>

      <div className="settings-grid">
        <EmailSection user={user} refreshUser={refreshUser} addToast={addToast} />
        <PasswordSection addToast={addToast} />
        <SessionsSection addToast={addToast} />
        <DangerSection logout={logout} addToast={addToast} />
      </div>
    </>
  );
}

// ── Cambio email (due passi: password → codice) ──────────────────────────────
function EmailSection({ user, refreshUser, addToast }) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState('form'); // 'form' | 'code'
  const [newEmail, setNewEmail] = useState('');
  const [password, setPassword] = useState('');
  const [code, setCode] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const reset = () => {
    setOpen(false);
    setStep('form');
    setNewEmail('');
    setPassword('');
    setCode('');
    setError('');
  };

  const requestCode = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await api.requestEmailChange(newEmail, password);
      setStep('code');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const confirmChange = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await api.confirmEmailChange(newEmail, code.trim().toUpperCase());
      await refreshUser();
      addToast('Email aggiornata');
      reset();
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="settings-section">
      <h2><Mail size={18} /> Email</h2>
      <p className="settings-desc">L'indirizzo con cui accedi e ricevi le comunicazioni.</p>

      {!open ? (
        <div className="settings-row">
          <span className="settings-field-value">{user?.email}</span>
          <button className="btn btn-secondary" onClick={() => setOpen(true)}>
            Cambia email
          </button>
        </div>
      ) : step === 'form' ? (
        <form className="settings-form" onSubmit={requestCode}>
          <label className="auth-label" htmlFor="new-email">Nuovo indirizzo</label>
          <input
            id="new-email"
            className="auth-input"
            type="email"
            value={newEmail}
            onChange={(e) => setNewEmail(e.target.value)}
            autoComplete="email"
            required
            autoFocus
          />
          <label className="auth-label" htmlFor="email-pw">Password attuale</label>
          <input
            id="email-pw"
            className="auth-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          {error && <div className="auth-error">{error}</div>}
          <div className="settings-actions">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              {busy ? 'Invio…' : 'Inviami il codice'}
            </button>
            <button className="btn btn-secondary" type="button" onClick={reset}>
              Annulla
            </button>
          </div>
        </form>
      ) : (
        <form className="settings-form" onSubmit={confirmChange}>
          <p className="settings-desc">
            Abbiamo mandato un codice a <strong>{newEmail}</strong>. Scade tra 15 minuti.
          </p>
          <label className="auth-label" htmlFor="email-code">Codice di conferma</label>
          <input
            id="email-code"
            className="auth-input auth-input-code"
            value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            maxLength={6}
            placeholder="ABC123"
            required
            autoFocus
          />
          {error && <div className="auth-error">{error}</div>}
          <div className="settings-actions">
            <button className="btn btn-primary" type="submit" disabled={busy}>
              <Check size={16} /> {busy ? 'Conferma…' : 'Conferma email'}
            </button>
            <button className="btn btn-secondary" type="button" onClick={reset}>
              Annulla
            </button>
          </div>
        </form>
      )}
    </section>
  );
}

// ── Cambio password ──────────────────────────────────────────────────────────
function PasswordSection({ addToast }) {
  const [current, setCurrent] = useState('');
  const [next, setNext] = useState('');
  const [confirm, setConfirm] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setError('');
    if (next !== confirm) {
      setError('Le due password non coincidono');
      return;
    }
    setBusy(true);
    try {
      await api.changePassword(current, next);
      addToast('Password aggiornata');
      setCurrent('');
      setNext('');
      setConfirm('');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="settings-section">
      <h2><KeyRound size={18} /> Password</h2>
      <p className="settings-desc">
        Cambiandola verrai disconnesso da tutti gli altri dispositivi.
      </p>
      <form className="settings-form" onSubmit={submit}>
        <label className="auth-label" htmlFor="cur-pw">Password attuale</label>
        <input
          id="cur-pw"
          className="auth-input"
          type="password"
          value={current}
          onChange={(e) => setCurrent(e.target.value)}
          autoComplete="current-password"
          required
        />
        <label className="auth-label" htmlFor="new-pw">Nuova password</label>
        <input
          id="new-pw"
          className="auth-input"
          type="password"
          value={next}
          onChange={(e) => setNext(e.target.value)}
          minLength={8}
          maxLength={72}
          autoComplete="new-password"
          required
        />
        <label className="auth-label" htmlFor="new-pw2">Ripeti la nuova password</label>
        <input
          id="new-pw2"
          className="auth-input"
          type="password"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          minLength={8}
          maxLength={72}
          autoComplete="new-password"
          required
        />
        <p className="auth-hint">Almeno 8 caratteri.</p>
        {error && <div className="auth-error">{error}</div>}
        <div className="settings-actions">
          <button className="btn btn-primary" type="submit" disabled={busy}>
            {busy ? 'Aggiornamento…' : 'Aggiorna password'}
          </button>
        </div>
      </form>
    </section>
  );
}

// ── Sessioni attive ──────────────────────────────────────────────────────────
function SessionsSection({ addToast }) {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const load = () => {
    setLoading(true);
    api.getSessions()
      .then(setSessions)
      .catch(() => setSessions([]))
      .finally(() => setLoading(false));
  };

  useEffect(load, []);

  const revokeOthers = async () => {
    setBusy(true);
    try {
      await api.revokeOtherSessions();
      addToast('Altre sessioni terminate');
      load();
    } catch (err) {
      addToast(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="settings-section">
      <h2><MonitorSmartphone size={18} /> Sessioni attive</h2>
      <p className="settings-desc">
        I dispositivi con una sessione aperta sul tuo account.
      </p>

      {loading ? (
        <div className="spinner" />
      ) : sessions.length === 0 ? (
        <p className="settings-desc">Nessuna sessione attiva.</p>
      ) : (
        <ul className="sessions-list">
          {sessions.map((s) => (
            <li key={s.id} className="session-item">
              <span className="session-agent">{s.user_agent || 'Dispositivo sconosciuto'}</span>
              <span className="session-date">
                {fmtDate(s.last_used_at || s.created_at)}
              </span>
            </li>
          ))}
        </ul>
      )}

      {sessions.length > 1 && (
        <div className="settings-actions">
          <button className="btn btn-secondary" onClick={revokeOthers} disabled={busy}>
            {busy ? 'Chiusura…' : 'Termina le altre sessioni'}
          </button>
        </div>
      )}
    </section>
  );
}

// ── Eliminazione account ─────────────────────────────────────────────────────
function DangerSection({ logout, addToast }) {
  const [confirming, setConfirming] = useState(false);
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const remove = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await api.deleteAccount(password);
      addToast('Account eliminato');
      // La sessione è già chiusa lato server; sgancio anche il client.
      await logout();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <section className="settings-section settings-danger">
      <h2><ShieldAlert size={18} /> Elimina account</h2>
      <p className="settings-desc">
        Cancella per sempre il tuo account, la lista dei visti, la watchlist e i progressi.
        L'operazione è irreversibile.
      </p>

      {!confirming ? (
        <div className="settings-actions">
          <button className="btn btn-danger" onClick={() => setConfirming(true)}>
            <Trash2 size={16} /> Elimina il mio account
          </button>
        </div>
      ) : (
        <form className="settings-form" onSubmit={remove}>
          <label className="auth-label" htmlFor="del-pw">
            Conferma con la password
          </label>
          <input
            id="del-pw"
            className="auth-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
            autoFocus
          />
          {error && <div className="auth-error">{error}</div>}
          <div className="settings-actions">
            <button className="btn btn-danger" type="submit" disabled={busy}>
              <Trash2 size={16} /> {busy ? 'Eliminazione…' : 'Elimina definitivamente'}
            </button>
            <button
              className="btn btn-secondary"
              type="button"
              onClick={() => { setConfirming(false); setPassword(''); setError(''); }}
            >
              Annulla
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
