import React, { useState, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Confetti from 'react-confetti';
import { ALL_GIFTS } from '../../giftData';
import { upgradeItem, fetchBalance } from '../../api';
import { DEFAULT_GIFT_IMAGE, getDynamicGiftImage } from '../../giftUtils';

export default function UpgradeGame({ isPage, inventory, setInventory, balance, setBalance, setSpent }) {
  const [selectedSlot1, setSelectedSlot1] = useState(null);
  const [selectedSlot2, setSelectedSlot2] = useState(null);
  const [isUpgrading, setIsUpgrading] = useState(false);
  const [result, setResult] = useState(null);
  const [showConfetti, setShowConfetti] = useState(false);
  const [showGiftSelector, setShowGiftSelector] = useState(false);
  const [arrowRotation, setArrowRotation] = useState(0);
  const [animKey, setAnimKey] = useState(0);
  const pendingResult = useRef(null);

  const triggerHaptic = () => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy');
    }
  };

  const successChance = useMemo(() => {
    if (!selectedSlot1 || !selectedSlot2 || (selectedSlot2?.price || selectedSlot2?.cost || 0) <= (selectedSlot1?.price || selectedSlot1?.cost || 0) || (selectedSlot2?.price || selectedSlot2?.cost || 0) === 0) return 0;
    const p1 = selectedSlot1?.price || selectedSlot1?.cost || 0;
    const p2 = selectedSlot2?.price || selectedSlot2?.cost || 0;
    return parseFloat(((p1 / p2) * 100).toFixed(2));
  }, [selectedSlot1, selectedSlot2]);

  const upgradeCost = useMemo(() => {
    if (!selectedSlot1) return 0;
    return Math.ceil((selectedSlot1?.price || selectedSlot1?.cost || 0) * 0.5);
  }, [selectedSlot1]);

  const eligibleTargets = useMemo(() => {
    if (!selectedSlot1) return [];
    const p1 = selectedSlot1?.price || selectedSlot1?.cost || 0;
    return ALL_GIFTS.filter(g => (g.price || g.cost || 0) > p1 && (g.price || g.cost || 0) >= 15);
  }, [selectedSlot1]);

  const handleUpgrade = async () => {
    if (isUpgrading || !selectedSlot1 || !selectedSlot2) return;

    if (balance < upgradeCost) {
      if (window.Telegram?.WebApp) {
          window.Telegram.WebApp.showAlert(`❌ Недостаточно средств! Нужно ${upgradeCost} ⭐`);
      }
      return;
    }

    const userId = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
    if (!userId) return;

    try {
        triggerHaptic();
        setIsUpgrading(true);
        setResult(null);
        setShowConfetti(false);

        // 1. Call backend /api/upgrade
        const res = await upgradeItem(userId, upgradeCost, successChance);
        
        // 2. Determine success from server
        const success = res.success;
        pendingResult.current = success;

        const greenAngle = (successChance / 100) * 360;

        let targetAngle;
        if (success) {
          // Point to green area
          targetAngle = Math.random() * greenAngle;
        } else {
          // Point to gray area
          targetAngle = greenAngle + Math.random() * (360 - greenAngle);
        }

        const totalRotation = (8 * 360) + targetAngle;

        setArrowRotation(totalRotation);
        setAnimKey(prev => prev + 1);
        
        // Refresh balance
        const balanceData = await fetchBalance(userId);
        if (setBalance) setBalance(balanceData.stars);

    } catch (error) {
        console.error("Upgrade error:", error);
        setIsUpgrading(false);
    }
  };

  const handleAnimationComplete = () => {
    const success = pendingResult.current;

    if (success) {
      const upgradedItem = {
        ...selectedSlot1,
        id: Date.now(),
        price: selectedSlot2?.price || selectedSlot2?.cost || 0,
        name: selectedSlot2?.name || 'Upgraded Item',
        image: selectedSlot2?.image || '',
      };

      setInventory(prev => {
        const newInv = prev.filter(i => i.id !== selectedSlot1.id);
        return [upgradedItem, ...newInv];
      });

      setResult('success');
      setShowConfetti(true);
      setTimeout(() => setShowConfetti(false), 3000);
    } else {
      setInventory(prev => prev.filter(i => i.id !== selectedSlot1.id));
      setResult('fail');
    }

    setSelectedSlot1(null);
    setSelectedSlot2(null);
    setIsUpgrading(false);
  };

  const renderChanceCircle = () => {
    const radius = 80;
    const displayChance = successAngleFromChance(successChance);
    
    return (
      <div className="relative w-48 h-48 mx-auto">
        <svg viewBox="0 0 200 200" className="w-full h-full">
          <circle cx="100" cy="100" r={radius} fill="rgba(255,255,255,0.02)" stroke="rgba(255,255,255,0.1)" strokeWidth="4" />
          
          {successChance < 100 && (
            <path
              d={describeArc(100, 100, radius, successChance, 100)}
              fill="rgba(107, 114, 128, 0.4)"
              className="transition-all duration-500"
            />
          )}
          {successChance > 0 && (
            <path
              d={describeArc(100, 100, radius, 0, successChance)}
              fill="rgba(34, 197, 94, 0.4)"
              className="transition-all duration-500"
              style={{ filter: 'drop-shadow(0 0 10px rgba(34, 197, 94, 0.5))' }}
            />
          )}

          <text x="100" y="95" textAnchor="middle" dominantBaseline="central" fill="white" fontSize="28" fontWeight="900" className="font-rounded drop-shadow-md">
            {successChance}%
          </text>
          <text x="100" y="115" textAnchor="middle" dominantBaseline="central" fill="rgba(255,255,255,0.5)" fontSize="10" className="font-rounded uppercase tracking-widest font-black">
            шанс
          </text>
        </svg>

        <motion.div
          key={animKey}
          animate={{ rotate: arrowRotation }}
          transition={{
            duration: 4,
            ease: [0.12, 0, 0.39, 0],
          }}
          onAnimationComplete={handleAnimationComplete}
          className="absolute top-[-10px] left-1/2 transform -translate-x-1/2 z-30"
          style={{ transformOrigin: '50% 110px' }}
        >
          <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <path d="M12 24L2 4H22L12 24Z" fill="white" className="drop-shadow-glow" />
            <path d="M12 20L4 6H20L12 20Z" fill="rgba(255,255,255,0.8)" />
          </svg>
        </motion.div>
      </div>
    );
  };

  function successAngleFromChance(chance) {
    return (chance / 100) * 360;
  }

  function describeArc(x, y, radius, startPercent, endPercent) {
    const startAngle = (startPercent / 100) * 360;
    const endAngle = (endPercent / 100) * 360;
    
    const start = polarToCartesian(x, y, radius, endAngle - 90);
    const end = polarToCartesian(x, y, radius, startAngle - 90);
    const largeArcFlag = endAngle - startAngle <= 180 ? 0 : 1;

    return [
      "M", x, y,
      "L", start.x, start.y,
      "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y,
      "Z"
    ].join(" ");
  }

  function polarToCartesian(centerX, centerY, radius, angleInDegrees) {
    const angleInRadians = (angleInDegrees) * Math.PI / 180.0;
    return {
      x: centerX + (radius * Math.cos(angleInRadians)),
      y: centerY + (radius * Math.sin(angleInRadians))
    };
  }

  const content = (
    <div className={`${isPage ? 'p-4 min-h-full pb-24' : ''}`}>
      <div className={`${!isPage ? 'glass-panel p-6 w-full max-w-lg mx-auto' : ''}`}>
        {!isPage && (
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-black text-white font-rounded uppercase tracking-widest">Апгрейд</h2>
          </div>
        )}
        {isPage && (
          <div className="mb-6">
            <h2 className="text-3xl font-black text-white font-rounded uppercase tracking-widest">Апгрейд</h2>
            <p className="text-white/40 text-xs uppercase font-bold tracking-widest mt-1">Улучшай предметы и повышай их ценность</p>
          </div>
        )}

        {!inventory || inventory.length === 0 ? (
          <div className="glass-panel p-12 text-center border-white/10 bg-white/5">
            <p className="text-white/30 font-rounded text-sm uppercase font-black tracking-widest">Инвентарь пуст. Открывайте ящики!</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="glass-panel p-6 border-white/10 relative overflow-hidden">
               <div className="absolute inset-0 bg-gradient-to-b from-white/[0.02] to-transparent pointer-events-none" />
              
              <div className="flex items-center justify-center mb-6">
                <div className="p-3 rounded-full bg-white/5 border border-white/10">
                   <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.4)" strokeWidth="3" strokeLinecap="round">
                    <path d="M12 5v14M5 12l7 7 7-7" />
                  </svg>
                </div>
              </div>

              <div className="flex items-center justify-center gap-6 mb-6">
                <div className="flex-1 text-center">
                  <h4 className="text-white/40 text-[10px] uppercase tracking-widest mb-3 font-black">Мой предмет</h4>
                  {!selectedSlot1 ? (
                    <div className="w-32 h-32 mx-auto rounded-3xl border-2 border-dashed border-white/10 bg-white/[0.02] flex items-center justify-center">
                      <span className="text-white/20 text-3xl font-black">?</span>
                    </div>
                  ) : (
                    <motion.div 
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      className="p-4 rounded-3xl bg-white/[0.05] border border-white/10 relative group"
                    >
                      <img src={getDynamicGiftImage(selectedSlot1)} alt={selectedSlot1?.name || 'Gift'} className="w-24 h-24 object-contain mx-auto relative z-10" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                      <div className="flex items-center justify-center gap-1.5 text-sm text-white font-black font-rounded mt-3">
                        {selectedSlot1?.price || selectedSlot1?.cost || 0}
                        <img src="/asset/Icons/TelegramStar.png" className="h-5 w-5" alt="Stars" />
                      </div>
                    </motion.div>
                  )}
                </div>

                <div className="text-white/20 text-3xl font-black pt-8">→</div>

                <div className="flex-1 text-center">
                  <h4 className="text-white/40 text-[10px] uppercase tracking-widest mb-3 font-black">Желаемый</h4>
                  {!selectedSlot2 ? (
                    <motion.button
                      whileHover={{ scale: 1.05, borderColor: 'rgba(34, 197, 94, 0.3)', backgroundColor: 'rgba(34, 197, 94, 0.05)' }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => {
                        setShowGiftSelector(true);
                        triggerHaptic();
                      }}
                      className="w-32 h-32 mx-auto rounded-3xl border-2 border-dashed border-white/10 bg-white/[0.02] transition-all flex items-center justify-center"
                    >
                      <span className="text-white/20 text-5xl font-black">+</span>
                    </motion.button>
                  ) : (
                    <motion.div 
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      className="p-4 rounded-3xl bg-green-500/10 border border-green-500/30 relative group"
                    >
                       <div className="absolute inset-0 bg-green-500/10 blur-xl rounded-full scale-75 opacity-50" />
                      <img src={getDynamicGiftImage(selectedSlot2)} alt={selectedSlot2?.name || 'Target'} className="w-24 h-24 object-contain mx-auto relative z-10" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                      <div className="flex items-center justify-center gap-1.5 text-sm text-green-400 font-black font-rounded mt-3 relative z-10">
                        {selectedSlot2?.price || selectedSlot2?.cost || 0}
                        <img src="/asset/Icons/TelegramStar.png" className="h-5 w-5" alt="Stars" />
                      </div>
                    </motion.div>
                  )}
                </div>
              </div>

              {selectedSlot1 && selectedSlot2 && renderChanceCircle()}
            </div>

            {selectedSlot1 && selectedSlot2 && (
              <UpgradeButtonContent
                canUpgrade={balance >= upgradeCost}
                isUpgrading={isUpgrading}
                upgradeCost={upgradeCost}
                handleUpgrade={handleUpgrade}
              />
            )}

            <AnimatePresence>
              {result && (
                <motion.div
                  initial={{ opacity: 0, scale: 0.8, y: 20 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.8 }}
                  className={`text-center p-8 rounded-3xl border-2 ${
                    result === 'success'
                      ? 'border-green-500/40 bg-green-500/10 shadow-[0_0_30px_rgba(34,197,94,0.1)]'
                      : 'border-red-500/40 bg-red-500/10 shadow-[0_0_30px_rgba(239,68,68,0.1)]'
                  }`}
                >
                  <p className={`font-black text-3xl mb-2 font-rounded uppercase tracking-tight ${
                    result === 'success' ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {result === 'success' ? 'УСПЕХ!' : 'ПРОВАЛ!'}
                  </p>
                  <p className="text-white/60 text-sm font-bold uppercase tracking-widest">
                    {result === 'success'
                      ? 'Предмет улучшен!'
                      : 'Предмет потерян...'}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="glass-panel p-6 border-white/10">
              <h3 className="text-white/60 font-black text-xs mb-4 uppercase tracking-[0.2em]">Выберите свой предмет</h3>
              <div className="grid grid-cols-3 gap-3 max-h-64 overflow-y-auto pr-1">
                {inventory.map(item => (
                  <motion.div
                    key={item.id}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => {
                      setSelectedSlot1(item);
                      setResult(null);
                      setSelectedSlot2(null);
                      triggerHaptic();
                    }}
                    className={`p-3 rounded-2xl border-2 cursor-pointer transition-all flex flex-col items-center ${
                      selectedSlot1?.id === item.id
                        ? 'border-white/40 bg-white/10 shadow-lg'
                        : 'border-white/5 bg-white/[0.02] hover:border-white/20'
                    }`}
                  >
                    <img src={getDynamicGiftImage(item)} alt={item?.name || 'Gift'} className="w-16 h-16 object-contain mb-2 mx-auto" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                    <span className="text-white text-[10px] font-bold text-center truncate block font-rounded w-full">{item?.name || 'Gift'}</span>
                    <div className="flex items-center justify-center gap-1 text-white/50 text-[11px] mt-1.5 font-black font-rounded">
                       {item?.price || item?.cost || 0}
                       <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3" alt="Stars" />
                    </div>
                  </motion.div>
                ))}
              </div>
            </div>
          </div>
        )}

        <AnimatePresence>
          {showGiftSelector && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4"
            >
              <motion.div
                initial={{ scale: 0.9, y: 30 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 30 }}
                className="glass-panel w-full max-w-lg mx-4 max-h-[85vh] overflow-hidden flex flex-col p-6 border-white/20 bg-[#1a1b1f]"
              >
                <div className="flex justify-between items-center mb-6">
                  <h3 className="text-white font-black text-2xl uppercase tracking-tight">Цель апгрейда</h3>
                  <button onClick={() => setShowGiftSelector(false)} className="text-white/40 hover:text-white text-2xl transition-colors">✕</button>
                </div>
                
                {selectedSlot1 && (
                  <div className="mb-6 px-4 py-3 rounded-2xl bg-white/5 border border-white/10">
                     <p className="text-white/40 text-[10px] font-black uppercase tracking-widest">
                      Доступны предметы дороже {selectedSlot1?.price || selectedSlot1?.cost || 0}
                      <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3 inline mx-1 mb-0.5" alt="Stars" />
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-3 gap-3 overflow-y-auto pr-2 pb-4">
                  {eligibleTargets.map((gift, idx) => (
                    <motion.div
                      key={idx}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => {
                        setSelectedSlot2(gift);
                        setShowGiftSelector(false);
                        triggerHaptic();
                      }}
                      className={`p-4 rounded-2xl border-2 cursor-pointer transition-all flex flex-col items-center ${
                        selectedSlot2?.name === gift.name
                          ? 'border-green-500/50 bg-green-500/10'
                          : 'border-white/5 bg-white/[0.03] hover:border-white/20'
                      }`}
                    >
                      <img src={getDynamicGiftImage(gift)} alt={gift?.name || 'Gift'} className="w-20 h-20 object-contain mb-3 mx-auto" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                      <p className="text-white text-[10px] font-black text-center truncate block font-rounded w-full mb-1">{gift?.name || 'Gift'}</p>
                      <div className="flex items-center justify-center gap-1 text-green-400 text-[11px] font-black font-rounded">
                          {gift?.price || gift?.cost || 0}
                          <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3" alt="Stars" />
                      </div>
                    </motion.div>
                  ))}
                  {eligibleTargets.length === 0 && selectedSlot1 && (
                    <div className="col-span-3 py-16 text-center">
                       <p className="text-white/20 text-sm font-black uppercase tracking-[0.2em]">Нет подходящих целей</p>
                    </div>
                  )}
                </div>
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {showConfetti && (
          <div className="fixed inset-0 z-[100] pointer-events-none">
            <Confetti
              width={window.innerWidth}
              height={window.innerHeight}
              recycle={false}
              numberOfPieces={300}
              colors={['#22c55e', '#4ade80', '#86efac', '#ffffff']}
            />
          </div>
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
    >
      {content}
    </motion.div>
  );
}

function UpgradeButtonContent({ canUpgrade, isUpgrading, upgradeCost, handleUpgrade }) {
  if (isUpgrading) {
    return (
      <div className="w-full py-5 rounded-2xl font-black text-xl flex items-center justify-center gap-3 bg-green-500/10 border-2 border-green-500/40 text-green-400 font-rounded uppercase tracking-tight shadow-lg shadow-green-500/10">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-6 h-6 border-3 border-green-400/30 border-t-green-400 rounded-full"
        />
        Апгрейдим...
      </div>
    );
  }

  return (
    <div className="w-full space-y-3">
      <motion.button
        whileHover={{ scale: canUpgrade ? 1.02 : 1, filter: canUpgrade ? 'brightness(1.1)' : 'none' }}
        whileTap={{ scale: canUpgrade ? 0.98 : 1 }}
        onClick={() => {
          handleUpgrade();
        }}
        disabled={isUpgrading || !canUpgrade}
        className="w-full py-5 rounded-2xl font-black text-xl disabled:opacity-50 transition-all flex items-center justify-center gap-2 uppercase tracking-tight"
        style={{
          backgroundColor: canUpgrade ? 'rgba(34, 197, 94, 0.2)' : 'rgba(255, 255, 255, 0.03)',
          border: `2px solid ${canUpgrade ? 'rgba(34, 197, 94, 0.5)' : 'rgba(255, 255, 255, 0.05)'}`,
          color: canUpgrade ? '#22c55e' : 'rgba(255,255,255,0.2)',
          boxShadow: canUpgrade ? '0 0 20px rgba(34, 197, 94, 0.15)' : 'none',
        }}
      >
        Апгрейд ({upgradeCost}
        <img src="/asset/Icons/TelegramStar.png" className="h-6 w-6" alt="Stars" />)
      </motion.button>
      {!canUpgrade && !isUpgrading && (
        <p className="text-red-500/60 text-[10px] text-center font-black uppercase tracking-[0.2em] animate-pulse">
          Недостаточно звёзд
        </p>
      )}
    </div>
  );
}
