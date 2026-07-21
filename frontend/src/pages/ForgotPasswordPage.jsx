import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, Film, Mail, KeyRound, CheckCircle2 } from 'lucide-react';
import { api } from '../api';

export default function ForgotPasswordPage() {
  const navigate = useNavigate();
  const [step, setStep] = useState('email'); // 'email' | 'code' | 'done'
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const requestCode = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await api.requestPasswordReset(email);
      // Si passa al passo 2 comunque: il backend risponde uguale anche se l'email non
      // esiste, per non rivelare quali indirizzi hanno un account.
      setStep('code');
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const confirmReset = async (e) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      await api.confirmPasswordReset(email, code.trim().toUpperCase(), password);
      setStep('done');
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

        {step === 'email' && (
          <>
            <p className="auth-subtitle">
              Inserisci la tua email: ti mandiamo un codice per reimpostare la password.
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
              Te la sei ricordata? <Link to="/login">Accedi</Link>
            </p>
          </>
        )}

        {step === 'code' && (
          <>
            <p className="auth-subtitle">
              Se <strong>{email}</strong> ha un account, il codice è in arrivo. Scade tra 15 minuti.
            </p>
            <form onSubmit={confirmReset}>
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

              <label className="auth-label" htmlFor="new-password">Nuova password</label>
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
                <KeyRound size={16} />
                {busy ? 'Reimpostazione…' : 'Reimposta password'}
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

        {step === 'done' && (
          <>
            <div className="auth-done">
              <CheckCircle2 size={40} />
              <p className="auth-subtitle" style={{ marginTop: 12 }}>
                Password aggiornata. Ora puoi accedere con quella nuova.
              </p>
            </div>
            <button
              className="btn btn-primary auth-submit"
              onClick={() => navigate('/login')}
            >
              Vai al login
            </button>
          </>
        )}
      </div>
    </div>
  );
}
