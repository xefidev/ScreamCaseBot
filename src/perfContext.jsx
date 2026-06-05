import React, { createContext, useContext, useEffect, useLayoutEffect, useState } from 'react';

const KEY = 'screamcase:lowperf';
const PerfContext = createContext({ lowPerf: false, setLowPerf: () => {} });

function detectInitialLowPerf() {
  try {
    const stored = localStorage.getItem(KEY);
    if (stored !== null) return stored === '1';
  } catch {}
  try {
    const mem = navigator.deviceMemory;
    const cores = navigator.hardwareConcurrency;
    const conn = navigator.connection?.effectiveType;
    if ((mem && mem <= 2) || (cores && cores <= 2) || conn === 'slow-2g' || conn === '2g') return true;
  } catch {}
  try {
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return true;
  } catch {}
  return false;
}

// Apply class to <html> synchronously before first paint to avoid flash
function applyClass(lowPerf) {
  try {
    const root = document.documentElement;
    if (lowPerf) {
      root.classList.add('lowperf');
      root.style.setProperty('--motion-duration', '0.12s');
    } else {
      root.classList.remove('lowperf');
      root.style.setProperty('--motion-duration', '0.3s');
    }
  } catch {}
}

// Run BEFORE React mounts so first render already has correct class
if (typeof window !== 'undefined') {
  applyClass(detectInitialLowPerf());
}

export function PerfProvider({ children }) {
  const [lowPerf, setLowPerfState] = useState(detectInitialLowPerf);

  // useLayoutEffect runs synchronously after DOM mutations but before paint
  useLayoutEffect(() => {
    applyClass(lowPerf);
    try { localStorage.setItem(KEY, lowPerf ? '1' : '0'); } catch {}
  }, [lowPerf]);

  // Listen to storage events so toggle in one tab/iframe syncs everywhere
  useEffect(() => {
    const handler = (e) => {
      if (e.key === KEY && e.newValue !== null) {
        setLowPerfState(e.newValue === '1');
      }
    };
    window.addEventListener('storage', handler);
    return () => window.removeEventListener('storage', handler);
  }, []);

  const setLowPerf = (v) => setLowPerfState(typeof v === 'function' ? v(lowPerf) : !!v);

  return <PerfContext.Provider value={{ lowPerf, setLowPerf }}>{children}</PerfContext.Provider>;
}

export const usePerf = () => useContext(PerfContext);

export const getMotionProps = (lowPerf, full, reduced) => lowPerf ? (reduced ?? {}) : full;

export const getTransition = (lowPerf, normal = { duration: 0.3 }) =>
  lowPerf ? { duration: 0.12, ease: 'linear' } : normal;
