import React, { createContext, useContext, useEffect, useState } from 'react';

const KEY = 'screamcase:lowperf';
const PerfContext = createContext({ lowPerf: false, setLowPerf: () => {} });

export function PerfProvider({ children }) {
  const [lowPerf, setLowPerfState] = useState(() => {
    try {
      const stored = localStorage.getItem(KEY);
      if (stored !== null) return stored === '1';
    } catch {}
    // Auto-detect weak devices
    try {
      const mem = navigator.deviceMemory;
      const cores = navigator.hardwareConcurrency;
      const conn = navigator.connection?.effectiveType;
      if ((mem && mem <= 2) || (cores && cores <= 2) || conn === 'slow-2g' || conn === '2g') {
        return true;
      }
    } catch {}
    // Respect prefers-reduced-motion
    try {
      if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) return true;
    } catch {}
    return false;
  });

  useEffect(() => {
    try { localStorage.setItem(KEY, lowPerf ? '1' : '0'); } catch {}
    const root = document.documentElement;
    if (lowPerf) {
      root.classList.add('lowperf');
    } else {
      root.classList.remove('lowperf');
    }
  }, [lowPerf]);

  const setLowPerf = (v) => setLowPerfState(typeof v === 'function' ? v(lowPerf) : !!v);

  return <PerfContext.Provider value={{ lowPerf, setLowPerf }}>{children}</PerfContext.Provider>;
}

export const usePerf = () => useContext(PerfContext);

// Motion helpers — return reduced transitions in lowPerf mode
export const getMotionProps = (lowPerf, full, reduced) => lowPerf ? (reduced ?? {}) : full;

export const getTransition = (lowPerf, normal = { duration: 0.3 }) =>
  lowPerf ? { duration: 0 } : normal;


// Return whether animation should play at all
export const shouldAnimate = (lowPerf) => !lowPerf;