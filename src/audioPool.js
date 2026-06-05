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
        // force browser to actually fetch+decode now, not on first play()
        try { a.load(); } catch {}
        pool.push(a);
      } catch (e) {
        console.warn('Audio create failed', e);
      }
    }
    cache.set(path, { pool, idx: 0 });
  }
  return cache.get(path);
}

// Preload a list of sounds and wait until they can play through.
// Resolves even on error so we never block the UI.
export function preloadSounds(paths) {
  const tasks = paths.map((path) => new Promise((resolve) => {
    try {
      const entry = getPool(path);
      const a = entry.pool[0];
      if (!a) return resolve();
      if (a.readyState >= 3) return resolve(); // HAVE_FUTURE_DATA or more
      const done = () => { cleanup(); resolve(); };
      const cleanup = () => {
        a.removeEventListener('canplaythrough', done);
        a.removeEventListener('error', done);
      };
      a.addEventListener('canplaythrough', done, { once: true });
      a.addEventListener('error', done, { once: true });
      try { a.load(); } catch {}
      // safety timeout — never wait more than 2s
      setTimeout(done, 2000);
    } catch { resolve(); }
  }));
  return Promise.all(tasks);
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
