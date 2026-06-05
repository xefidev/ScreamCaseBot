import React, { useState, useRef, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ALL_GIFTS } from '../../giftData';
import { spinWheel } from '../../api';
import { DEFAULT_GIFT_IMAGE, getDynamicGiftImage } from '../../giftUtils';

import { playSound } from '../../App';

const SEGMENT_ANGLE = 360 / 12;
const SPIN_COST = 50;

export default function WheelGame({ onClose, isPage, onWin, balance = 0, setBalance = null, setSpent = null }) {
  const [isSpinning, setIsSpinning] = useState(false);
  const [winSegment, setWinSegment] = useState(null);
  
  const wheelSegments = useMemo(() => {
    // Выбираем 12 уникальных подарков из разных ценовых категорий
    const selectedItems = [
      ALL_GIFTS.find(g => g.name === 'Rosae') || ALL_GIFTS[0],
      ALL_GIFTS.find(g => g.name === 'Flowers') || ALL_GIFTS[5],
      ALL_GIFTS.find(g => g.name === 'Xmas Stockings') || ALL_GIFTS[7],
      ALL_GIFTS.find(g => g.name === 'Jester Hats') || ALL_GIFTS[11],
      ALL_GIFTS.find(g => g.name === 'Magic Potions') || ALL_GIFTS[17],
      ALL_GIFTS.find(g => g.name === 'Ice Creams') || ALL_GIFTS[25],
      ALL_GIFTS.find(g => g.name === 'Scared Cats') || ALL_GIFTS[30],
      ALL_GIFTS.find(g => g.name === 'Victory Medals') || ALL_GIFTS[33],
      ALL_GIFTS.find(g => g.name === 'Voodoo Dolls') || ALL_GIFTS[36],
      ALL_GIFTS.find(g => g.name === 'Diamond Rings') || ALL_GIFTS[55],
      ALL_GIFTS.find(g => g.name === 'Mini Oscars') || ALL_GIFTS[76],
      ALL_GIFTS.find(g => g.name === 'Low Riders') || ALL_GIFTS[88],
    ];

    const colors = [
      '#ff4444', '#44ff44', '#4444ff', '#ffff44', 
      '#ff44ff', '#44ffff', '#ff8844', '#8844ff', 
      '#44ff88', '#ffbc00', '#00d2ff', '#9d50bb'
    ];

    return selectedItems.map((item, idx) => ({
      id: idx + 1,
      label: item.price.toString(),
      color: colors[idx],
      item: item,
      price: item.price
    }));
  }, []);

  const [spinRotation, setSpinRotation] = useState(0);
  const [targetRotation, setTargetRotation] = useState(0);
  const [animKey, setAnimKey] = useState(0);
  const pendingWinSegment = useRef(null);

  const handleSpin = async () => {
    if (isSpinning) return;
    
    if (balance < SPIN_COST) {
      window?.Telegram?.WebApp?.showConfirm?.(
        `Недостаточно звёзд! Стоимость вращения: ${SPIN_COST} ⭐. Пополнить баланс?`,
        (ok) => {
          if (ok) window?.Telegram?.WebApp?.showAlert?.("Перейдите в профиль для пополнения!");
        }
      );
      return;
    }

    const userId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
    if (!userId) return;

    try {
        setIsSpinning(true);
        setWinSegment(null);
        
        playSound('/asset/Sounds/go-new-gambling.mp3');

        const res = await spinWheel(userId);
        if (!res.success) {
            setIsSpinning(false);
            if (res.error && window.Telegram?.WebApp) window.Telegram.WebApp.showAlert(res.error);
            return;
        }

        // Сервер возвращает реальный item ({name, price, image}). Маппим его на ближайший сектор.
        const wonItem = res.item || {};
        let winIndex = wheelSegments.findIndex(s => s.item?.name === wonItem.name);
        if (winIndex === -1 && typeof wonItem.price === 'number') {
            let bestIdx = 0, bestDiff = Infinity;
            wheelSegments.forEach((s, i) => {
                const d = Math.abs((s.price || 0) - wonItem.price);
                if (d < bestDiff) { bestDiff = d; bestIdx = i; }
            });
            winIndex = bestIdx;
        }
        if (winIndex === -1) winIndex = 0;

        // Подменяем отображаемый item на реальный выигрыш с сервера
        const wonSegment = {
            ...wheelSegments[winIndex],
            item: wonItem.name ? wonItem : wheelSegments[winIndex].item,
            price: wonItem.price ?? wheelSegments[winIndex].price,
            label: (wonItem.price ?? wheelSegments[winIndex].price).toString()
        };
        pendingWinSegment.current = wonSegment;

        if (window.Telegram?.WebApp?.HapticFeedback) window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy');

        const fullRotations = 10;
        // Смещение к ЦЕНТРУ сектора, иначе стрелка попадает на границу
        const segmentOffset = 360 - (winIndex * SEGMENT_ANGLE) - (SEGMENT_ANGLE / 2);
        const newTargetRotation = spinRotation + (fullRotations * 360) + segmentOffset;

        setTargetRotation(newTargetRotation);
        setAnimKey(prev => prev + 1);

        if (setBalance) setBalance(prev => Math.max(0, prev - SPIN_COST));
        if (setSpent) setSpent(prev => prev + SPIN_COST);
    } catch (error) { console.error("Spin error:", error); setIsSpinning(false); }
  };

  const handleAnimationComplete = () => {
    setTimeout(() => {
      playSound('/asset/Sounds/win_sound.mp3');
    }, 500);
    
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
            <image href={getDynamicGiftImage(segment.item)} x={contentX - 18} y={contentY - 20} width="36" height="36" preserveAspectRatio="xMidYMid meet" loading="lazy" />
            <text x={contentX} y={contentY + 34} textAnchor="middle" fill="white" fontSize="12" fontWeight="900" style={{ textShadow: '0 0 5px rgba(0,0,0,0.5)' }} className="font-rounded">{segment.label}</text>
          </g>
      );
    });
  };

  const content = (
    <div className={`${isPage ? 'h-full overflow-y-auto p-4 pb-24' : ''} bg-[#1a1b1e]`}>
      <div className={`${!isPage ? 'glass-panel p-8 w-full max-w-lg mx-auto relative' : ''}`}>
        {!isPage && onClose && ( 
          <button 
            onClick={onClose} 
            className="absolute top-4 right-4 w-10 h-10 flex items-center justify-center rounded-xl bg-white/5 border border-white/10 text-white/50 hover:text-white transition-all z-50"
          >
            ✕
          </button> 
        )}
        
        <div className="mb-8 text-center pt-4">
          <h2 className="text-3xl font-black text-white font-rounded uppercase tracking-tight text-glow">Колесо Фортуны</h2>
          <div className="mt-3 inline-flex items-center gap-3 px-5 py-2 rounded-2xl bg-white/5 border border-white/10 backdrop-blur-md">
            <span className="text-white/40 text-[10px] font-black uppercase tracking-[0.2em]">Стоимость: {SPIN_COST}</span>
            <img src="/asset/Icons/TelegramStar.png" className="h-5 w-5" alt="Stars" onError={(e) = loading="lazy" decoding="async"> { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
          </div>
        </div>

        <div className="relative w-80 h-80 mx-auto mb-10">
          <div className="absolute inset-[-20px] rounded-full animate-pulse-slow opacity-50" style={{ background: 'radial-gradient(circle, rgba(168, 85, 247, 0.2) 0%, transparent 70%)' }} />
          <div className="absolute top-[-25px] left-1/2 transform -translate-x-1/2 z-40 filter drop-shadow-[0_0_15px_rgba(255,255,255,0.5)]">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 24L2 4H22L12 24Z" fill="white" />
              <path d="M12 20L5 6H19L12 20Z" fill="rgba(255,255,255,0.8)" />
            </svg>
          </div>
          <div className="w-full h-full rounded-full overflow-hidden relative shadow-[0_0_60px_rgba(0,0,0,0.6)]" style={{ background: '#15161a', border: '8px solid rgba(255,255,255,0.05)' }}>
            <div className="absolute inset-0 bg-gradient-to-tr from-purple-500/10 via-transparent to-white/5 pointer-events-none z-10" />
            <motion.div key={animKey} animate={{ rotate: targetRotation }} transition={{ duration: 5, ease: [0.12, 0, 0.39, 0] }} onAnimationComplete={handleAnimationComplete} style={{ transformOrigin: 'center center' }} className="w-full h-full">
              <svg viewBox="0 0 400 400" className="w-full h-full">
                <defs>
                  <radialGradient id="wheelGrad">
                    <stop offset="0%" stopColor="rgba(255,255,255,0.05)" />
                    <stop offset="100%" stopColor="rgba(0,0,0,0.4)" />
                  </radialGradient>
                </defs>
                <circle cx="200" cy="200" r="198" fill="url(#wheelGrad)" />
                {generateWheelSVG()}
                <circle cx="200" cy="200" r="45" fill="#15161a" stroke="rgba(255,255,255,0.1)" strokeWidth="4" />
                <circle cx="200" cy="200" r="38" fill="rgba(168, 85, 247, 0.1)" />
                <image href="/asset/Icons/TelegramStar.png" x="178" y="178" width="44" height="44" className="filter drop-shadow-[0_0_15px_rgba(168,85,247,0.6)]" />
              </svg>
            </motion.div>
          </div>
        </div>

        <div className="px-4">
          <motion.button 
            whileHover={{ scale: 1.02 }} 
            whileTap={{ scale: 0.98 }} 
            onClick={handleSpin} 
            disabled={isSpinning} 
            className="w-full py-5 rounded-3xl font-black text-xl transition-all flex items-center justify-center gap-3 uppercase tracking-widest shadow-2xl overflow-hidden relative group" 
            style={{ 
              backgroundColor: isSpinning ? 'rgba(255,255,255,0.03)' : 'rgba(168, 85, 247, 0.2)', 
              border: `2px solid ${isSpinning ? 'rgba(255,255,255,0.1)' : 'rgba(168, 85, 247, 0.4)'}`, 
              color: isSpinning ? 'rgba(255,255,255,0.2)' : '#c084fc' 
            }}
          >
              <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-1000" />
              {isSpinning ? ( 
                <div className="flex items-center justify-center gap-3 font-rounded">
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} className="w-6 h-6 border-3 border-purple-400/30 border-t-purple-400 rounded-full" />
                  Крутим...
                </div> 
              ) : ( 
                <span className="flex items-center justify-center gap-2 font-rounded">
                  ИСПЫТАТЬ УДАЧУ
                </span> 
              )}
          </motion.button>
        </div>

        <AnimatePresence>
          {winSegment && (
            <motion.div initial={{ opacity: 0, scale: 0.8, y: 30 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.8 }} className="mt-8 text-center p-8 rounded-[2rem] border-2 relative overflow-hidden bg-[#1a1b1f] shadow-[0_20px_50px_rgba(0,0,0,0.5)]" style={{ borderColor: `${winSegment.color}40` }}>
              <div className="absolute inset-0 bg-gradient-to-b from-white/[0.03] to-transparent pointer-events-none" />
              <div className="absolute -top-24 -left-24 w-48 h-48 rounded-full blur-[80px] opacity-20" style={{ backgroundColor: winSegment.color }} />
              
              <p className="text-white/40 text-[10px] mb-6 uppercase font-black tracking-[0.4em] font-rounded">Поздравляем!</p>
              
              <div className="relative mb-8">
                <div className="absolute inset-0 blur-3xl rounded-full scale-75 opacity-30" style={{ backgroundColor: winSegment.color }} />
                <motion.div 
                  animate={{ y: [0, -12, 0], rotate: [0, 5, -5, 0] }} 
                  transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                >
                  <img 
                    src={getDynamicGiftImage(winSegment.item)} 
                    alt={winSegment.item.name} 
                    className="h-44 w-44 object-contain mx-auto relative z-10" 
                    onError={(e) = loading="lazy" decoding="async"> { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} 
                    style={{ filter: `drop-shadow(0 0 40px ${winSegment.color}80)` }} 
                  />
                </motion.div>
              </div>

              <h3 className="text-white font-black text-3xl mb-1 font-rounded uppercase tracking-tighter" style={{ color: winSegment.color }}>
                {winSegment.item.name}
              </h3>
              <p className="text-white/30 text-[10px] uppercase font-bold tracking-[0.2em] mb-4">Стоимость: {winSegment.price} ⭐</p>
              <div className="w-full h-px bg-white/5 mb-4" />
              <p className="text-white/40 text-[9px] uppercase font-black tracking-widest">Выигрыш добавлен в ваш инвентарь</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );

  if (isPage) return content;
  return ( <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-xl p-4">{content}</motion.div> );
}
