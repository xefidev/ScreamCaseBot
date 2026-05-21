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

  const triggerHaptic = (type = 'heavy') => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred(type);
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

        const res = await upgradeItem(userId, upgradeCost, successChance);
        
        const success = res.success;
        pendingResult.current = success;

        const greenAngle = (successChance / 100) * 360;

        let targetAngle;
        if (success) {
          targetAngle = (Math.random() * (greenAngle - 10)) + 5; // Safety margin
        } else {
          targetAngle = greenAngle + (Math.random() * (350 - greenAngle)) + 5;
        }

        const totalRotation = (10 * 360) + targetAngle;

        setArrowRotation(totalRotation);
        setAnimKey(prev => prev + 1);
        
        if (setBalance) {
          const balanceData = await fetchBalance(userId);
          setBalance(balanceData.stars);
        }

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
      triggerHaptic('success');
    } else {
      setInventory(prev => prev.filter(i => i.id !== selectedSlot1.id));
      setResult('fail');
      if (window.Telegram?.WebApp?.HapticFeedback) {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('error');
      }
    }

    setSelectedSlot1(null);
    setSelectedSlot2(null);
    setIsUpgrading(false);
  };

  const renderChanceCircle = () => {
    const radius = 80;
    
    return (
      <div className="relative w-48 h-48 mx-auto mt-6">
        <div className="absolute inset-0 rounded-full bg-white/[0.02] shadow-[inset_0_0_20px_rgba(0,0,0,0.5)]" />
        
        <svg viewBox="0 0 200 200" className="w-full h-full rotate-[-90deg]">
          <circle cx="100" cy="100" r={radius} fill="none" stroke="rgba(255,255,255,0.05)" strokeWidth="8" />
          
          {successChance < 100 && (
            <path
              d={describeArc(100, 100, radius, successChance, 100)}
              fill="none"
              stroke="rgba(107, 114, 128, 0.4)"
              strokeWidth="10"
              strokeLinecap="round"
            />
          )}
          {successChance > 0 && (
            <path
              d={describeArc(100, 100, radius, 0, successChance)}
              fill="none"
              stroke="rgba(34, 197, 94, 0.6)"
              strokeWidth="12"
              strokeLinecap="round"
              className="filter drop-shadow-[0_0_8px_rgba(34,197,94,0.5)]"
            />
          )}
        </svg>

        <div className="absolute inset-0 flex flex-col items-center justify-center rotate-0">
          <span className="text-4xl font-black text-white drop-shadow-glow">{successChance}%</span>
          <span className="text-[10px] font-black uppercase tracking-[0.2em] text-white/30">Шанс</span>
        </div>

        <motion.div
          key={animKey}
          animate={{ rotate: arrowRotation }}
          transition={{
            duration: 5,
            ease: [0.12, 0, 0.39, 0],
          }}
          onAnimationComplete={handleAnimationComplete}
          className="absolute top-[-15px] left-1/2 transform -translate-x-1/2 z-30"
          style={{ transformOrigin: '50% 115px' }}
        >
          <svg width="32" height="32" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg" className="filter drop-shadow-[0_0_5px_rgba(255,255,255,0.8)]">
            <path d="M12 24L2 4H22L12 24Z" fill="white" />
            <path d="M12 20L5 6H19L12 20Z" fill="rgba(255,255,255,0.8)" />
          </svg>
        </motion.div>
      </div>
    );
  };

  function describeArc(x, y, radius, startPercent, endPercent) {
    const startAngle = (startPercent / 100) * 360;
    const endAngle = (endPercent / 100) * 360;
    
    const start = polarToCartesian(x, y, radius, endAngle);
    const end = polarToCartesian(x, y, radius, startAngle);
    const largeArcFlag = endAngle - startAngle <= 180 ? 0 : 1;

    return [
      "M", start.x, start.y,
      "A", radius, radius, 0, largeArcFlag, 0, end.x, end.y
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
          <div className="mb-6 text-center">
            <h2 className="text-3xl font-black text-white font-rounded uppercase tracking-widest text-glow">Апгрейд</h2>
            <p className="text-white/40 text-[10px] uppercase font-black tracking-[0.2em] mt-2">Улучшай свои предметы</p>
          </div>
        )}

        {!inventory || inventory.length === 0 ? (
          <div className="glass-panel p-16 text-center border-white/5 bg-white/[0.02]">
            <p className="text-white/20 font-black text-xs uppercase tracking-[0.3em]">Инвентарь пуст</p>
          </div>
        ) : (
          <div className="space-y-6">
            <div className="glass-panel p-8 border-white/10 relative overflow-hidden bg-[#1a1b1f]">
               <div className="absolute inset-0 bg-gradient-to-br from-white/[0.03] to-transparent pointer-events-none" />
              
              <div className="flex items-center justify-center gap-6 mb-2">
                <div className="flex-1 text-center">
                  <h4 className="text-white/30 text-[9px] uppercase tracking-widest mb-4 font-black">Текущий</h4>
                  {!selectedSlot1 ? (
                    <div className="w-32 h-32 mx-auto rounded-3xl border-2 border-dashed border-white/10 bg-white/[0.01] flex items-center justify-center">
                      <span className="text-white/10 text-4xl font-black">?</span>
                    </div>
                  ) : (
                    <motion.div 
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      className="p-5 rounded-3xl bg-white/5 border border-white/10 relative shadow-2xl"
                    >
                      <img src={getDynamicGiftImage(selectedSlot1)} alt="Item" className="w-24 h-24 object-contain mx-auto relative z-10" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                      <div className="flex items-center justify-center gap-1.5 text-xs text-white/70 font-black font-rounded mt-4 bg-black/40 py-1.5 rounded-xl">
                        {selectedSlot1?.price || selectedSlot1?.cost || 0}
                        <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} />
                      </div>
                    </motion.div>
                  )}
                </div>

                <div className="text-white/10 text-4xl font-black pt-10">→</div>

                <div className="flex-1 text-center">
                  <h4 className="text-white/30 text-[9px] uppercase tracking-widest mb-4 font-black">Цель</h4>
                  {!selectedSlot2 ? (
                    <motion.button
                      whileHover={{ scale: 1.05, borderColor: 'rgba(34, 197, 94, 0.3)', backgroundColor: 'rgba(34, 197, 94, 0.05)' }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => {
                        setShowGiftSelector(true);
                        triggerHaptic('light');
                      }}
                      className="w-32 h-32 mx-auto rounded-3xl border-2 border-dashed border-white/10 bg-white/[0.01] transition-all flex items-center justify-center"
                    >
                      <span className="text-white/10 text-6xl font-black">+</span>
                    </motion.button>
                  ) : (
                    <motion.div 
                      initial={{ scale: 0.9, opacity: 0 }}
                      animate={{ scale: 1, opacity: 1 }}
                      className="p-5 rounded-3xl bg-green-500/10 border border-green-500/30 relative shadow-[0_0_30px_rgba(34,197,94,0.1)]"
                    >
                       <div className="absolute inset-0 bg-green-500/5 blur-3xl rounded-full" />
                      <img src={getDynamicGiftImage(selectedSlot2)} alt="Target" className="w-24 h-24 object-contain mx-auto relative z-10" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                      <div className="flex items-center justify-center gap-1.5 text-xs text-green-400 font-black font-rounded mt-4 bg-green-500/10 py-1.5 rounded-xl border border-green-500/20">
                        {selectedSlot2?.price || selectedSlot2?.cost || 0}
                        <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} />
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
                  className={`text-center p-8 rounded-3xl border-2 relative overflow-hidden bg-[#1a1b1f] ${
                    result === 'success'
                      ? 'border-green-500/50 shadow-[0_0_50px_rgba(34,197,94,0.15)]'
                      : 'border-red-500/50 shadow-[0_0_50px_rgba(239,68,68,0.15)]'
                  }`}
                >
                  <p className={`font-black text-4xl mb-2 font-rounded uppercase tracking-tight ${
                    result === 'success' ? 'text-green-400 text-glow' : 'text-red-400 text-glow'
                  }`}>
                    {result === 'success' ? 'УСПЕХ!' : 'ПРОВАЛ!'}
                  </p>
                  <p className="text-white/40 text-[10px] font-black uppercase tracking-[0.2em]">
                    {result === 'success' ? 'Предмет улучшен' : 'Предмет потерян'}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="glass-panel p-6 border-white/5 bg-white/[0.01]">
              <h3 className="text-white/20 font-black text-[9px] mb-5 uppercase tracking-[0.3em] text-center">Ваш инвентарь</h3>
              <div className="grid grid-cols-3 gap-4 max-h-72 overflow-y-auto pr-1">
                {inventory.map(item => (
                  <motion.div
                    key={item.id}
                    whileHover={{ scale: 1.05 }}
                    whileTap={{ scale: 0.95 }}
                    onClick={() => {
                      setSelectedSlot1(item);
                      setResult(null);
                      setSelectedSlot2(null);
                      triggerHaptic('light');
                    }}
                    className={`p-3 rounded-2xl border-2 cursor-pointer transition-all flex flex-col items-center ${
                      selectedSlot1?.id === item.id
                        ? 'border-white/50 bg-white/10 shadow-2xl'
                        : 'border-white/5 bg-white/[0.02] hover:border-white/10'
                    }`}
                  >
                    <img src={getDynamicGiftImage(item)} alt="Gift" className="w-16 h-16 object-contain mb-2 mx-auto" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                    <span className="text-white text-[10px] font-black text-center truncate block font-rounded w-full px-1">{item?.name || 'Gift'}</span>
                    <div className="flex items-center justify-center gap-1 text-white/40 text-[10px] mt-2 font-black font-rounded">
                       {item?.price || item?.cost || 0}
                       <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} />
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
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/95 backdrop-blur-xl p-4"
            >
              <motion.div
                initial={{ scale: 0.9, y: 30 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 30 }}
                className="glass-panel w-full max-w-lg mx-4 max-h-[85vh] overflow-hidden flex flex-col p-8 border-white/10 bg-[#15161a]"
              >
                <div className="flex justify-between items-center mb-8">
                  <h3 className="text-white font-black text-2xl uppercase tracking-tight">Выберите цель</h3>
                  <button onClick={() => setShowGiftSelector(false)} className="text-white/20 hover:text-white text-3xl transition-colors">✕</button>
                </div>
                
                {selectedSlot1 && (
                  <div className="mb-8 px-5 py-4 rounded-2xl bg-white/[0.02] border border-white/5">
                     <p className="text-white/30 text-[10px] font-black uppercase tracking-[0.2em] text-center">
                      Доступны предметы дороже {selectedSlot1?.price || selectedSlot1?.cost || 0}
                      <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3 inline mx-2 mb-0.5" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} />
                    </p>
                  </div>
                )}

                <div className="grid grid-cols-3 gap-4 overflow-y-auto pr-2 pb-6 custom-scrollbar">
                  {eligibleTargets.map((gift, idx) => (
                    <motion.div
                      key={idx}
                      whileHover={{ scale: 1.05 }}
                      whileTap={{ scale: 0.95 }}
                      onClick={() => {
                        setSelectedSlot2(gift);
                        setShowGiftSelector(false);
                        triggerHaptic('light');
                      }}
                      className={`p-4 rounded-3xl border-2 cursor-pointer transition-all flex flex-col items-center ${
                        selectedSlot2?.name === gift.name
                          ? 'border-green-500/60 bg-green-500/10'
                          : 'border-white/5 bg-white/[0.03] hover:border-white/10'
                      }`}
                    >
                      <img src={getDynamicGiftImage(gift)} alt="Gift" className="w-20 h-20 object-contain mb-3 mx-auto" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                      <p className="text-white text-[10px] font-black text-center truncate block font-rounded w-full mb-1.5">{gift?.name || 'Gift'}</p>
                      <div className="flex items-center justify-center gap-1 text-green-400 text-[11px] font-black font-rounded bg-green-500/5 px-2 py-1 rounded-lg">
                          {gift?.price || gift?.cost || 0}
                          <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} />
                      </div>
                    </motion.div>
                  ))}
                  {eligibleTargets.length === 0 && selectedSlot1 && (
                    <div className="col-span-3 py-20 text-center">
                       <p className="text-white/10 text-sm font-black uppercase tracking-[0.3em]">Цели не найдены</p>
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
              numberOfPieces={400}
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
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-xl p-4"
    >
      {content}
    </motion.div>
  );
}

function UpgradeButtonContent({ canUpgrade, isUpgrading, upgradeCost, handleUpgrade }) {
  if (isUpgrading) {
    return (
      <div className="w-full py-6 rounded-2xl font-black text-2xl flex items-center justify-center gap-4 bg-green-500/10 border-2 border-green-500/40 text-green-400 font-rounded uppercase tracking-tight shadow-[0_0_30px_rgba(34,197,94,0.2)]">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-7 h-7 border-4 border-green-400/20 border-t-green-400 rounded-full"
        />
        Апгрейдим...
      </div>
    );
  }

  return (
    <div className="w-full space-y-4">
      <motion.button
        whileHover={{ scale: canUpgrade ? 1.02 : 1 }}
        whileTap={{ scale: canUpgrade ? 0.98 : 1 }}
        onClick={() => {
          handleUpgrade();
        }}
        disabled={isUpgrading || !canUpgrade}
        className="w-full py-6 rounded-2xl font-black text-2xl disabled:opacity-50 transition-all flex items-center justify-center gap-3 uppercase tracking-tighter shadow-2xl relative overflow-hidden group"
        style={{
          backgroundColor: canUpgrade ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255, 255, 255, 0.02)',
          border: `2px solid ${canUpgrade ? 'rgba(34, 197, 94, 0.6)' : 'rgba(255, 255, 255, 0.05)'}`,
          color: canUpgrade ? '#4ade80' : 'rgba(255,255,255,0.1)',
        }}
      >
        {canUpgrade && (
          <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:translate-x-full transition-transform duration-700" />
        )}
        Апгрейд ({upgradeCost}
        <img src="/asset/Icons/TelegramStar.png" className="h-8 w-8" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} />)
      </motion.button>
      {!canUpgrade && !isUpgrading && (
        <p className="text-red-500/50 text-[9px] text-center font-black uppercase tracking-[0.3em] animate-pulse">
          Недостаточно звёзд
        </p>
      )}
    </div>
  );
}
