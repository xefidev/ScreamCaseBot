import React, { useState, useMemo, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Confetti from 'react-confetti';
import { getGiftsInRange, ALL_GIFTS } from '../giftData';
import { openCase } from '../api';
import { getDynamicGiftImage, DEFAULT_GIFT_IMAGE } from '../giftUtils';
import { playSound } from '../App';

export default function CasePreview({ user, caseItem, onClose, onWin, balance, setBalance, setSpent, flashDiscount = null, promoOpened = false, setPromoOpened = null, onTopUpRequest, lowPerf = false }) {
  const [isSpinning, setIsSpinning] = useState(false);
  const [hasSpun, setHasSpun] = useState(false);
  const [showConfetti, setShowConfetti] = useState(false);
  const [showResult, setShowResult] = useState(false);
  const [wonItems, setWonItems] = useState([]);
  const [spinData, setSpinData] = useState({ items: [], targetX: 0 });
  const [currentStock, setCurrentStock] = useState(caseItem?.remaining_limit !== undefined ? caseItem?.remaining_limit : (caseItem?.stock || 0));
  const [quantity, setQuantity] = useState(1);
  const [promoCode, setPromoCode] = useState('');
  const [isCollecting, setIsCollecting] = useState(false);
  const animationKey = useRef(0);

  if (!caseItem) return null;

  const isDaily = caseItem?.name?.toLowerCase()?.includes('daily');
  const isPromo = !!caseItem?.isPromo || caseItem?.name?.toLowerCase() === 'promo';
  const hasLimit = caseItem?.total_limit !== -1;
  const canOpen = (!hasLimit || currentStock >= quantity) && (!isPromo || promoCode.trim().length > 0);

  const getCost = useMemo(() => {
    if (isPromo) return 0;
    if (isDaily) return 1;
    let basePrice = caseItem?.price || 0;
    if (flashDiscount && basePrice > 0) {
      basePrice = Math.floor(basePrice * (1 - flashDiscount));
    }
    return basePrice * quantity;
  }, [caseItem?.price, flashDiscount, quantity, isPromo, isDaily]);

  const dropItems = useMemo(() =>
    getGiftsInRange(caseItem?.minPrice || 0, caseItem?.maxPrice || 0),
    [caseItem?.minPrice, caseItem?.maxPrice]
  );

  const previewGifts = useMemo(() => {
    if (!dropItems || dropItems.length === 0) return [];
    if (dropItems.length === 1) return [dropItems[0]];
    const sorted = [...dropItems].sort((a, b) => b.price - a.price);
    return sorted.slice(0, 2);
  }, [dropItems]);

  const spinItems = useMemo(() => {
    if (dropItems.length === 0) return ALL_GIFTS.slice(0, 8);
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
    if (isSpinning || !user?.id) return;

    // promo code validated server-side via openCase

    const totalCost = getCost;
    
    if (balance < totalCost) {
        window?.Telegram?.WebApp?.showAlert?.("\u041d\u0435\u0434\u043e\u0441\u0442\u0430\u0442\u043e\u0447\u043d\u043e \u0437\u0432\u0451\u0437\u0434!");
        return;
    }

    if (isPromo && promoCode.trim().length === 0) {
        window?.Telegram?.WebApp?.showAlert?.("❌ Введите промокод");
        return;
    }
    if (!canOpen) {
       window?.Telegram?.WebApp?.showAlert?.("\u274c \u041a\u0435\u0439\u0441 \u0432\u0440\u0435\u043c\u0435\u043d\u043d\u043e \u043d\u0435\u0434\u043e\u0441\u0442\u0443\u043f\u0435\u043d");
       return;
    }

    // \u041e\u043f\u0442\u0438\u043c\u0438\u0441\u0442\u0438\u0447\u043d\u043e\u0435 \u0441\u043f\u0438\u0441\u0430\u043d\u0438\u0435 \u0434\u043b\u044f UI (\u0435\u0441\u043b\u0438 \u0446\u0435\u043d\u0430 > 0)
    if (setBalance && totalCost > 0) {
        setBalance(prev => Math.max(0, prev - totalCost));
    }

    playSound('/asset/Sounds/go-new-gambling.mp3');
    
    setIsSpinning(true);
    setWonItems([]);

    let lastServerBalance = null; // \u0411\u0430\u043b\u0430\u043d\u0441 \u0441 \u0441\u0435\u0440\u0432\u0435\u0440\u0430 \u043f\u043e\u0441\u043b\u0435 \u043e\u0442\u043a\u0440\u044b\u0442\u0438\u044f

    try {
        const results = [];
        const targetQuantity = (isDaily || isPromo) ? 1 : quantity;

        for (let i = 0; i < targetQuantity; i++) {
          const response = await openCase(user?.id, caseItem?.id, isPromo ? promoCode.trim().toUpperCase() : null);
          // \u0421\u0435\u0440\u0432\u0435\u0440 \u0432\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0435\u0442: { ok, success, item, deducted, new_balance }
          if (!response?.success || !response?.item) throw new Error(`Failed to open case ${i+1}`);
          results.push(response.item);
          // \u0421\u043e\u0445\u0440\u0430\u043d\u044f\u0435\u043c \u0440\u0435\u0430\u043b\u044c\u043d\u044b\u0439 \u0431\u0430\u043b\u0430\u043d\u0441 \u0441 \u0441\u0435\u0440\u0432\u0435\u0440\u0430
          if (typeof response.new_balance === 'number') {
            lastServerBalance = response.new_balance;
          }
        }

        // \u0421\u0438\u043d\u0445\u0440\u043e\u043d\u0438\u0437\u0438\u0440\u0443\u0435\u043c \u0431\u0430\u043b\u0430\u043d\u0441 \u0441 \u0438\u0441\u0442\u0438\u043d\u043d\u044b\u043c \u0437\u043d\u0430\u0447\u0435\u043d\u0438\u0435\u043c \u0441\u0435\u0440\u0432\u0435\u0440\u0430
        if (setBalance && lastServerBalance !== null) {
          setBalance(lastServerBalance);
          console.log('\u2705 \u0411\u0430\u043b\u0430\u043d\u0441 \u043f\u043e\u0441\u043b\u0435 \u043e\u0442\u043a\u0440\u044b\u0442\u0438\u044f \u043a\u0435\u0439\u0441\u0430:', lastServerBalance);
        }

        triggerHaptic();
        if (setSpent) setSpent(prev => prev + totalCost);
        // promo no longer one-time gated; server enforces validity
        setCurrentStock(prev => Math.max(0, prev - targetQuantity));

        setWonItems(results);
        setHasSpun(false);
        setShowConfetti(false);
        setShowResult(false);

        const lastWonItem = results[results.length - 1];

        // Строим ленту из 10 повторов spinItems, НО подменяем целевую позицию на реальный выигрыш с сервера.
        // Это гарантирует визуальное совпадение независимо от findIndex.
        const repetitions = 10;
        const extendedItems = [];
        for (let r = 0; r < repetitions; r++) extendedItems.push(...spinItems);

        // Ищем выигрыш в локальном пуле (для красивого случая); если нет — всё равно подменим
        let winIndex = spinItems.findIndex(i => i?.name === lastWonItem?.name);
        if (winIndex === -1) {
            winIndex = Math.floor(spinItems.length / 2);
            console.warn('⚠️ Выигранный предмет не найден в spinItems:', lastWonItem?.name);
        }

        const targetIndex = spinItems.length * 7 + winIndex;
        // КРИТИЧНО: подменяем ячейку на targetIndex на реальный выигрыш
        if (lastWonItem && targetIndex < extendedItems.length) {
            extendedItems[targetIndex] = { ...lastWonItem };
        }

        const viewportWidth = viewportRef.current ? viewportRef.current.offsetWidth : (window.innerWidth - 64);
        const containerCenter = viewportWidth / 2;
        const itemCenter = (targetIndex * FULL_ITEM_WIDTH) + (ITEM_SIZE / 2);
        const targetX = containerCenter - itemCenter;

        animationKey.current += 1;
        // Play spin sound synchronized with wheel start (not before server response)
        playSound('/asset/Sounds/go-new-gambling.mp3');
        setSpinData({ items: extendedItems, targetX, animKey: animationKey.current });
        // Low perf mode — skip animation, show result immediately
        if (lowPerf) {
          setHasSpun(true);
          setIsSpinning(false);
          setShowConfetti(true);
          setShowResult(true);
          playSound('/asset/Sounds/win_sound.mp3');
          if (onWin && wonItems?.length > 0) {
            wonItems.forEach(item => { if (item) onWin(item, caseItem); });
          }
          setTimeout(() => setShowConfetti(false), 3000);
        }
    } catch (e) {
        window.scrollTo({ top: 0, behavior: 'smooth' });
        if (viewportRef.current) viewportRef.current.scrollTo({ left: 0, behavior: 'auto' });
        console.error("Error in handleOpen:", e);
        stopSound();
        setIsSpinning(false);
        // \u041e\u0442\u043a\u0430\u0442 \u043e\u043f\u0442\u0438\u043c\u0438\u0441\u0442\u0438\u0447\u043d\u043e\u0433\u043e \u0441\u043f\u0438\u0441\u0430\u043d\u0438\u044f \u2014 \u0432\u043e\u0437\u0432\u0440\u0430\u0449\u0430\u0435\u043c \u043b\u043e\u043a\u0430\u043b\u044c\u043d\u0443\u044e \u0441\u0443\u043c\u043c\u0443 (\u0441\u0435\u0440\u0432\u0435\u0440 \u043d\u0435 \u0441\u043f\u0438\u0441\u0430\u043b, \u0442\u0430\u043a \u043a\u0430\u043a \u043e\u0448\u0438\u0431\u043a\u0430)
        if (setBalance && totalCost > 0) setBalance(prev => prev + totalCost);
        if (window.Telegram?.WebApp) window.Telegram.WebApp.showAlert("\u274c \u041e\u0448\u0438\u0431\u043a\u0430 \u043f\u0440\u0438 \u043e\u0442\u043a\u0440\u044b\u0442\u0438\u0438 \u043a\u0435\u0439\u0441\u0430");
    }
  };

  const handleAnimationComplete = () => {
    // Защита от двойного триггера — если анимация уже завершена, игнорируем
    if (hasSpun) return;
    setTimeout(() => {
      setHasSpun(true);
      setIsSpinning(false);
      setShowConfetti(true);
      setShowResult(true);
      playSound('/asset/Sounds/win_sound.mp3');
      if (onWin && wonItems?.length > 0) {
        wonItems.forEach(item => { if (item) onWin(item, caseItem); });
      }
      setTimeout(() => setShowConfetti(false), 3000);
    }, 100);
  };

  const handleClaim = () => {
    if (isCollecting) return;
    setIsCollecting(true);
    triggerHaptic();
    setShowConfetti(false);
    onClose();
  };

  const isLowBalance = balance < getCost;
  const missingAmount = getCost - balance;

  return (
    <div className="h-full flex flex-col bg-[#1a1b1e]">
      {showConfetti && (
        <div className="fixed inset-0 z-60 pointer-events-none">
          <Confetti width={window.innerWidth} height={window.innerHeight} recycle={false} numberOfPieces={200} />
        </div>
      )}

      <div className="relative z-10 flex-1 overflow-y-auto custom-scrollbar">
        <div className="px-6 py-4 flex items-center justify-between sticky top-0 z-20 bg-[#1a1b1e]/80 backdrop-blur-lg">
          <button onClick={() => { if (!isSpinning && !showResult) { onClose(); triggerHaptic(); } }} className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/5 border border-white/10 text-white hover:bg-white/10 transition-colors">
            <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"><path d="m15 18-6-6 6-6"/></svg>
          </button>
          <div className="flex flex-col items-center">
            <h2 className="text-white font-black text-xl uppercase tracking-tighter">{caseItem?.name || 'Case'}</h2>
            <div className="flex items-center gap-1.5 mt-0.5">
              <div className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse" />
              <p className="text-white/40 text-[10px] uppercase font-black tracking-widest">
                {caseItem?.total_limit === -1 ? 'Бесконечно' : `Осталось: ${currentStock} / ${caseItem?.total_limit ?? '?'}`}
              </p>
            </div>
          </div>
          <div className="w-10" />
        </div>

        <div className="relative h-64 mx-4 mb-4">
          <div className="absolute inset-0 rounded-3xl" style={{ background: `radial-gradient(ellipse at center, ${caseItem?.glowColor || '#ffffff'}20, transparent 70%)` }} />
          <div className="absolute inset-0 flex items-center justify-center">
            {previewGifts?.map((gift, idx) => (
              <motion.div key={idx} animate={{ y: [0, -12, 0], rotate: [0, 4, -4, 0], scale: [1.3, 1.4, 1.3] }} transition={{ duration: 2.5 + idx * 0.4, repeat: Infinity, ease: "easeInOut", delay: idx * 0.6 }} className="absolute" style={{ left: previewGifts?.length === 1 ? '50%' : idx === 0 ? '35%' : '65%', top: '15%', transform: 'translateX(-50%)', zIndex: 10 }}>
                <div className="rounded-3xl p-4" style={{ backgroundColor: `${caseItem?.glowColor || '#ffffff'}15` }}>
                  <img src={getDynamicGiftImage(gift)} alt="Gift" className="w-28 h-28 object-contain" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} style={{ filter: `drop-shadow(0 0 15px ${caseItem?.glowColor || '#ffffff'}80)` }} />
                </div>
              </motion.div>
            ))}
          </div>
          <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2">
            <img src={caseItem?.image || '/asset/Case/CaseBlack.png'} alt="Case" className="w-48 h-48 object-contain" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} style={{ filter: `drop-shadow(0 0 30px ${caseItem?.glowColor || '#ffffff'}80)` }} />
          </div>
        </div>

        <AnimatePresence>
          {(isSpinning || hasSpun) && (
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="mx-4 mb-6">
              <div className="glass-panel p-4 border-white/10 bg-white/[0.02]">
                <div className="relative mb-4">
                  <div className="absolute left-1/2 top-0 transform -translate-x-1/2 z-30"><div className="w-0 h-0 border-l-4 border-r-4 border-t-8 border-l-transparent border-r-transparent border-t-white" /></div>
                  <div className="absolute left-1/2 top-2 transform -translate-x-1/2 w-0.5 h-40 bg-white/30 z-20 pointer-events-none" />
                  <div ref={viewportRef} className="overflow-hidden rounded-2xl bg-white/[0.02] border border-white/10 p-4">
                    {spinData?.items?.length > 0 && (
                      <motion.div key={spinData?.animKey} className="flex gap-3" initial={{ x: 0 }} animate={{ x: spinData?.targetX }} transition={{ duration: 4, ease: [0.12, 0, 0.39, 0] }} onAnimationComplete={handleAnimationComplete} style={{ willChange: 'transform', transform: 'translateZ(0)' }}>
                        {spinData?.items?.map((item, idx) => (
                          <div key={idx} className="flex-shrink-0 w-36 h-36 rounded-2xl border-2 flex flex-col items-center justify-center p-2" style={{ borderColor: `${caseItem?.glowColor || '#ffffff'}40`, backgroundColor: `${caseItem?.glowColor || '#ffffff'}10` }}>
                            <img src={getDynamicGiftImage(item)} alt="Gift" className="w-28 h-28 object-contain mb-1" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                            <div className="flex items-center justify-center gap-1 text-[10px] text-white/70">
                              <span className="font-bold flex items-center gap-0.5 font-rounded text-xs">{item?.price ?? item?.cost ?? 0} <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} /></span>
                            </div>
                          </div>
                        ))}
                      </motion.div>
                    )}
                  </div>
                </div>

                {hasSpun && wonItems?.length > 0 && showResult && (
                  <motion.div initial={{ opacity: 0, scale: 0.8 }} animate={{ opacity: 1, scale: 1 }} className="mt-4">
                    <p className="text-white/50 text-xs text-center mb-4 uppercase tracking-widest font-black">
                      {wonItems?.length > 1 ? `ПОЗДРАВЛЯЕМ! +${wonItems.length} ПРЕДМЕТОВ` : 'ПОЗДРАВЛЯЕМ! ВЫ ВЫИГРАЛИ!'}
                    </p>
                    <div className={`grid gap-4 ${wonItems?.length > 2 ? 'grid-cols-2' : wonItems?.length > 1 ? 'grid-cols-2' : 'grid-cols-1'}`}>
                      {wonItems?.map((wonItem, idx) => wonItem && (
                        <motion.div key={idx} initial={{ opacity: 0, y: 20, scale: 0.8 }} animate={{ opacity: 1, y: 0, scale: 1 }} transition={{ delay: idx * 0.15, duration: 0.4 }} className="text-center p-4 rounded-3xl relative overflow-hidden border" style={{ borderColor: `${caseItem?.glowColor || '#ffffff'}30`, backgroundColor: `${caseItem?.glowColor || '#ffffff'}10` }}>
                          <motion.img src={getDynamicGiftImage(wonItem)} alt="Gift" className={`${wonItems?.length > 2 ? 'h-16 w-16' : wonItems?.length > 1 ? 'h-24 w-24' : 'h-48 w-48'} object-contain mx-auto mb-2`} onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} animate={{ y: [0, -4, 0] }} transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }} style={{ willChange: 'transform', transform: 'translateZ(0)', filter: `drop-shadow(0 0 15px ${caseItem?.glowColor || '#ffffff'}60)` }} />
                          <p className={`${wonItems?.length > 2 ? 'text-[10px]' : wonItems?.length > 1 ? 'text-xs' : 'text-xl'} text-white font-black mb-1 font-rounded uppercase tracking-tight truncate`} style={{ color: caseItem?.glowColor || '#ffffff' }} title={wonItem?.name || 'Gift'}>{wonItem?.name || 'Gift'}</p>
                          <div className="flex items-center justify-center gap-1 text-white/70 text-sm"><span className="flex items-center gap-1 font-black font-rounded text-xs">{wonItem?.price ?? wonItem?.cost ?? 0} <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3" alt="Stars" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} /></span></div>
                        </motion.div>
                      ))}
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        <AnimatePresence>
          {!isSpinning && !hasSpun && (
            <motion.div initial={{ opacity: 1 }} exit={{ opacity: 0 }} className="mx-4 mb-6">
              {isPromo && (
                <div className="mb-6 glass-panel p-4 bg-white/5 border-white/10">
                  <h3 className="text-white text-[10px] uppercase tracking-[0.2em] mb-3 font-black">Введите промокод</h3>
                  <input type="text" value={promoCode} onChange={(e) => setPromoCode(e.target.value)} placeholder="ВВЕДИТЕ КОД" className="w-full bg-white/5 border border-white/10 rounded-xl p-3 text-white font-black uppercase tracking-widest focus:outline-none focus:border-white/30" />
                </div>
              )}
              <div className="mb-8">
                <h3 className="text-white text-[10px] uppercase tracking-[0.2em] mb-3 font-black">Количество открытий</h3>
                <div className="flex gap-2">
                  {[1, 3, 6, 10].map((q) => {
                    if (q !== 1 && (isDaily || isPromo)) return null;
                    return (
                      <button key={q} onClick={() => { setQuantity(q); triggerHaptic('light'); }} className={`flex-1 py-3 rounded-xl border font-black transition-all ${quantity === q ? 'bg-white/10 border-white/40 text-white shadow-[0_0_15px_rgba(255,255,255,0.05)]' : 'bg-white/5 border-white/10 text-white/30 hover:bg-white/10'}`}>x{q}</button>
                    );
                  })}
                </div>
              </div>

              <h3 className="text-white text-[10px] uppercase tracking-[0.2em] mb-4 font-black text-center">Возможный дроп</h3>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 w-full p-4 max-h-[32rem] overflow-y-auto pr-1 custom-scrollbar justify-items-center">
                {dropItems?.map((item, idx) => (
                  <motion.div key={idx} whileHover={{ scale: 1.05 }} className="glass-panel w-full max-w-[140px] p-3 flex flex-col items-center bg-white/[0.03] border border-white/5 rounded-2xl shadow-lg">
                    <div className="w-16 h-16 flex items-center justify-center mb-2">
                        <img src={getDynamicGiftImage(item)} alt="Gift" className="w-full h-full object-contain" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                    </div>
                    <p className="text-white font-bold text-[10px] text-center truncate w-full uppercase tracking-tight mb-1">{item?.name || 'Gift'}</p>
                    <div className="flex items-center justify-center gap-1.5 px-2 py-0.5 rounded-full bg-white/5 border border-white/5">
                        <span className="text-white/60 text-[9px] font-black">{item?.price ?? item?.cost ?? 0}</span>
                        <img src="/asset/Icons/TelegramStar.png" className="h-2.5 w-2.5" alt="Stars" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                    </div>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="p-4 bg-[#1a1b1e] border-t border-white/10">
        {!isSpinning && !hasSpun ? (
          <motion.button 
            whileHover={{ scale: 1.02 }} 
            whileTap={{ scale: 0.98 }} 
            onClick={isLowBalance ? () => onTopUpRequest(missingAmount) : handleOpen} 
            className="w-full py-5 rounded-2xl font-black text-lg transition-all flex items-center justify-center gap-3 uppercase tracking-tighter shadow-lg shadow-black/20" 
            style={{ 
              backgroundColor: isLowBalance ? 'rgba(234, 179, 8, 0.2)' : (isPromo && promoOpened) ? 'rgba(255,255,255,0.05)' : (caseItem?.glowColor || '#ffffff') + '20', 
              border: `1px solid ${isLowBalance ? 'rgba(234, 179, 8, 0.4)' : (isPromo && promoOpened) ? 'rgba(255,255,255,0.1)' : (caseItem?.glowColor || '#ffffff') + '40'}`, 
              color: isLowBalance ? '#eab308' : (isPromo && promoOpened) ? 'rgba(255,255,255,0.2)' : (caseItem?.glowColor || '#ffffff')
            }}
          >
            {isLowBalance ? (
              <div className="flex items-center gap-2">
                <span>ПОПОЛНИТЬ НА {missingAmount}</span>
                <img src="/asset/Icons/TelegramStar.png" className="h-6 w-6" alt="Stars" />
              </div>
            ) : isPromo && promoOpened ? 'УЖЕ ОТКРЫТО' : (isPromo || caseItem?.price === 0) ? 'ОТКРЫТЬ БЕСПЛАТНО' : (
              <div className="flex items-center justify-center gap-2">
                <span>ОТКРЫТЬ x{isDaily ? 1 : quantity}</span>
                <div className="w-px h-4 bg-white/20 mx-1" />
                <span className="flex items-center gap-1">
                  {isDaily ? 1 : getCost} 
                  <img src="/asset/Icons/TelegramStar.png" className="h-6 w-6" alt="Stars" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                </span>
              </div>
            )}
          </motion.button>
        ) : hasSpun && showResult ? (
          <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={handleClaim} disabled={isCollecting} className="w-full py-5 rounded-2xl bg-white/10 border border-white/20 text-white font-black text-xl font-rounded flex items-center justify-center disabled:opacity-50 shadow-lg shadow-black/20 uppercase tracking-widest">ЗАБРАТЬ</motion.button>
        ) : (
          <div className="flex flex-col items-center justify-center py-2 gap-2">
            <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} className="w-6 h-6 border-3 border-white/10 border-t-white rounded-full" />
            <div className="text-center text-white/30 text-[10px] font-black uppercase tracking-[0.3em]">Открытие...</div>
          </div>
        )}
      </div>
    </div>
  );
}
