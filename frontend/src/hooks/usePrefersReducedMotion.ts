import { useEffect, useState } from 'react';

export function usePrefersReducedMotion(): boolean {
  const [prefersReducedMotion, setPrefersReducedMotion] = useState(false);

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
      return undefined;
    }

    const mediaQuery = window.matchMedia('(prefers-reduced-motion: reduce)');
    const syncPreference = () => {
      setPrefersReducedMotion(mediaQuery.matches);
    };

    syncPreference();
    mediaQuery.addEventListener('change', syncPreference);

    return () => {
      mediaQuery.removeEventListener('change', syncPreference);
    };
  }, []);

  return prefersReducedMotion;
}
