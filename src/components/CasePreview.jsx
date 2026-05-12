import React, { useState, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Confetti from 'react-confetti';
import { getGiftsInRange, ALL_GIFTS } from '../giftData';
import { openCase } from '../api';

const easeOutCirc = [0, 0.55, 0.45, 1];

export default function CasePreview({ user, caseItem, onClose, onWin, balance, setBalance, setSpent, flashDiscount = null }) {
  const [isSpinning, setIsSpinning] = useState(false);
  const [hasSpun, setHasSpun] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [promoCode, setPromoCode] = useState('');
  const [showResult, setShowResult] = useState(false);
  const [wonItem, setWonItem] = useState(null);
  const [spinData, setSpinData] = useState({ items: [], targetX: 0 });
  const [currentStock, setCurrentStock] = useState(caseItem.stock || 0);
  const animationKey = useRef(0);

  const isPromo = caseItem.id === 1;
  const canOpen = (!isPromo || promoCode.trim().length > 0) && currentStock > 0;

  const getCost = useMemo(() => {
    if (!flashDiscount || caseItem.price === 0) return caseItem.price;
    return Math.floor(caseItem.price * (1 - flashDiscount));
  }, [caseItem.price, flashDiscount]);

  const dropItems = useMemo(() =>
    getGiftsInRange(caseItem.minPrice, caseItem.maxPrice),
    [caseItem.minPrice, caseItem.maxPrice]
  );

  const previewGifts = useMemo(() => {
    if (!dropItems || dropItems.length === 0) return [];
    if (dropItems.length === 1) return [dropItems[0]];
    const sorted = [...dropItems].sort((a, b) => b.price - a.price);
    return sorted.slice(0, 2);
  }, [dropItems]);

  const spinItems = useMemo(() => {
    if (dropItems.length === 0) {
      return ALL_GIFTS.slice(0, 8);
    }
    return dropItems;
  }, [dropItems]);

  const ITEM_SIZE = 144;
  const GAP = 12;
  const FULL_ITEM_WIDTH = ITEM_SIZE + GAP;
  const viewportRef = useRef(null);

  const triggerHaptic = () => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy');
    }
  };

  const handleOpen = async () => {
    if (isSpinning || !canOpen || !user?.id) return;

    const cost = getCost;
    if (balance < cost) {
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.showAlert("❌ Недостаточно средств!");
      }
      return;
    }

    setIsSpinning(true);

    try {
        const response = await openCase(user.id, caseItem.id, isPromo ? promoCode : null);
        
        if (!response?.success) {
          throw new Error("Invalid response from server");
        }

        const actualWonItem = response.item;
        if (!actualWonItem && !isPromo) {
           throw new Error("No item returned from server");
        }

        if (isPromo && response.reward) {
          // If it was a promo, the reward was already added to balance on server
          // but we might need to update local balance
          if (setBalance) setBalance(prev => prev + response.reward);
          
          // For promos, we don't necessarily spin if it's just a star reward
          // but let's assume promo cases can also return items
        }

        triggerHaptic();
        
        if (!isPromo && setBalance) {
          // Balance is already updated on server, but we update locally for smoothness
          // Or we could syncBalance(user.id)
          setBalance(prev => Math.max(0, prev - (response.deducted !== undefined ? response.deducted : cost)));
        }
        if (!isPromo && setSpent) {
          setSpent(prev => prev + (response.deducted !== undefined ? response.deducted : cost));
        }
        setCurrentStock(prev => Math.max(0, prev - 1));

        setWonItem(actualWonItem);
        setHasSpun(false);
        setShowConfetti(false);
        setShowResult(false);

        // Find index of won item in spinItems for animation
        let winIndex = spinItems.findIndex(i => i.name === actualWonItem.name && i.price === actualWonItem.price);
        if (winIndex === -1) winIndex = 0;

        const repetitions = 10;
        const extendedItems = [];
        for (let r = 0; r < repetitions; r++) extendedItems.push(...spinItems);

        const targetIndex = spinItems.length * 7 + winIndex;
        const viewportWidth = viewportRef.current ? viewportRef.current.offsetWidth : (window.innerWidth - 64);
        const containerCenter = viewportWidth / 2;
        const itemCenter = (targetIndex * FULL_ITEM_WIDTH) + (ITEM_SIZE / 2);
        const targetX = containerCenter - itemCenter;

        animationKey.current += 1;
        setSpinData({ items: extendedItems, targetX, animKey: animationKey.current });
        // isSpinning is already true, animation will start
    } catch (e) {
        console.error("Error in handleOpen:", e);
        // STOP animation immediately on error
        setIsSpinning(false);
        setHasSpun(false);
        setShowConfetti(false);
        setShowResult(false);
        
        // Error message is already shown by api.js showAlert()
        // But if we get here, make sure alert is shown
        if (!e.status) {
          if (window.Telegram?.WebApp) {
            window.Telegram.WebApp.showAlert("❌ Ошибка при открытии кейса");
          }
        }
    }
  };

  const handleAnimationComplete = () => {
    setTimeout(() => {
      setHasSpun(true);
      setIsSpinning(false);
      setShowConfetti(true);
      setShowResult(true);

      if (onWin && wonItem) {
        onWin(wonItem, caseItem);
      }

      setTimeout(() => setShowConfetti(false), 3000);
    }, 100);
  };

  const handleClaim = () => {
    triggerHaptic();
    setShowConfetti(false);
    onClose();
  };

  return (
    <div className="h-full flex flex-col bg-black">
      {showConfetti && (
        <div className="fixed inset-0 z-60 pointer-events-none">
          <Confetti
            width={window.innerWidth}
            height={window.innerHeight}
            recycle={false}
            numberOfPieces={200}
            colors={['#ff0000', '#00ff00', '#0099ff', '#ff00ff', '#ffaa00', '#888888']}
          />
        </div>
      )}

      <div className="relative z-10 flex-1 overflow-y-auto">
        <div className="glass-panel border-b border-white/10 px-6 py-4 flex items-center justify-between sticky top-0 z-20">
          <button
            onClick={() => {
              if (!isSpinning && !showResult) {
                onClose();
                triggerHaptic();
              }
            }}
            className="text-white/50 hover:text-white text-xl"
          >
            ←
          </button>
          <div className="flex flex-col items-center">
            <h2 className="text-white font-bold text-lg leading-tight">{caseItem.name}</h2>
            <p className="text-white/40 text-[10px] uppercase font-black tracking-widest">Available: {currentStock}</p>
          </div>
          <div className="w-8" />
        </div>

        <AnimatePresence>
          {isPromo && !isSpinning && !hasSpun && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mx-4 mb-4 mt-4"
            >
              <input
                type="text"
                value={promoCode}
                onChange={(e) => setPromoCode(e.target.value)}
                placeholder="Введите промокод"
                className="glass-input w-full px-6 py-4 text-sm font-rounded flex items-center justify-center text-center"
              />
            </motion.div>
          )}
        </AnimatePresence>

        <div className="relative h-64 mx-4 mb-4">
          <div
            className="absolute inset-0 rounded-3xl"
            style={{
              background: `radial-gradient(ellipse at center, ${caseItem.glowColor}20, transparent 70%)`,
            }}
          />

          <div className="absolute inset-0 flex items-center justify-center">
            {previewGifts.map((gift, idx) => (
              <motion.div
                key={gift.price + idx}
                animate={{
                  y: [0, -12, 0],
                  rotate: [0, 4, -4, 0],
                  scale: [1.3, 1.4, 1.3],
                }}
                transition={{
                  duration: 2.5 + idx * 0.4,
                  repeat: Infinity,
                  ease: "easeInOut",
                  delay: idx * 0.6,
                }}
                className="absolute"
                style={{
                  left: previewGifts.length === 1 ? '50%' : idx === 0 ? '35%' : '65%',
                  top: '15%',
                  transform: 'translateX(-50%)',
                  zIndex: 10,
                }}
              >
                <div
                  className="rounded-3xl p-4"
                  style={{ backgroundColor: `${caseItem.glowColor}15` }}
                >
                  <img
                    src={gift.image}
                    alt={gift.name}
                    className="w-28 h-28 object-contain"
                    style={{ filter: `drop-shadow(0 0 15px ${caseItem.glowColor}80)` }}
                  />
                </div>
              </motion.div>
            ))}
          </div>

          <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2">
            <img
              src={caseItem.name === 'Pussy Case' ? '/asset/Gifts/50S_GiftBox.png' : '/asset/Case/CaseBlack.png'}
              alt={caseItem.name}
              className={caseItem.name === 'Pussy Case' ? "w-32 h-32 object-contain mb-8" : "w-48 h-48 object-contain"}
              style={{ filter: `drop-shadow(0 0 30px ${caseItem.glowColor}80)` }}
            />
          </div>
        </div>

        <AnimatePresence>
          {(isSpinning || hasSpun) && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mx-4 mb-6"
            >
              <div className="glass-panel p-4">
                <div className="relative mb-4">
                  <div className="absolute left-1/2 top-0 transform -translate-x-1/2 z-30">
                    <div className="w-0 h-0 border-l-4 border-r-4 border-t-8 border-l-transparent border-r-transparent border-t-white" />
                  </div>
                  <div className="absolute left-1/2 top-2 transform -translate-x-1/2 w-0.5 h-40 bg-white/30 z-20 pointer-events-none" />

                  <div ref={viewportRef} className="overflow-hidden rounded-2xl bg-white/[0.02] border border-white/10 p-4">
                    {spinData.items.length > 0 && (
                      <motion.div
                        key={spinData.animKey}
                        className="flex gap-3"
                        initial={{ x: 0 }}
                        animate={{ x: spinData.targetX }}
                        transition={{
                          duration: 4,
                          ease: [0.12, 0, 0.39, 0],
                        }}
                        onAnimationComplete={handleAnimationComplete}
                      >
                        {spinData.items.map((item, idx) => (
                          <div
                            key={`${item.price}-${idx}-${spinData.animKey}`}
                            className="flex-shrink-0 w-36 h-36 rounded-2xl border-2 flex flex-col items-center justify-center p-2"
                            style={{
                              borderColor: `${caseItem.glowColor}40`,
                              backgroundColor: `${caseItem.glowColor}10`,
                            }}
                          >
                            <img src={item.image} alt={item.name} className="w-28 h-28 object-contain mb-1" />
                            <div className="flex items-center justify-center gap-1 text-[10px] text-white/70">
                              <span className="font-bold flex items-center gap-0.5 font-rounded text-xs">
                                {item.price}
                                <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" />
                              </span>
                            </div>
                          </div>
                        ))}
                      </motion.div>
                    )}
                  </div>
                </div>

                {hasSpun && wonItem && showResult && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="text-center p-4 rounded-3xl relative overflow-hidden mt-4"
                    style={{
                      borderColor: `${caseItem.glowColor}30`,
                      backgroundColor: `${caseItem.glowColor}10`,
                    }}
                  >
                    <motion.div
                      animate={{
                        scale: [1, 1.2, 1],
                        opacity: [0.3, 0.6, 0.3],
                      }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="absolute inset-0 rounded-2xl"
                      style={{
                        backgroundColor: `${caseItem.glowColor}20`,
                        filter: 'blur(20px)',
                      }}
                    />

                    <div className="relative z-10">
                      <p className="text-white/50 text-xs mb-2 uppercase tracking-wider font-rounded">Вы выиграли!</p>
                      <motion.img
                        src={wonItem.image}
                        alt={wonItem.name}
                        className="h-48 w-48 object-contain mx-auto mb-4"
                        style={{ filter: `drop-shadow(0 0 35px ${caseItem.glowColor}90)` }}
                        animate={{
                          scale: [1, 1.1, 1],
                        }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                      />
                      <p
                        className="text-white font-black text-3xl mb-3 font-rounded"
                        style={{ color: caseItem.glowColor }}
                      >
                        {wonItem.name}
                      </p>
                      <div className="flex items-center justify-center gap-2 text-white/70 text-lg">
                        <span className="flex items-center gap-1.5 font-black font-rounded">
                          {wonItem.price}
                          <img src="/asset/Icons/TelegramStar.png" className="h-7 w-7" alt="Stars" />
                        </span>
                      </div>
                    </div>
                  </motion.div>
                )}

                {isSpinning && !hasSpun && (
                  <div className="text-center py-3">
                    <div className="inline-flex items-center justify-center gap-2 text-white/50">
                      <motion.div
                        animate={{ rotate: 360 }}
                        transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                        className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                      />
                      <span className="text-sm">Открываем...</span>
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {!isSpinning && !hasSpun && (
            <motion.div
              initial={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mx-4 mb-6"
            >
              <h3 className="text-white/50 text-xs uppercase tracking-wider mb-3">Возможный дроп</h3>
              <div className="grid grid-cols-3 gap-2 max-h-48 overflow-y-auto">
                {dropItems.map((item, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="glass-panel p-2 flex flex-col items-center"
                  >
                    <img src={item.image} alt={item.name} className="w-12 h-12 object-contain mb-1" />
                    <p className="text-white text-[10px] font-semibold text-center truncate w-full">{item.name}</p>
                    <div className="flex items-center justify-center gap-1 text-white/50 text-[8px]">
                      <img src="/asset/Icons/TelegramStar.png" alt="Star" className="w-3 h-3" />
                      <span className="flex items-center gap-0.5">
                        {item.price}
                        <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3" alt="Stars" />
                      </span>
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="glass-panel border-t border-white/10 p-4">
        {!isSpinning && !hasSpun ? (
          <div className="space-y-3">
            {flashDiscount && caseItem.price > 0 && (
              <div className="text-center mb-2">
                <span className="text-red-500 text-xs font-rounded line-through opacity-50">
                  {caseItem.price}
                </span>
                <span className="text-red-500 text-sm font-black ml-2 font-rounded">
                  -{Math.round(flashDiscount * 100)}% FLASH SALE!
                </span>
              </div>
            )}
            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={handleOpen}
              disabled={!canOpen || balance < getCost || isSpinning}
              className="w-full py-4 rounded-xl font-black text-lg disabled:opacity-50 transition-all flex items-center justify-center gap-2"
              style={{
                backgroundColor: canOpen && balance >= getCost && !isSpinning ? `${caseItem.glowColor}20` : 'rgba(255,255,255,0.05)',
                border: `1px solid ${canOpen && balance >= getCost && !isSpinning ? `${caseItem.glowColor}40` : 'rgba(255,255,255,0.1)'}`,
                color: canOpen && balance >= getCost && !isSpinning ? caseItem.glowColor : 'rgba(255,255,255,0.3)',
              }}
            >
              {caseItem.price === 0 ? 'ОТКРЫТЬ БЕСПЛАТНО' : (
                <span className="flex items-center justify-center gap-2">
                  ОТКРЫТЬ ЗА {getCost}
                  <img src="/asset/Icons/TelegramStar.png" className="h-6 w-6" alt="Stars" />
                </span>
              )}
            </motion.button>
          </div>
        ) : hasSpun && showResult ? (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleClaim}
            className="w-full py-4 rounded-2xl bg-white/10 border border-white/20 text-white font-black text-xl font-rounded flex items-center justify-center"
          >
            ЗАБРАТЬ
          </motion.button>
        ) : (
          <div className="text-center py-2 text-white/30 text-sm font-rounded uppercase tracking-widest">Открытие кейса...</div>
        )}
      </div>
    </div>
  );
}
