import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Film, LogIn } from 'lucide-react';
import { useAuth } from '../AuthContext';

export default function LoginPage() {
  const { login } = useAuth();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const onSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await login(identifier, password);
      // Nessun redirect qui: comparso lo user, App monta da sé l'app autenticata.
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
        <p className="auth-subtitle">Accedi per ritrovare la tua lista.</p>

        <form onSubmit={onSubmit}>
          <label className="auth-label" htmlFor="identifier">Username o email</label>
          <input
            id="identifier"
            className="auth-input"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            autoComplete="username"
            required
            autoFocus
          />

          <label className="auth-label" htmlFor="password">Password</label>
          <input
            id="password"
            className="auth-input"
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />

          {error && <div className="auth-error">{error}</div>}

          <button className="btn btn-primary auth-submit" type="submit" disabled={busy}>
            <LogIn size={16} />
            {busy ? 'Accesso…' : 'Accedi'}
          </button>
        </form>

        <p className="auth-switch">
          Non hai un account? <Link to="/register">Registrati</Link>
        </p>
      </div>
    </div>
  );
}
