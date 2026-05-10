import React, { useState, useRef } from 'react';
import { motion, AnimatePresence, useAnimation } from 'framer-motion';
import Confetti from 'react-confetti';

const RARITY_COLORS = {
  common: '#888888',
  uncommon: '#00ff00',
  rare: '#0099ff',
  epic: '#ff00ff',
  legendary: '#ffaa00'
};

// easeOutQuart function
const easeOutQuart = (x) => 1 - Math.pow(1 - x, 4);

export default function CasePreviewModal({ caseItem, onClose, onWin, balance, setBalance }) {
  const [showDropList, setShowDropList] = useState(true);
  const [isSpinning, setIsSpinning] = useState(false);
  const [hasSpun, setHasSpun] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [showConfetti, setShowConfetti] = useState(false);
  const [promoCode, setPromoCode] = useState('');
  const [showResult, setShowResult] = useState(false);
  const [wonItem, setWonItem] = useState(null); // Store the actual won item
  const controls = useAnimation();

  const isPromo = caseItem.id === 1;
  const canOpen = !isPromo || promoCode.trim().length > 0;

  // Create spin items from caseItem.dropItems
  const spinItems = useMemo(() => {
    if (!caseItem.dropItems || caseItem.dropItems.length === 0) {
      return [{ id: 1, name: 'Default', color: '#888888', rarity: 'common', image: '/asset/Gifts/Xmas Stockings.png' }];
    }
    return caseItem.dropItems.map((item, idx) => ({
      id: idx + 1,
      name: item.name,
      color: RARITY_COLORS[item.rarity] || '#888888',
      rarity: item.rarity,
      image: item.image,
      value: item.value
    }));
  }, [caseItem]);

  const TRIPLE_LOOT = [...spinItems, ...spinItems, ...spinItems];
  const ITEM_WIDTH = 120;
  const CONTAINER_WIDTH = ITEM_WIDTH * 5;
  const MIDDLE_START = spinItems.length;

export default function CasePreviewModal({ caseItem, onClose, onWin, balance, setBalance }) {
  const [showDropList, setShowDropList] = useState(true);
  const [isSpinning, setIsSpinning] = useState(false);
  const [hasSpun, setHasSpun] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const [showConfetti, setShowConfetti] = useState(false);
  const [promoCode, setPromoCode] = useState('');
  const [showResult, setShowResult] = useState(false);
  const controls = useAnimation();

  const isPromo = caseItem.id === 1;
  const canOpen = !isPromo || promoCode.trim().length > 0;

  const handleOpen = () => {
    if (isSpinning || !canOpen) return;

    // Deduct balance FIRST
    if (setBalance && caseItem.price > 0) {
      setBalance(prev => Math.max(0, prev - caseItem.price));
    }

    // Hide drop list, show spin
    setShowDropList(false);
    setIsSpinning(true);
    setHasSpun(false);
    setSelectedItem(null);
    setShowConfetti(false);
    setShowResult(false);

    // Determine winning item from spinItems - THIS IS THE ITEM THAT WILL BE WON
    const winIndex = Math.floor(Math.random() * spinItems.length);
    const actualWonItem = spinItems[winIndex];
    setWonItem(actualWonItem); // Store for inventory

    // Calculate target position - STRICTLY TIED TO WON ITEM ID
    const targetIndex = MIDDLE_START + winIndex;
    const itemCenterPos = targetIndex * ITEM_WIDTH + ITEM_WIDTH / 2;
    const containerCenter = CONTAINER_WIDTH / 2;
    const targetX = -(itemCenterPos - containerCenter);
    const startX = containerCenter + 2000;

    controls.set({ x: startX });

    setTimeout(() => {
      controls.start({
        x: targetX,
        transition: {
          duration: 5,
          ease: (t) => easeOutQuart(t),
        }
      }).then(() => {
        setSelectedItem(actualWonItem); // Show the SAME item that was won
        setHasSpun(true);
        setIsSpinning(false);
        setShowConfetti(true);
        setShowResult(true);

        // Call onWin callback to add item to inventory - PASS THE ACTUAL WON ITEM
        if (onWin) {
          onWin(actualWonItem, caseItem);
        }

        // Stop confetti after 3 seconds
        setTimeout(() => setShowConfetti(false), 3000);
      });
    }, 100);
  };

  const handleClaim = () => {
    setShowConfetti(false);
    onClose();
  };

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex flex-col bg-black"
    >
      {/* Confetti Effect */}
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

      {/* Backdrop */}
      <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />

      {/* Content */}
      <div className="relative z-10 flex-1 overflow-y-auto">
        {/* Header */}
        <div className="glass-panel border-b border-white/10 px-6 py-4 flex items-center justify-between sticky top-0 z-20">
          <button
            onClick={!isSpinning && !showResult ? onClose : undefined}
            className="text-white/50 hover:text-white text-xl"
          >
            ←
          </button>
          <h2 className="text-white font-bold text-lg">{caseItem.name}</h2>
          <div className="w-8" />
        </div>

        {/* Case Preview Section - Always visible */}
        <div className="relative h-64 mx-4 mt-6 mb-4">
          {/* Radial glow */}
          <div
            className="absolute inset-0 rounded-3xl"
            style={{
              background: `radial-gradient(ellipse at center, ${caseItem.glowColor}20, transparent 70%)`,
              filter: 'blur(20px)',
            }}
          />

          {/* Floating Gift - positioned at same level as case */}
          <motion.div
            animate={{ y: [0, -6, 0] }}
            transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
            className="absolute top-4 left-1/2 transform -translate-x-1/2 z-10"
          >
            <div
              className="rounded-2xl p-4"
              style={{ backgroundColor: `${caseItem.glowColor}15` }}
            >
              <img
                src={caseItem.topGift}
                alt="Top Gift"
                className="w-20 h-20 object-contain"
                style={{ filter: `drop-shadow(0 0 20px ${caseItem.glowColor}80)` }}
              />
            </div>
          </motion.div>

          {/* Case Image */}
          <div className="absolute bottom-0 left-1/2 transform -translate-x-1/2">
            <img
              src="/asset/Case/CaseBlack.png"
              alt={caseItem.name}
              className="w-48 h-48 object-contain"
              style={{ filter: `drop-shadow(0 0 30px ${caseItem.glowColor}80)` }}
            />
          </div>
        </div>

        {/* Drop List - Show initially, hide during spin */}
        <AnimatePresence>
          {showDropList && (
            <motion.div
              initial={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="mx-4 mb-6"
            >
              <h3 className="text-white/50 text-xs uppercase tracking-wider mb-3">Возможный дроп</h3>
              <div className="grid grid-cols-3 gap-2">
                {caseItem.dropItems.map((item, idx) => (
                  <motion.div
                    key={idx}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: idx * 0.05 }}
                    className="glass-panel p-2 flex flex-col items-center"
                  >
                    <img src={item.image} alt={item.name} className="w-12 h-12 object-contain mb-1" />
                    <p className="text-white text-[10px] font-semibold text-center truncate w-full">{item.name}</p>
                    <p className="text-white/50 text-[8px]">{item.value}<img src="/asset/Icons/TelegramStar.png" className="inline-block h-2.5 w-2.5 mb-0.5" /></p>
                    <span
                      className="inline-block px-1 py-0.5 rounded text-[8px] font-bold uppercase mt-0.5"
                      style={{
                        backgroundColor: RARITY_COLORS[item.rarity] + '20',
                        color: RARITY_COLORS[item.rarity],
                      }}
                    >
                      {item.rarity}
                    </span>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Promo Code Field - Inside modal for Promo Case */}
        {isPromo && showDropList && (
          <div className="mx-4 mb-4">
            <input
              type="text"
              value={promoCode}
              onChange={(e) => setPromoCode(e.target.value)}
              placeholder="Введите промокод"
              className="glass-input w-full px-4 py-3 text-sm"
            />
          </div>
        )}

        {/* Spin Section - Appears after clicking Open */}
        <AnimatePresence>
          {isSpinning || hasSpun ? (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="mx-4 mb-6"
            >
              <div className="glass-panel p-4">
                {/* Pointer */}
                <div className="relative mb-4">
                  <div className="absolute left-1/2 top-0 transform -translate-x-1/2 z-30">
                    <div className="w-0 h-0 border-l-4 border-r-4 border-t-8 border-l-transparent border-r-transparent border-t-white" />
                  </div>
                  <div className="absolute left-1/2 top-2 transform -translate-x-1/2 w-0.5 h-32 bg-white/30 z-20 pointer-events-none" />

                  {/* Ribbon */}
                  <div className="overflow-hidden rounded-2xl bg-white/[0.02] border border-white/10 p-4">
                    <motion.div
                      className="flex gap-3"
                      animate={controls}
                    >
                      {TRIPLE_LOOT.map((item, idx) => (
                        <div
                          key={`${item.id}-${idx}`}
                          className="flex-shrink-0 w-28 h-28 rounded-xl border-2 flex flex-col items-center justify-center p-2"
                          style={{
                            borderColor: item.color + '40',
                            backgroundColor: item.color + '10',
                          }}
                        >
                          <img src={item.image} alt={item.name} className="w-14 h-14 object-contain mb-1" />
                          <span className="text-white/70 text-[10px] text-center font-semibold uppercase">{item.rarity}</span>
                        </div>
                      ))}
                    </motion.div>
                  </div>
                </div>

                {/* Win Result with Bloom Effect */}
                {hasSpun && selectedItem && showResult && (
                  <motion.div
                    initial={{ opacity: 0, scale: 0.8 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="text-center p-4 rounded-2xl relative overflow-hidden mt-4"
                    style={{
                      borderColor: selectedItem.color + '30',
                      backgroundColor: selectedItem.color + '10',
                    }}
                  >
                    {/* Bloom/Glow Effect */}
                    <motion.div
                      animate={{
                        scale: [1, 1.2, 1],
                        opacity: [0.3, 0.6, 0.3],
                      }}
                      transition={{ duration: 2, repeat: Infinity }}
                      className="absolute inset-0 rounded-2xl"
                      style={{
                        backgroundColor: selectedItem.color + '20',
                        filter: 'blur(20px)',
                      }}
                    />

                    <div className="relative z-10">
                      <p className="text-white/50 text-xs mb-2 uppercase tracking-wider">Вы выиграли!</p>
                      <motion.img
                        src={selectedItem.image}
                        alt={selectedItem.name}
                        className="h-24 w-24 object-contain mx-auto mb-3"
                        style={{ filter: `drop-shadow(0 0 30px ${selectedItem.color}80)` }}
                        animate={{
                          scale: [1, 1.05, 1],
                        }}
                        transition={{ duration: 1.5, repeat: Infinity }}
                      />
                      <p
                        className="text-white font-black text-2xl mb-2"
                        style={{ color: selectedItem.color }}
                      >
                        {selectedItem.name}
                      </p>
                      <span
                        className="inline-block px-3 py-1 rounded-lg text-xs font-bold uppercase tracking-wider"
                        style={{
                          backgroundColor: selectedItem.color + '20',
                          color: selectedItem.color,
                          border: `1px solid ${selectedItem.color}40`,
                        }}
                      >
                        {selectedItem.rarity}
                      </span>
                    </div>
                  </motion.div>
                )}

                {/* Spinning Indicator */}
                {isSpinning && !hasSpun && (
                  <div className="text-center py-3">
                    <div className="inline-flex items-center gap-2 text-white/50">
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
          ) : null}
        </AnimatePresence>
      </div>

      {/* Bottom Action Button - Stays in same position */}
      <div className="glass-panel border-t border-white/10 p-4">
        {showDropList ? (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleOpen}
            disabled={!canOpen || balance < caseItem.price}
            className="w-full py-4 rounded-xl font-black text-lg disabled:opacity-50 transition-all"
            style={{
              backgroundColor: canOpen && balance >= caseItem.price ? `${caseItem.glowColor}20` : 'rgba(255,255,255,0.05)',
              border: `1px solid ${canOpen && balance >= caseItem.price ? `${caseItem.glowColor}40` : 'rgba(255,255,255,0.1)'}`,
              color: canOpen && balance >= caseItem.price ? caseItem.glowColor : 'rgba(255,255,255,0.3)',
            }}
          >
            {caseItem.price === 0 ? 'ОТКРЫТЬ БЕСПЛАТНО' : `ОТКРЫТЬ ЗА ${caseItem.price} <img src="/asset/Icons/TelegramStar.png" className="inline-block h-5 w-5 mb-1" />`}
          </motion.button>
        ) : hasSpun && showResult ? (
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleClaim}
            className="w-full py-4 rounded-xl bg-white/10 border border-white/20 text-white font-bold text-lg"
          >
            Забрать
          </motion.button>
        ) : (
          <div className="text-center py-2 text-white/30 text-sm">Открытие кейса...</div>
        )}
      </div>
    </motion.div>
  );
}
