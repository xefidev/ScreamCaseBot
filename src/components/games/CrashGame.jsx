import React, { useState, useEffect, useRef } from 'react';
import { motion } from 'framer-motion';

export default function CrashGame({ onClose, isPage }) {
  const [multiplier, setMultiplier] = useState(1.0);
  const [isRunning, setIsRunning] = useState(false);
  const [crashed, setCrashed] = useState(false);
  const [cashOut, setCashOut] = useState(null);
  const [history, setHistory] = useState([]);
  const intervalRef = useRef(null);

  const startGame = () => {
    setIsRunning(true);
    setCrashed(false);
    setCashOut(null);
    setMultiplier(1.0);
    
    const crashPoint = 1 + Math.random() * 9; // Crash between 1x and 10x
    let currentMultiplier = 1.0;
    
    intervalRef.current = setInterval(() => {
      currentMultiplier += 0.1;
      setMultiplier(parseFloat(currentMultiplier.toFixed(2)));
      
      if (currentMultiplier >= crashPoint) {
        clearInterval(intervalRef.current);
        setIsRunning(false);
        setCrashed(true);
        setHistory(prev => [...prev.slice(-9), crashPoint.toFixed(2)]);
      }
    }, 100);
  };

  const handleCashOut = () => {
    if (isRunning && !crashed) {
      clearInterval(intervalRef.current);
      setIsRunning(false);
      setCashOut(multiplier);
      setHistory(prev => [...prev.slice(-9), multiplier.toFixed(2)]);
    }
  };

  useEffect(() => {
    return () => clearInterval(intervalRef.current);
  }, []);

  const content = (
    <div className={`${isPage ? 'h-full overflow-y-auto p-4' : 'backdrop-blur-2xl bg-white/5 border border-white/10 rounded-3xl p-8 w-full max-w-md mx-4'}`}>
      {!isPage && onClose && (
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-2xl font-black text-white">Crash</h2>
          <button onClick={onClose} className="text-white/50 hover:text-white">
            ✕
          </button>
        </div>
      )}
      {isPage && (
        <div className="mb-6">
          <h2 className="text-2xl font-black text-white">Crash</h2>
        </div>
      )}

      {/* Multiplier Display */}
      <div className="text-center mb-8">
        <motion.div
          className={`text-6xl font-black mb-2 ${
            crashed ? 'text-red-500' : cashOut ? 'text-green-500' : 'text-white'
          }`}
          animate={{ scale: isRunning ? [1, 1.05, 1] : 1 }}
          transition={{ duration: 0.5, repeat: isRunning ? Infinity : 0 }}
        >
          {crashed ? 'CRASH' : cashOut ? `${cashOut}x` : `${multiplier}x`}
        </motion.div>
        {cashOut && (
          <p className="text-green-400 font-bold">Cashed out at {cashOut}x</p>
        )}
      </div>

      {/* Controls */}
      <div className="flex gap-3 mb-6">
        {!isRunning && !crashed && !cashOut && (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={startGame}
            className="flex-1 py-3 rounded-xl bg-green-500/20 border border-green-500/30 text-green-400 font-bold"
          >
            START
          </motion.button>
        )}
        {isRunning && (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleCashOut}
            className="flex-1 py-3 rounded-xl bg-red-500/20 border border-red-500/30 text-red-400 font-bold"
          >
            CASH OUT
          </motion.button>
        )}
        {(crashed || cashOut) && (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={startGame}
            className="flex-1 py-3 rounded-xl bg-white/10 border border-white/20 text-white font-bold"
          >
            PLAY AGAIN
          </motion.button>
        )}
      </div>

      {/* History */}
      <div>
        <p className="text-white/50 text-xs mb-2">RECENT CRASHES</p>
        <div className="flex gap-2 flex-wrap">
          {history.map((item, index) => (
            <span
              key={index}
              className={`px-2 py-1 rounded-lg text-xs font-bold ${
                item >= 2 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
              }`}
            >
              {item}x
            </span>
          ))}
        </div>
      </div>
    </div>
  );

  if (isPage) {
    return <div className="min-h-full">{content}</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
    >
      {content}
    </motion.div>
  );
}
