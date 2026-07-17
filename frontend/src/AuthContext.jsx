import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { api, setSessionExpiredHandler } from './api';

const AuthContext = createContext();
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  // `loading` evita il lampo della pagina di login a ogni ricarica: i cookie sono
  // httpOnly, quindi l'unico modo di sapere se la sessione è viva è chiederlo al server.
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setSessionExpiredHandler(() => setUser(null));

    api.me()
      .then(setUser)
      .catch(() => setUser(null))
      .finally(() => setLoading(false));
  }, []);

  const login = useCallback(async (identifier, password) => {
    const u = await api.login(identifier, password);
    setUser(u);
    return u;
  }, []);

  const register = useCallback(async (payload) => {
    const u = await api.register(payload);
    setUser(u);
    return u;
  }, []);

  const logout = useCallback(async () => {
    // Anche se la chiamata fallisce l'utente esce comunque dal client: restare
    // "dentro" dopo aver premuto Esci sarebbe peggio di una revoca mancata.
    try {
      await api.logout();
    } finally {
      setUser(null);
    }
  }, []);

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
