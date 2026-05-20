import React, { useState, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Confetti from 'react-confetti';
import { getGiftsInRange, ALL_GIFTS } from '../giftData';
import { openCase } from '../api';
import { normalizeGiftImage, useDefaultGiftImage } from '../giftUtils';

const easeOutCirc = [0, 0.55, 0.45, 1];

export default function CasePreview({ user, caseItem, onClose, onWin, balance, setBalance, setSpent, flashDiscount = null }) {
  const [isSpinning, setIsSpinning] = useState(false);
  const [hasSpun, setHasSpun] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [wonItems, setWonItems] = useState([]);
  const [spinData, setSpinData] = useState({ items: [], targetX: 0 });
  const [currentStock, setCurrentStock] = useState(caseItem.stock || 0);
  const [quantity, setQuantity] = useState(1);
  const animationKey = useRef(0);

  const canOpen = currentStock >= quantity;

  const getCost = useMemo(() => {
    let basePrice = caseItem.price;
    if (flashDiscount && basePrice > 0) {
      basePrice = Math.floor(basePrice * (1 - flashDiscount));
    }
    return basePrice * quantity;
  }, [caseItem.price, flashDiscount, quantity]);

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

  const triggerHaptic = (type = 'heavy') => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred(type);
    }
  };

  const handleOpen = async () => {
    if (isSpinning || !canOpen || !user?.id) return;

    const totalCost = getCost;
    if (balance < totalCost) {
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.showAlert("❌ Недостаточно средств!");
      }
      return;
    }

    setIsSpinning(true);
    setWonItems([]);

    try {
        const results = [];
        let totalDeducted = 0;

        // Perform multiple openings
        for (let i = 0; i < quantity; i++) {
          const response = await openCase(user.id, caseItem.id);
          if (!response?.success || !response.item) {
            throw new Error(`Failed to open case ${i+1}`);
          }
          results.push(response.item);
          totalDeducted += (response.deducted !== undefined ? response.deducted : (totalCost / quantity));
        }

        triggerHaptic();
        
        if (setBalance) {
          setBalance(prev => Math.max(0, prev - totalDeducted));
        }
        if (setSpent) {
          setSpent(prev => prev + totalDeducted);
        }
        setCurrentStock(prev => Math.max(0, prev - quantity));

        setWonItems(results);
        setHasSpun(false);
        setShowConfetti(false);
        setShowResult(false);

        // Animation logic (based on the last item for visual effect)
        const lastWonItem = results[results.length - 1];
        let winIndex = spinItems.findIndex(i => i.name === lastWonItem.name && i.price === lastWonItem.price);
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
    } catch (e) {
        console.error("Error in handleOpen:", e);
        setIsSpinning(false);
        if (window.Telegram?.WebApp) {
          window.Telegram.WebApp.showAlert("❌ Ошибка при открытии кейса");
        }
    }
  };

  const handleAnimationComplete = () => {
    setTimeout(() => {
      setHasSpun(true);
      setIsSpinning(false);
      setShowConfetti(true);
      setShowResult(true);

      if (onWin && wonItems.length > 0) {
        wonItems.forEach(item => onWin(item, caseItem));
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
                    src={normalizeGiftImage(gift.image)}
                    alt={gift.name}
                    className="w-28 h-28 object-contain"
                    onError={useDefaultGiftImage}
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
                            <img src={normalizeGiftImage(item.image)} alt={item.name} className="w-28 h-28 object-contain mb-1" onError={useDefaultGiftImage} />
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

                {hasSpun && wonItems.length > 0 && showResult && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="mt-4"
                  >
                    <p className="text-white/50 text-xs text-center mb-4 uppercase tracking-wider font-rounded">Вы выиграли!</p>
                    
                    <div className={`grid gap-4 ${wonItems.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
                      {wonItems.map((wonItem, idx) => (
                        <motion.div
                          key={`${wonItem.name}-${idx}`}
                          initial={{ opacity: 0, y: 20 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ delay: idx * 0.1 }}
                          className="text-center p-4 rounded-3xl relative overflow-hidden border"
                          style={{
                            borderColor: `${caseItem.glowColor}30`,
                            backgroundColor: `${caseItem.glowColor}10`,
                          }}
                        >
                          <div className="relative z-10">
                            <motion.img
                              src={getDynamicGiftImage(wonItem)}
                              alt={wonItem.name}
                              className={`${wonItems.length > 1 ? 'h-24 w-24' : 'h-48 w-48'} object-contain mx-auto mb-2`}
                              onError={useDefaultGiftImage}
                              style={{ filter: `drop-shadow(0 0 25px ${caseItem.glowColor}90)` }}
                            />
                            <p
                              className={`${wonItems.length > 1 ? 'text-sm' : 'text-2xl'} text-white font-black mb-1 font-rounded`}
                              style={{ color: caseItem.glowColor }}
                            >
                              {wonItem.name}
                            </p>
                            <div className="flex items-center justify-center gap-1 text-white/70 text-sm">
                              <span className="flex items-center gap-1 font-black font-rounded">
                                {wonItem.price}
                                <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" />
                              </span>
                            </div>
                          </div>
                        </motion.div>
                      ))}
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
                      <span className="text-sm">Открываем... ({wonItems.length}/{quantity})</span>
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
              {/* Quantity Selector */}
              <div className="mb-6">
                <h3 className="text-white/50 text-[10px] uppercase tracking-widest mb-3 font-black">Количество открытий</h3>
                <div className="flex gap-2">
                  {[1, 3, 5, 10].map((q) => (
                    <button
                      key={q}
                      disabled={caseItem.name === 'Daily Case' && q > 1}
                      onClick={() => {
                        setQuantity(q);
                        triggerHaptic('light');
                      }}
                      className={`flex-1 py-3 rounded-xl border font-black transition-all ${
                        quantity === q 
                          ? 'bg-white/10 border-white/40 text-white' 
                          : 'bg-white/5 border-white/10 text-white/30 hover:bg-white/10'
                      } ${caseItem.name === 'Daily Case' && q > 1 ? 'opacity-0 pointer-events-none' : ''}`}
                    >
                      x{q}
                    </button>
                  ))}
                </div>
              </div>

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
                    <img src={normalizeGiftImage(item.image)} alt={item.name} className="w-12 h-12 object-contain mb-1" onError={useDefaultGiftImage} />
                    <p className="text-white text-[10px] font-semibold text-center truncate w-full">{item.name}</p>
                    <div className="flex items-center justify-center gap-1 text-white/50 text-[8px]">
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
                  {caseItem.price * quantity}
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
                  ОТКРЫТЬ x{quantity} ЗА {getCost}
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
          <div className="text-center py-2 text-white/30 text-sm font-rounded uppercase tracking-widest">Открытие {quantity} {quantity === 1 ? 'кейса' : 'кейсов'}...</div>
        )}
      </div>
    </div>
  );
}
