// Audio pool — preload, reuse instances, cheap on weak devices.
const cache = new Map();
const POOL_SIZE = 2;

function getPool(path) {
  if (!cache.has(path)) {
    const pool = [];
    for (let i = 0; i < POOL_SIZE; i++) {
      try {
        const a = new Audio(path);
        a.preload = 'auto';
        a.volume = 0.5;
        pool.push(a);
      } catch (e) {
        console.warn('Audio create failed', e);
      }
    }
    cache.set(path, { pool, idx: 0 });
  }
  return cache.get(path);
}

export function playSound(path) {
  try {
    if (!path) return;
    const entry = getPool(path);
    if (!entry.pool.length) return;
    const a = entry.pool[entry.idx];
    entry.idx = (entry.idx + 1) % entry.pool.length;
    try { a.pause(); a.currentTime = 0; } catch {}
    const p = a.play();
    if (p?.catch) p.catch(() => {});
  } catch (e) {
    console.warn('playSound error', e);
  }
}

export function stopSound() {
  try {
    cache.forEach(({ pool }) => pool.forEach(a => { try { a.pause(); a.currentTime = 0; } catch {} }));
  } catch {}
}

// Lowperf override — bind to render time via setLowPerfMute
let muted = false;
export const setAudioMuted = (v) => { muted = !!v; };

// Wrap play to respect mute
const _play = playSound;
export const playSoundSafe = (path) => { if (!muted) _play(path); };
