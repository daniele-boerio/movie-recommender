import { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowLeft, Film, Mail, UserPlus } from 'lucide-react';
import { api } from '../api';
import { useAuth } from '../AuthContext';

export default function RegisterPage() {
  const { register } = useAuth();
  const [step, setStep] = useState('email'); // 'email' | 'code'
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const requestCode = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await api.requestCode(email);
      // Si passa al passo 2 comunque: il backend risponde uguale anche se l'email
      // è già registrata, apposta per non rivelare quali indirizzi hanno un account.
      setStep('code');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const completeRegistration = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await register({ email, code: code.trim().toUpperCase(), username, password });
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  return (
    <div className="auth-layout">
      <div className="auth-card">
        <div className="auth-logo">
          <Film size={22} />
          WatchNext
        </div>

        {step === 'email' ? (
          <>
            <p className="auth-subtitle">
              Inserisci la tua email: ti mandiamo un codice per confermarla.
            </p>
            <form onSubmit={requestCode}>
              <label className="auth-label" htmlFor="email">Email</label>
              <input
                id="email"
                className="auth-input"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                required
                autoFocus
              />

              {error && <div className="auth-error">{error}</div>}

              <button className="btn btn-primary auth-submit" type="submit" disabled={busy}>
                <Mail size={16} />
                {busy ? 'Invio…' : 'Inviami il codice'}
              </button>
            </form>

            <p className="auth-switch">
              Hai già un account? <Link to="/login">Accedi</Link>
            </p>
          </>
        ) : (
          <>
            <p className="auth-subtitle">
              Se <strong>{email}</strong> è un indirizzo valido, il codice è in arrivo.
              Scade tra 15 minuti.
            </p>
            <form onSubmit={completeRegistration}>
              <label className="auth-label" htmlFor="code">Codice di verifica</label>
              <input
                id="code"
                className="auth-input auth-input-code"
                value={code}
                onChange={(e) => setCode(e.target.value.toUpperCase())}
                maxLength={6}
                placeholder="ABC123"
                required
                autoFocus
              />

              <label className="auth-label" htmlFor="username">Username</label>
              <input
                id="username"
                className="auth-input"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                minLength={3}
                maxLength={32}
                autoComplete="username"
                required
              />

              <label className="auth-label" htmlFor="new-password">Password</label>
              <input
                id="new-password"
                className="auth-input"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                minLength={8}
                maxLength={72}
                autoComplete="new-password"
                required
              />
              <p className="auth-hint">Almeno 8 caratteri.</p>

              {error && <div className="auth-error">{error}</div>}

              <button className="btn btn-primary auth-submit" type="submit" disabled={busy}>
                <UserPlus size={16} />
                {busy ? 'Creazione…' : 'Crea account'}
              </button>
            </form>

            <button
              type="button"
              className="auth-back"
              onClick={() => { setStep('email'); setError(''); }}
            >
              <ArrowLeft size={14} />
              Ho sbagliato email
            </button>
          </>
        )}
      </div>
    </div>
  );
}
