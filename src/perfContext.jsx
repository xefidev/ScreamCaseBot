import React, { createContext, useContext } from 'react';

// Simple mode is removed. All devices get full animations with GPU-optimized rendering.
const PerfContext = createContext({ lowPerf: false, setLowPerf: () => {} });

export function PerfProvider({ children }) {
  // Always full animations - mobile optimization handled via CSS/will-change
  const value = { lowPerf: false, setLowPerf: () => {} };
  return <PerfContext.Provider value={value}>{children}</PerfContext.Provider>;
}

export const usePerf = () => useContext(PerfContext);

// Compat helpers (now always return full motion)
export const getMotionProps = (_lowPerf, full) => full;
export const getTransition = (_lowPerf, normal = { duration: 0.3 }) => normal;
export const shouldAnimate = () => true;
