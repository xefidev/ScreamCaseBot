import React, { useState, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Confetti from 'react-confetti';
import { ALL_GIFTS } from '../../giftData';
import { upgradeItem, fetchBalance } from '../../api';
import { normalizeGiftImage, useDefaultGiftImage } from '../../giftUtils';

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
    if (!selectedSlot1 || !selectedSlot2 || selectedSlot2.price <= selectedSlot1.price || selectedSlot2.price === 0) return 0;
    return parseFloat(((selectedSlot1.price / selectedSlot2.price) * 100).toFixed(2));
  }, [selectedSlot1, selectedSlot2]);

  const upgradeCost = useMemo(() => {
    if (!selectedSlot1) return 0;
    return Math.ceil(selectedSlot1.price * 0.5);
  }, [selectedSlot1]);

  const eligibleTargets = useMemo(() => {
    if (!selectedSlot1) return [];
    return ALL_GIFTS.filter(g => g.price > selectedSlot1.price && g.price >= 15);
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
        price: selectedSlot2.price,
        name: selectedSlot2.name,
        image: selectedSlot2.image,
      };

      setInventory(prev => {
        const newInv = prev.filter(i => i.id !== selectedSlot1.id);
        return [...newInv, upgradedItem];
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
    const displayChance = successChance;
    const successAngle = Math.min(displayChance, 100);

    const successPath = describeArc(100, 100, radius, 0, successAngle);
    const failPath = describeArc(100, 100, radius, successAngle, 100);

    return (
      <div className="relative w-48 h-48 mx-auto">
        <svg viewBox="0 0 200 200" className="w-full h-full">
          {displayChance < 100 && (
            <path
              d={failPath}
              fill="rgba(107, 114, 128, 0.6)"
              stroke="rgba(107, 114, 128, 0.8)"
              strokeWidth="2"
            />
          )}
          {displayChance > 0 && (
            <path
              d={successPath}
              fill="rgba(34, 197, 94, 0.6)"
              stroke="rgba(34, 197, 94, 0.8)"
              strokeWidth="2"
            />
          )}
          <circle cx="100" cy="100" r={radius - 2} fill="none" stroke="rgba(255,255,255,0.1)" strokeWidth="4" />

          <text x="100" y="95" textAnchor="middle" dominantBaseline="central" fill="white" fontSize="28" fontWeight="bold" className="font-rounded">
            {successChance}%
          </text>
          <text x="100" y="115" textAnchor="middle" dominantBaseline="central" fill="rgba(255,255,255,0.5)" fontSize="10" className="font-rounded uppercase tracking-widest">
            шанс
          </text>
        </svg>

        {isUpgrading ? (
          <motion.div
            key={animKey}
            animate={{ rotate: arrowRotation }}
            transition={{
              duration: 4,
              ease: [0.12, 0, 0.39, 0],
            }}
            onAnimationComplete={handleAnimationComplete}
            className="absolute top-[-16px] left-1/2 transform -translate-x-1/2 z-30"
            style={{ transformOrigin: '50% 112px' }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 24L2 4H22L12 24Z" fill="white" />
              <path d="M12 20L4 6H20L12 20Z" fill="rgba(255,255,255,0.8)" />
            </svg>
          </motion.div>
        ) : (
          <div className="absolute top-[-16px] left-1/2 transform -translate-x-1/2 z-30">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
              <path d="M12 24L2 4H22L12 24Z" fill="white" />
              <path d="M12 20L4 6H20L12 20Z" fill="rgba(255,255,255,0.8)" />
            </svg>
          </div>
        )}
      </div>
    );
  };

  function describeArc(x, y, radius, startAngle, endAngle) {
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
    <div className={`${isPage ? 'p-4 min-h-full' : ''}`}>
      <div className={`${!isPage ? 'glass-panel p-6 w-full max-w-lg mx-auto' : ''}`}>
        {!isPage && (
          <div className="flex justify-between items-center mb-6">
            <h2 className="text-2xl font-black text-white font-rounded">Апгрейд</h2>
          </div>
        )}
        {isPage && (
          <div className="mb-6">
            <h2 className="text-2xl font-black text-white font-rounded">Апгрейд</h2>
            <p className="text-white/50 text-sm mt-1">Улучшай предметы и повышай их ценность</p>
          </div>
        )}

        {!inventory || inventory.length === 0 ? (
          <div className="glass-panel p-8 text-center">
            <p className="text-white/50 font-rounded">Инвентарь пуст. Открывайте ящики!</p>
          </div>
        ) : (
          <div className="space-y-4">
            <div className="glass-panel p-4">
              <div className="flex items-center justify-center mb-4">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,0.3)" strokeWidth="2">
                  <path d="M12 5v14M5 12l7 7 7-7" />
                </svg>
              </div>

              <div className="flex items-center justify-center gap-4 mb-4">
                <div className="flex-1 text-center">
                  <h4 className="text-white/50 text-[10px] uppercase tracking-wider mb-2 font-rounded">Мой предмет</h4>
                  {!selectedSlot1 ? (
                    <div className="w-32 h-32 mx-auto rounded-3xl border border-dashed border-white/20 bg-white/5 flex items-center justify-center">
                      <span className="text-white/30 text-xl font-rounded">?</span>
                    </div>
                  ) : (
                    <div className="p-3 rounded-3xl bg-white/10 border border-white/20">
                      <img src={normalizeGiftImage(selectedSlot1.image)} alt={selectedSlot1.name} className="w-24 h-24 object-contain mx-auto" onError={useDefaultGiftImage} />
                      <div className="flex items-center justify-center gap-1.5 text-sm text-white/70 mt-2 font-black font-rounded">
                        {selectedSlot1.price}
                        <img src="/asset/Icons/TelegramStar.png" className="h-5 w-5" alt="Stars" />
                      </div>
                    </div>
                  )}
                </div>

                <div className="text-white/30 text-2xl font-rounded">→</div>

                <div className="flex-1 text-center">
                  <h4 className="text-white/50 text-[10px] uppercase tracking-wider mb-2 font-rounded">Желаемый</h4>
                  {!selectedSlot2 ? (
                    <motion.button
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => {
                        setShowGiftSelector(true);
                        triggerHaptic();
                      }}
                      className="w-32 h-32 mx-auto rounded-3xl border border-dashed border-white/20 bg-white/5 hover:bg-white/10 flex items-center justify-center"
                    >
                      <span className="text-white/30 text-4xl font-rounded">+</span>
                    </motion.button>
                  ) : (
                    <div className="p-3 rounded-3xl bg-green-500/10 border border-green-500/30">
                      <img src={normalizeGiftImage(selectedSlot2.image)} alt={selectedSlot2.name} className="w-24 h-24 object-contain mx-auto" onError={useDefaultGiftImage} />
                      <div className="flex items-center justify-center gap-1.5 text-sm text-green-400 mt-2 font-black font-rounded">
                        {selectedSlot2.price}
                        <img src="/asset/Icons/TelegramStar.png" className="h-5 w-5" alt="Stars" />
                      </div>
                    </div>
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
                  className={`text-center p-6 rounded-3xl border ${
                    result === 'success'
                      ? 'border-green-500/30 bg-green-500/10'
                      : 'border-red-500/30 bg-red-500/10'
                  }`}
                >
                  <p className={`font-black text-2xl mb-2 font-rounded ${
                    result === 'success' ? 'text-green-400' : 'text-red-400'
                  }`}>
                    {result === 'success' ? 'АПГРЕЙД УСПЕШЕН!' : 'АПГРЕЙД ПРОВАЛЕН!'}
                  </p>
                  <p className="text-white/50 text-sm font-rounded">
                    {result === 'success'
                      ? 'Предмет улучшен и добавлен в инвентарь!'
                      : 'Предмет потерян при попытке улучшения.'}
                  </p>
                </motion.div>
              )}
            </AnimatePresence>

            <div className="glass-panel p-4">
              <h3 className="text-white font-bold text-sm mb-3 font-rounded uppercase tracking-widest">Выберите предмет</h3>
              <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto">
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
                    className={`p-2 rounded-xl border cursor-pointer transition-all flex flex-col items-center ${
                      selectedSlot1?.id === item.id
                        ? 'border-white/40 bg-white/10'
                        : 'border-white/10 bg-white/5 hover:border-white/20'
                    }`}
                  >
                    <img src={normalizeGiftImage(item.image)} alt={item.name} className="w-16 h-16 object-contain mb-1 mx-auto" onError={useDefaultGiftImage} />
                    <span className="text-white text-[10px] font-semibold text-center truncate block font-rounded">{item.name}</span>
                    <div className="flex items-center justify-center gap-1 text-white/50 text-[10px] mt-1 font-rounded">
                      <span className="font-bold flex items-center gap-0.5">
                        {item.price}
                        <img src="/asset/Icons/TelegramStar.png" className="h-2.5 w-2.5" alt="Stars" />
                      </span>
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
              className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm p-4"
            >
              <motion.div
                initial={{ scale: 0.9, y: 20 }}
                animate={{ scale: 1, y: 0 }}
                exit={{ scale: 0.9, y: 20 }}
                className="glass-panel w-full max-w-lg mx-4 max-h-[80vh] overflow-y-auto p-6"
              >
                <div className="flex justify-between items-center mb-4">
                  <h3 className="text-white font-bold text-lg font-rounded">Выберите желаемый предмет</h3>
                  <button onClick={() => setShowGiftSelector(false)} className="text-white/50 hover:text-white text-xl">✕</button>
                </div>
                {selectedSlot1 && (
                  <p className="text-white/50 text-xs mb-3 font-rounded">
                    Показываются только предметы дороже вашего ({selectedSlot1.price}
                    <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3 inline mx-0.5" alt="Stars" />)
                  </p>
                )}
                <div className="grid grid-cols-3 gap-3">
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
                      className={`p-3 rounded-2xl border cursor-pointer transition-all flex flex-col items-center ${
                        selectedSlot2?.name === gift.name
                          ? 'border-green-500/40 bg-green-500/10'
                          : 'border-white/10 bg-white/5 hover:border-white/20'
                      }`}
                    >
                      <img src={normalizeGiftImage(gift.image)} alt={gift.name} className="w-20 h-20 object-contain mb-2 mx-auto" onError={useDefaultGiftImage} />
                      <p className="text-white text-[10px] font-semibold text-center truncate block font-rounded">{gift.name}</p>
                      <div className="flex items-center justify-center gap-1 text-white/50 text-[10px] mt-1 font-rounded">
                        <span className="font-bold flex items-center gap-0.5">
                          {gift.price}
                          <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3" alt="Stars" />
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </div>
                {eligibleTargets.length === 0 && selectedSlot1 && (
                  <p className="text-white/50 text-sm text-center py-8 font-rounded">
                    Нет предметов дороже {selectedSlot1.price}
                    <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3 inline mx-0.5" alt="Stars" />
                  </p>
                )}
              </motion.div>
            </motion.div>
          )}
        </AnimatePresence>

        {showConfetti && (
          <div className="fixed inset-0 z-50 pointer-events-none">
            <Confetti
              width={window.innerWidth}
              height={window.innerHeight}
              recycle={false}
              numberOfPieces={200}
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
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
    >
      {content}
    </motion.div>
  );
}

function UpgradeButtonContent({ canUpgrade, isUpgrading, upgradeCost, handleUpgrade }) {
  if (isUpgrading) {
    return (
      <div className="w-full py-4 rounded-xl font-black text-lg flex items-center justify-center gap-2 bg-green-500/15 border border-green-500/30 text-green-400 font-rounded">
        <motion.div
          animate={{ rotate: 360 }}
          transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
          className="w-5 h-5 border-2 border-green-400/30 border-t-green-400 rounded-full"
        />
        Апгрейдим...
      </div>
    );
  }

  return (
    <div className="w-full space-y-2">
      <motion.button
        whileHover={{ scale: canUpgrade ? 1.02 : 1 }}
        whileTap={{ scale: canUpgrade ? 0.98 : 1 }}
        onClick={() => {
          handleUpgrade();
          if (canUpgrade && window.Telegram?.WebApp?.HapticFeedback) {
            window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy');
          }
        }}
        disabled={isUpgrading || !canUpgrade}
        className="w-full py-4 rounded-xl font-black text-lg disabled:opacity-50 transition-all flex items-center justify-center gap-2"
        style={{
          backgroundColor: canUpgrade ? 'rgba(34, 197, 94, 0.15)' : 'rgba(255, 255, 255, 0.05)',
          border: `1px solid ${canUpgrade ? 'rgba(34, 197, 94, 0.3)' : 'rgba(255, 255, 255, 0.1)'}`,
          color: canUpgrade ? '#22c55e' : 'rgba(255,255,255,0.3)',
        }}
      >
        Апгрейд ({upgradeCost}
        <img src="/asset/Icons/TelegramStar.png" className="h-6 w-6" alt="Stars" />)
      </motion.button>
      {!canUpgrade && !isUpgrading && (
        <p className="text-red-400 text-[10px] text-center font-rounded uppercase tracking-wider">
          Недостаточно звёзд для апгрейда
        </p>
      )}
    </div>
  );
}
