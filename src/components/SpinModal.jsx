import React, { useState, useEffect, useRef } from 'react';
import { motion, useAnimation, AnimatePresence } from 'framer-motion';
import { normalizeGiftImage, useDefaultGiftImage } from '../giftUtils';

const LOOT_ITEMS = [
  { id: 1, name: 'Xmas Stockings', color: '#ff0000', rarity: 'common', image: '/asset/Gifts/300S_Xmas Stockings.png' },
  { id: 2, name: 'Witch Hats', color: '#00ff00', rarity: 'uncommon', image: '/asset/Gifts/400S_Witch Hats.png' },
  { id: 3, name: 'Diamond Rings', color: '#0099ff', rarity: 'rare', image: '/asset/Gifts/1200S_Diamond Rings.png' },
  { id: 4, name: 'Easter Eggs', color: '#ff00ff', rarity: 'epic', image: '/asset/Gifts/400S_Easter Eggs.png' },
  { id: 5, name: 'Victory Medals', color: '#ffaa00', rarity: 'legendary', image: '/asset/Gifts/600S_Victory Medals.png' },
  { id: 6, name: 'Toy Bears', color: '#888888', rarity: 'common', image: '/asset/Gifts/4799S_Toy Bears.png' },
  { id: 7, name: 'Top Hats', color: '#00ff00', rarity: 'uncommon', image: '/asset/Gifts/450S_Top Hats.png' },
  { id: 8, name: 'Swiss Watches', color: '#0099ff', rarity: 'rare', image: '/asset/Gifts/500S_Swiss Watches.png' },
];

// Triple the ribbon for seamless infinite loop
const TRIPLE_LOOT = [...LOOT_ITEMS, ...LOOT_ITEMS, ...LOOT_ITEMS];

const ITEM_WIDTH = 120;
const CONTAINER_WIDTH = ITEM_WIDTH * 5; // Show 5 items at a time
const MIDDLE_START = LOOT_ITEMS.length; // Start of middle copy

// easeOutCirc function: circular deceleration
const easeOutCirc = (x) => {
  return Math.sqrt(1 - Math.pow(x - 1, 2));
};

export default function SpinModal({ caseItem, onSpinComplete, onClose, isSpinning }) {
  const [hasSpun, setHasSpun] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const controls = useAnimation();
  const ribbonRef = useRef(null);

  useEffect(() => {
    if (isSpinning && !hasSpun) {
      // "Truth First" logic: Determine winning item BEFORE animation
      // In a real app, this should come from backend
      const items = caseItem?.items || LOOT_ITEMS;
      const winIndex = Math.floor(Math.random() * items.length);
      const wonItem = items[winIndex];

      // Calculate target position in the MIDDLE copy of the tripled ribbon
      const targetIndex = MIDDLE_START + winIndex;

      // Calculate the x offset to center the winning item under the pointer
      const itemCenterPos = targetIndex * ITEM_WIDTH + ITEM_WIDTH / 2;
      const containerCenter = CONTAINER_WIDTH / 2;
      const targetX = -(itemCenterPos - containerCenter);

      // Start position - far to the right for a long spin
      const startX = containerCenter + 3000;

      // Set initial position
      controls.set({ x: startX });

      // Animate with easeOutCirc
      const timer = setTimeout(() => {
        controls.start({
          x: targetX,
          transition: {
            duration: 6, // Slightly longer for more dramatic slowdown
            ease: (t) => easeOutCirc(t),
          }
        }).then(() => {
          setSelectedItem(wonItem);
          setHasSpun(true);
          onSpinComplete(wonItem);
        });
      }, 100);

      return () => clearTimeout(timer);
    }
  }, [isSpinning, hasSpun, caseItem]);

  // Reset when modal closes
  useEffect(() => {
    if (!isSpinning) {
      setHasSpun(false);
      setSelectedItem(null);
    }
  }, [isSpinning]);

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-50 flex items-center justify-center"
    >
      {/* Backdrop */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        onClick={!isSpinning && hasSpun ? onClose : undefined}
        className="absolute inset-0 bg-black/80 backdrop-blur-sm"
      />

      {/* Modal Content */}
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="relative z-10 w-full max-w-lg mx-4"
      >
        <div className="glass-panel p-6 space-y-6">
          {/* Header */}
          <div className="text-center">
            <h2 className="text-2xl font-black text-white mb-1">{caseItem.name}</h2>
            <p className="text-white/50 text-sm">{isSpinning && !hasSpun ? 'Spinning...' : 'Opening Complete!'}</p>
          </div>

          {/* Roulette Container */}
          <div className="relative">
            {/* Center Pointer - Top Triangle */}
            <div className="absolute left-1/2 top-0 transform -translate-x-1/2 z-30">
              <div className="w-0 h-0 border-l-4 border-r-4 border-t-8 border-l-transparent border-r-transparent border-t-white drop-shadow-glow" />
            </div>

            {/* Center Line */}
            <div className="absolute left-1/2 top-8 bottom-0 transform -translate-x-1/2 w-0.5 bg-white/40 z-20 pointer-events-none" />

            {/* Ribbon Viewport */}
            <div className="overflow-hidden rounded-2xl bg-white/[0.02] border border-white/10 backdrop-blur-xl p-4">
              <motion.div
                ref={ribbonRef}
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
                    <img
                      src={normalizeGiftImage(item.image)}
                      alt={item.name}
                      className="w-14 h-14 object-contain mb-1"
                      onError={useDefaultGiftImage}
                    />
                    <span className="text-white/70 text-[10px] text-center font-semibold uppercase">{item.rarity}</span>
                  </div>
                ))}
              </motion.div>
            </div>
          </div>

          {/* Win Result */}
          <AnimatePresence>
            {hasSpun && selectedItem && (
              <motion.div
                initial={{ opacity: 0, scale: 0.8, y: 20 }}
                animate={{ opacity: 1, scale: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.8 }}
                className="text-center p-4 rounded-xl border"
                style={{
                  borderColor: selectedItem.color + '30',
                  backgroundColor: selectedItem.color + '10',
                }}
              >
                <p className="text-white/50 text-xs mb-2 uppercase tracking-wider">You Won!</p>
                <img
                  src={normalizeGiftImage(selectedItem.image)}
                  alt={selectedItem.name}
                  className="h-24 w-24 object-contain mx-auto mb-3"
                  onError={useDefaultGiftImage}
                  style={{
                    filter: `drop-shadow(0 0 20px ${selectedItem.color}80)`,
                  }}
                />
                <p
                  className="text-white font-black text-2xl mb-2"
                  style={{ color: selectedItem.color }}
                >
                  {selectedItem.name}
                </p>
                <span
                  className="inline-block px-4 py-1.5 rounded-lg text-xs font-bold uppercase tracking-wider"
                  style={{
                    backgroundColor: selectedItem.color + '20',
                    color: selectedItem.color,
                    border: `1px solid ${selectedItem.color}40`,
                  }}
                >
                  {selectedItem.rarity}
                </span>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Actions */}
          <div className="flex gap-3">
            {!isSpinning && hasSpun && (
              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  onClose();
                  if (window.Telegram?.WebApp?.HapticFeedback) {
                    window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy');
                  }
                }}
                className="flex-1 py-3 rounded-xl bg-white/10 border border-white/20 text-white font-bold hover:bg-white/15 transition-colors"
              >
                Claim
              </motion.button>
            )}
            {isSpinning && !hasSpun && (
              <div className="w-full text-center py-3">
                <div className="inline-flex items-center gap-2 text-white/50">
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full"
                  />
                  <span className="text-sm">Spinning...</span>
                </div>
              </div>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
