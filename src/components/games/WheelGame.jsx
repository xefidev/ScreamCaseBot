import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ALL_GIFTS } from '../../giftData';

const SEGMENT_ANGLE = 360 / 12;
const SPIN_COST = 50;
const easeOutCirc = [0.12, 0, 0.39, 0];

export default function WheelGame({ onClose, isPage, onWin, balance = 0, setBalance = null, setSpent = null }) {
  const [isSpinning, setIsSpinning] = useState(false);
  const [winSegment, setWinSegment] = useState(null);
  const [wheelSegments, setWheelSegments] = useState(() => generateWheelSegments());
  const [spinRotation, setSpinRotation] = useState(0);
  const [targetRotation, setTargetRotation] = useState(0);
  const [animKey, setAnimKey] = useState(0);
  const pendingWinSegment = useRef(null);

  function generateWheelSegments() {
    const commonItems = ALL_GIFTS.filter(g => g.price >= 15 && g.price <= 50);
    const premiumItems = ALL_GIFTS.filter(g => g.price > 50);

    const shuffledPremium = [...premiumItems].sort(() => Math.random() - 0.5);
    const segments = [
      ...commonItems.slice(0, 4),
      ...shuffledPremium.slice(0, 8),
    ];

    const colors = ['#ff0000', '#00ff00', '#0099ff', '#ff00ff', '#ffaa00', '#888888', '#00ffff', '#ff00aa', '#a855f7', '#22c55e', '#f97316', '#3b82f6'];

    return segments.map((segment, idx) => ({
      id: idx + 1,
      label: segment.price.toString(),
      color: colors[idx % colors.length],
      image: segment.image,
      price: segment.price,
    }));
  }

  const handleSpin = () => {
    if (isSpinning) return;

    if (balance < SPIN_COST) {
      console.error(`Insufficient balance! Need ${SPIN_COST}, have ${balance}`);
      return;
    }

    setIsSpinning(true);
    setWinSegment(null);

    if (setBalance) {
      setBalance(prev => Math.max(0, prev - SPIN_COST));
    }
    if (setSpent) {
      setSpent(prev => prev + SPIN_COST);
    }

    const cheapIndices = wheelSegments.map((s, i) => s.price <= 50 ? i : -1).filter(i => i !== -1);
    const midIndices = wheelSegments.map((s, i) => s.price > 50 && s.price <= 150 ? i : -1).filter(i => i !== -1);
    const jackpotIndices = wheelSegments.map((s, i) => s.price > 150 ? i : -1).filter(i => i !== -1);

    const rand = Math.random() * 100;
    let winIndex;

    if (rand < 85 && cheapIndices.length > 0) {
      winIndex = cheapIndices[Math.floor(Math.random() * cheapIndices.length)];
    } else if (rand < 97 && midIndices.length > 0) {
      winIndex = midIndices[Math.floor(Math.random() * midIndices.length)];
    } else if (jackpotIndices.length > 0) {
      winIndex = jackpotIndices[Math.floor(Math.random() * jackpotIndices.length)];
    } else {
      winIndex = Math.floor(Math.random() * wheelSegments.length);
    }

    const wonSegment = wheelSegments[winIndex];
    pendingWinSegment.current = wonSegment;

    const fullRotations = 5;
    const segmentOffset = 360 - (winIndex * SEGMENT_ANGLE + SEGMENT_ANGLE / 2);
    const newTargetRotation = spinRotation + (fullRotations * 360) + segmentOffset;

    setTargetRotation(newTargetRotation);
    setAnimKey(prev => prev + 1);
  };

  const handleAnimationComplete = () => {
    setWinSegment(pendingWinSegment.current);
    setIsSpinning(false);
    setSpinRotation(targetRotation % 360); // Keep it normalized if needed, but cumulative is fine

    if (onWin && pendingWinSegment.current) {
      onWin(pendingWinSegment.current);
    }
  };

  const generateWheelSVG = () => {
    const radius = 180;
    const center = 200;

    return wheelSegments.map((segment, index) => {
      const startAngle = index * SEGMENT_ANGLE;
      const endAngle = startAngle + SEGMENT_ANGLE;
      const startRad = (startAngle - 90) * Math.PI / 180;
      const endRad = (endAngle - 90) * Math.PI / 180;

      const x1 = center + radius * Math.cos(startRad);
      const y1 = center + radius * Math.sin(startRad);
      const x2 = center + radius * Math.cos(endRad);
      const y2 = center + radius * Math.sin(endRad);

      const largeArc = SEGMENT_ANGLE > 180 ? 1 : 0;
      const pathD = `M ${center} ${center} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;

      const midAngle = (startAngle + SEGMENT_ANGLE / 2 - 90) * Math.PI / 180;
      const contentRadius = radius * 0.65;
      const contentX = center + contentRadius * Math.cos(midAngle);
      const contentY = center + contentRadius * Math.sin(midAngle);

      return (
        <g key={segment.id}>
          <path
            d={pathD}
            fill={`${segment.color}20`}
            stroke={`${segment.color}50`}
            strokeWidth="2"
          />
          <circle
            cx={contentX}
            cy={contentY}
            r="24"
            fill={`${segment.color}25`}
          />
          <image
            href={segment.image}
            x={contentX - 16}
            y={contentY - 16}
            width="32"
            height="32"
            preserveAspectRatio="xMidYMid meet"
          />
          <text
            x={contentX}
            y={contentY + 28}
            textAnchor="middle"
            fill="rgba(255,255,255,0.9)"
            fontSize="11"
            fontWeight="bold"
          >
            {segment.label}
          </text>
        </g>
      );
    });
  };

  const content = (
    <div className={`${isPage ? 'min-h-full overflow-y-auto p-4' : ''}`}>
      <div className={`${!isPage ? 'glass-panel p-6 w-full max-w-lg mx-auto' : ''}`}>
        {!isPage && onClose && (
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-black text-white font-rounded uppercase tracking-widest">Колесо Фортуны</h2>
            <button onClick={onClose} className="text-white/50 hover:text-white text-xl font-rounded">✕</button>
          </div>
        )}
        {isPage && (
          <div className="mb-6">
            <h2 className="text-3xl font-black text-white font-rounded uppercase tracking-widest">Колесо Фортуны</h2>
            <p className="text-white/50 text-sm mt-1 font-rounded flex items-center justify-center gap-1">
              Стоимость прокрута: {SPIN_COST}
              <img src="/asset/Icons/TelegramStar.png" className="h-7 w-7" alt="Stars" />
            </p>
          </div>
        )}

        <div className="relative w-72 h-72 mx-auto mb-8">
          <div className="absolute inset-[-8px] rounded-full"
            style={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.1), rgba(255,255,255,0.02))',
              border: '2px solid rgba(255,255,255,0.15)',
            }}
          />

          <div className="absolute top-[-16px] left-1/2 transform -translate-x-1/2 z-30">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 24L2 4H22L12 24Z" fill="white" />
              <path d="M12 20L4 6H20L12 20Z" fill="rgba(255,255,255,0.8)" />
            </svg>
            <div className="absolute top-0 left-1/2 -translate-x-1/2 w-0.5 h-10 bg-white/20 blur-[1px] -z-10" />
          </div>

          <div className="absolute inset-[-4px] rounded-full"
            style={{
              border: '1px solid rgba(255,255,255,0.1)',
              boxShadow: isSpinning ? '0 0 20px rgba(255,255,255,0.2)' : '0 0 10px rgba(255,255,255,0.1)',
            }}
          />

          <div className="w-full h-full rounded-full overflow-hidden"
            style={{
              background: 'linear-gradient(135deg, rgba(255,255,255,0.05), rgba(255,255,255,0.02))',
              border: '3px solid rgba(255,255,255,0.1)',
              boxShadow: 'inset 0 0 50px rgba(0,0,0,0.5)',
              filter: 'none',
            }}
          >
            <motion.div
              key={animKey}
              animate={{ rotate: targetRotation }}
              transition={{
                duration: 4,
                ease: [0.12, 0, 0.39, 0],
              }}
              onAnimationComplete={handleAnimationComplete}
              style={{ transformOrigin: 'center center' }}
            >
              <svg viewBox="0 0 400 400" className="w-full h-full" style={{ filter: 'none' }}>
                <circle cx="200" cy="200" r="198" fill="url(#metalGradient)" opacity="0.3" />
                <defs>
                  <radialGradient id="metalGradient">
                    <stop offset="0%" stopColor="rgba(255,255,255,0.1)" />
                    <stop offset="100%" stopColor="rgba(0,0,0,0.2)" />
                  </radialGradient>
                </defs>
                {generateWheelSVG()}
                <circle cx="200" cy="200" r="30" fill="rgba(255,255,255,0.05)" stroke="rgba(255,255,255,0.2)" strokeWidth="2" />
                <image
                  href="/asset/Icons/TelegramStar.png"
                  x="185"
                  y="185"
                  width="30"
                  height="30"
                  preserveAspectRatio="xMidYMid meet"
                />
              </svg>
            </motion.div>
          </div>
        </div>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={handleSpin}
          disabled={isSpinning || balance < SPIN_COST}
          className="w-full py-4 rounded-xl font-black text-lg disabled:opacity-50 transition-all flex items-center justify-center gap-2"
          style={{
            backgroundColor: (isSpinning || balance < SPIN_COST) ? 'rgba(255,255,255,0.05)' : 'rgba(168, 85, 247, 0.15)',
            border: `1px solid ${(isSpinning || balance < SPIN_COST) ? 'rgba(255,255,255,0.1)' : 'rgba(168, 85, 247, 0.3)'}`,
            color: (isSpinning || balance < SPIN_COST) ? 'rgba(255,255,255,0.3)' : '#a855f7',
          }}
        >
            {isSpinning ? (
              <div className="flex items-center justify-center gap-2 font-rounded">
                <motion.div
                  animate={{ rotate: 360 }}
                  transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                  className="w-5 h-5 border-2 border-purple-400/30 border-t-purple-400 rounded-full"
                />
                Крутим...
              </div>
            ) : (
              <span className="flex items-center justify-center gap-2 font-rounded">
                КРУТИТЬ ({SPIN_COST}
                <img src="/asset/Icons/TelegramStar.png" className="h-6 w-6" alt="Stars" />)
              </span>
            )}
        </motion.button>

          {winSegment && (
            <motion.div
              initial={{ opacity: 0, scale: 0.8, y: 20 }}
              animate={{ opacity: 1, scale: 1, y: 0 }}
              className="mt-6 text-center p-6 rounded-3xl border"
              style={{
                borderColor: `${winSegment.color}30`,
                backgroundColor: `${winSegment.color}10`,
              }}
            >
              <p className="text-white/50 text-xs mb-2 uppercase tracking-wider font-rounded">Вы выиграли!</p>
              <img
                src={winSegment.image}
                alt={winSegment.label}
                className="h-28 w-28 object-contain mx-auto mb-3"
                style={{ filter: `drop-shadow(0 0 25px ${winSegment.color}70)` }}
              />
              <p
                className="text-white font-black text-3xl mb-1 flex items-center justify-center gap-2 font-rounded"
                style={{ color: winSegment.color }}
              >
                {winSegment.label}
                <img src="/asset/Icons/TelegramStar.png" className="h-7 w-7" alt="Stars" />
              </p>
            </motion.div>
          )}
      </div>
    </div>
  );

  if (isPage) return content;

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
    >
      {content}
    </motion.div>
  );
}
