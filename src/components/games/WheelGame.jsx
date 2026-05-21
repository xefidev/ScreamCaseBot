import React, { useState, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ALL_GIFTS } from '../../giftData';
import { spinWheel } from '../../api';
import { DEFAULT_GIFT_IMAGE, getDynamicGiftImage } from '../../giftUtils';

const SEGMENT_ANGLE = 360 / 12;
const SPIN_COST = 50;

const playSound = (path) => {
  try {
    const audio = new Audio(path);
    audio.volume = 0.5;
    audio.play().catch(e => console.warn("Audio play blocked", e));
  } catch (e) {
    console.error("Audio error", e);
  }
};

export default function WheelGame({ onClose, isPage, onWin, balance = 0, setBalance = null, setSpent = null }) {
  const [isSpinning, setIsSpinning] = useState(false);
  const [winSegment, setWinSegment] = useState(null);
  const [wheelSegments] = useState(() => {
    const SEGMENTS = [15, 50, 20, 100, 25, 200, 30, 300, 40, 500, 50, 150];
    const colors = ['#ff0000', '#00ff00', '#0099ff', '#ff00ff', '#ffaa00', '#888888', '#00ffff', '#ff00aa', '#a855f7', '#22c55e', '#f97316', '#3b82f6'];
    return SEGMENTS.map((val, idx) => {
        const gift = ALL_GIFTS.find(g => (g.price || g.cost) === val) || ALL_GIFTS[0];
        return { id: idx + 1, label: val.toString(), color: colors[idx % colors.length], item: gift, price: val };
    });
  });
  const [spinRotation, setSpinRotation] = useState(0);
  const [targetRotation, setTargetRotation] = useState(0);
  const [animKey, setAnimKey] = useState(0);
  const pendingWinSegment = useRef(null);

  const handleSpin = async () => {
    if (isSpinning || balance < SPIN_COST) return;
    const userId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
    if (!userId) return;

    try {
        setIsSpinning(true);
        setWinSegment(null);
        
        // Gambling sound start
        playSound('/asset/Sounds/go-new-gambling.mp3');

        const res = await spinWheel(userId);
        if (!res.success) {
            setIsSpinning(false);
            if (res.error && window.Telegram?.WebApp) window.Telegram.WebApp.showAlert(res.error);
            return;
        }

        const winIndex = res.prize_index;
        const wonSegment = wheelSegments[winIndex];
        pendingWinSegment.current = wonSegment;

        if (window.Telegram?.WebApp?.HapticFeedback) window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy');

        const fullRotations = 10;
        const segmentOffset = 360 - (winIndex * SEGMENT_ANGLE); 
        const newTargetRotation = spinRotation + (fullRotations * 360) + segmentOffset;

        setTargetRotation(newTargetRotation);
        setAnimKey(prev => prev + 1);

        if (setBalance) setBalance(prev => Math.max(0, prev - SPIN_COST));
        if (setSpent) setSpent(prev => prev + SPIN_COST);
    } catch (error) { console.error("Spin error:", error); setIsSpinning(false); }
  };

  const handleAnimationComplete = () => {
    playSound('/asset/Sounds/win_sound.mp3');
    setWinSegment(pendingWinSegment.current);
    setIsSpinning(false);
    setSpinRotation(targetRotation % 360);
    if (onWin && pendingWinSegment.current) onWin(pendingWinSegment.current);
    if (window.Telegram?.WebApp?.HapticFeedback) window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
  };

  const generateWheelSVG = () => {
    const radius = 180; const center = 200;
    return wheelSegments.map((segment, index) => {
      const startAngle = index * SEGMENT_ANGLE; const endAngle = startAngle + SEGMENT_ANGLE;
      const startRad = (startAngle - 90) * Math.PI / 180; const endRad = (endAngle - 90) * Math.PI / 180;
      const x1 = center + radius * Math.cos(startRad); const y1 = center + radius * Math.sin(startRad);
      const x2 = center + radius * Math.cos(endRad); const y2 = center + radius * Math.sin(endRad);
      const largeArc = SEGMENT_ANGLE > 180 ? 1 : 0;
      const pathD = `M ${center} ${center} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2} Z`;
      const midAngle = (startAngle + SEGMENT_ANGLE / 2 - 90) * Math.PI / 180;
      const contentRadius = radius * 0.68; const contentX = center + contentRadius * Math.cos(midAngle); const contentY = center + contentRadius * Math.sin(midAngle);
      return (
          <g key={segment.id} className="select-none">
            <path d={pathD} fill={`${segment.color}25`} stroke={`${segment.color}60`} strokeWidth="2" style={{ filter: `drop-shadow(0 0 6px ${segment.color}80)` }} />
            <circle cx={contentX} cy={contentY} r="28" fill={`${segment.color}30`} style={{ filter: 'blur(4px)' }} />
            <image href={getDynamicGiftImage(segment.item)} x={contentX - 18} y={contentY - 20} width="36" height="36" preserveAspectRatio="xMidYMid meet" />
            <text x={contentX} y={contentY + 34} textAnchor="middle" fill="white" fontSize="12" fontWeight="900" style={{ textShadow: '0 0 5px rgba(0,0,0,0.5)' }} className="font-rounded">{segment.label}</text>
          </g>
      );
    });
  };

  const content = (
    <div className={`${isPage ? 'min-h-full overflow-y-auto p-4 pb-24' : ''}`}>
      <div className={`${!isPage ? 'glass-panel p-6 w-full max-w-lg mx-auto' : ''}`}>
        {!isPage && onClose && ( <div className="flex justify-between items-center mb-6"><h2 className="text-2xl font-black text-white font-rounded uppercase tracking-widest">Колесо Фортуны</h2><button onClick={onClose} className="text-white/50 hover:text-white text-xl font-rounded">✕</button></div> )}
        {isPage && ( <div className="mb-6 text-center"><h2 className="text-3xl font-black text-white font-rounded uppercase tracking-widest text-glow">Колесо Фортуны</h2><div className="mt-2 inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-white/5 border border-white/10"><span className="text-white/40 text-[10px] font-black uppercase tracking-[0.2em]">Стоимость: {SPIN_COST}</span><img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} /></div></div> )}

        <div className="relative w-80 h-80 mx-auto mb-10">
          <div className="absolute inset-[-15px] rounded-full animate-pulse-slow" style={{ background: 'radial-gradient(circle, rgba(168, 85, 247, 0.15) 0%, transparent 70%)' }} />
          <div className="absolute top-[-25px] left-1/2 transform -translate-x-1/2 z-40"><svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="filter drop-shadow-[0_0_10px_rgba(255,255,255,0.8)]"><path d="M12 24L2 4H22L12 24Z" fill="white" /><path d="M12 20L5 6H19L12 20Z" fill="rgba(255,255,255,0.8)" /></svg></div>
          <div className="w-full h-full rounded-full overflow-hidden relative shadow-[0_0_50px_rgba(0,0,0,0.8)]" style={{ background: '#15161a', border: '6px solid rgba(255,255,255,0.08)' }}>
             <div className="absolute inset-0 bg-gradient-to-tr from-purple-500/10 to-transparent pointer-events-none z-10" />
            <motion.div key={animKey} animate={{ rotate: targetRotation }} transition={{ duration: 5, ease: [0.12, 0, 0.39, 0] }} onAnimationComplete={handleAnimationComplete} style={{ transformOrigin: 'center center' }} className="w-full h-full">
              <svg viewBox="0 0 400 400" className="w-full h-full"><defs><radialGradient id="wheelGrad"><stop offset="0%" stopColor="rgba(255,255,255,0.05)" /><stop offset="100%" stopColor="rgba(0,0,0,0.4)" /></radialGradient></defs><circle cx="200" cy="200" r="198" fill="url(#wheelGrad)" />{generateWheelSVG()}<circle cx="200" cy="200" r="40" fill="#15161a" stroke="rgba(255,255,255,0.15)" strokeWidth="4" /><circle cx="200" cy="200" r="35" fill="rgba(168, 85, 247, 0.1)" /><image href="/asset/Icons/TelegramStar.png" x="180" y="180" width="40" height="40" preserveAspectRatio="xMidYMid meet" className="filter drop-shadow-[0_0_10px_rgba(168, 85, 247, 0.5)]" /></svg>
            </motion.div>
          </div>
        </div>

        <motion.button whileHover={{ scale: 1.02, brightness: 1.1 }} whileTap={{ scale: 0.98 }} onClick={handleSpin} disabled={isSpinning || balance < SPIN_COST} className="w-full py-5 rounded-2xl font-black text-xl disabled:opacity-50 transition-all flex items-center justify-center gap-3 uppercase tracking-wider shadow-2xl overflow-hidden relative group" style={{ backgroundColor: (isSpinning || balance < SPIN_COST) ? 'rgba(255,255,255,0.03)' : 'rgba(168, 85, 247, 0.25)', border: `2px solid ${(isSpinning || balance < SPIN_COST) ? 'rgba(255,255,255,0.08)' : 'rgba(168, 85, 247, 0.45)'}`, color: (isSpinning || balance < SPIN_COST) ? 'rgba(255,255,255,0.15)' : '#c084fc' }}>
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/5 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
            {isSpinning ? ( <div className="flex items-center justify-center gap-3 font-rounded"><motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} className="w-6 h-6 border-3 border-purple-400/30 border-t-purple-400 rounded-full" />Крутим...</div> ) : ( <span className="flex items-center justify-center gap-2 font-rounded">ИСПЫТАТЬ УДАЧУ ({SPIN_COST} <img src="/asset/Icons/TelegramStar.png" className="h-6 w-6" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} />)</span> )}
        </motion.button>

        <AnimatePresence>
          {winSegment && (
            <motion.div initial={{ opacity: 0, scale: 0.8, y: 30 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.8 }} className="mt-8 text-center p-8 rounded-3xl border-2 relative overflow-hidden bg-[#1a1b1f]" style={{ borderColor: `${winSegment.color}50`, boxShadow: `0 0 50px ${winSegment.color}20` }}>
              <div className="absolute inset-0 bg-gradient-to-b from-white/[0.05] to-transparent pointer-events-none" />
              <p className="text-white/40 text-[10px] mb-4 uppercase font-black tracking-[0.3em] font-rounded">Поздравляем!</p>
              <div className="relative mb-6"><div className="absolute inset-0 bg-white/10 blur-3xl rounded-full scale-75 opacity-50" /><motion.div animate={{ y: [0, -10, 0], rotate: [0, 5, -5, 0] }} transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}><img src={getDynamicGiftImage(winSegment.item)} alt={winSegment.label} className="h-36 w-32 object-contain mx-auto relative z-10" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} style={{ filter: `drop-shadow(0 0 30px ${winSegment.color}90)` }} /></motion.div></div>
              <p className="text-white font-black text-5xl mb-2 flex items-center justify-center gap-3 font-rounded" style={{ color: winSegment.color, textShadow: `0 0 30px ${winSegment.color}60` }}>{winSegment.label} <img src="/asset/Icons/TelegramStar.png" className="h-10 w-10" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} /></p>
              <p className="text-white/40 text-[10px] uppercase font-bold tracking-widest mt-3">Выигрыш зачислен на баланс</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );

  if (isPage) return content;
  return ( <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-xl p-4">{content}</motion.div> );
}
