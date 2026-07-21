import { useState } from 'react';
import { Sun, Moon } from 'lucide-react';

// Applica il tema al documento e lo ricorda. main.jsx lo imposta al boot; qui lo si
// commuta a runtime (l'attributo su <html> è la fonte di verità, il CSS reagisce a quello).
const applyTheme = (t) => {
  document.documentElement.setAttribute('data-theme', t);
  try {
    localStorage.setItem('theme', t);
  } catch {
    /* localStorage non disponibile: pazienza, resta la scelta di sessione */
  }
};

export default function ThemeToggle() {
  const [theme, setTheme] = useState(
    () => document.documentElement.getAttribute('data-theme') || 'dark'
  );

  const toggle = () => {
    const next = theme === 'dark' ? 'light' : 'dark';
    setTheme(next);
    applyTheme(next);
  };

  return (
    <button
      className="sidebar-logout"
      onClick={toggle}
      title={theme === 'dark' ? 'Passa al tema chiaro' : 'Passa al tema scuro'}
      aria-label="Cambia tema"
    >
      {theme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
    </button>
  );
}
