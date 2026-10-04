import { useEffect } from 'react';
import { usePrefs } from '../services/mock/store';

/** Setzt Hell/Dunkel und Schriftgröße am <html>-Element. */
export function ThemeSync() {
  const theme = usePrefs((s) => s.theme);
  const largeText = usePrefs((s) => s.largeText);
  useEffect(() => {
    const mq = matchMedia('(prefers-color-scheme: dark)');
    const apply = () => {
      const dark = theme === 'dark' || (theme === 'system' && mq.matches);
      document.documentElement.classList.toggle('dark', dark);
      document.querySelector('meta[name="theme-color"]')?.setAttribute('content', dark ? '#0B0D10' : '#F3F4F6');
    };
    apply();
    mq.addEventListener('change', apply);
    return () => mq.removeEventListener('change', apply);
  }, [theme]);
  useEffect(() => {
    document.documentElement.classList.toggle('text-lg-mode', largeText);
  }, [largeText]);
  return null;
}
