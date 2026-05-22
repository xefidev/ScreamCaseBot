import React, { useState, useEffect, useRef } from 'react';
import { motion, useAnimation, AnimatePresence } from 'framer-motion';
import { getDynamicGiftImage, DEFAULT_GIFT_IMAGE } from '../giftUtils';

const LOOT_ITEMS = [
  { id: 1, name: 'Xmas Stocking', color: '#ff0000', rarity: 'common', price: 325 },
  { id: 2, name: 'Witch Hat', color: '#00ff00', rarity: 'uncommon', price: 550 },
  { id: 3, name: 'Diamond Ring', color: '#0099ff', rarity: 'rare', price: 1200 },
  { id: 4, name: 'Easter Egg', color: '#ff00ff', rarity: 'epic', price: 420 },
  { id: 5, name: 'Victory Medal', color: '#ffaa00', rarity: 'legendary', price: 2300 },
  { id: 6, name: 'Toy Bear', color: '#888888', rarity: 'common', price: 50 },
  { id: 7, name: 'Top Hat', color: '#00ff00', rarity: 'uncommon', price: 450 },
  { id: 8, name: 'Swiss Watch', color: '#0099ff', rarity: 'rare', price: 5284 },
];

const TRIPLE_LOOT = [...LOOT_ITEMS, ...LOOT_ITEMS, ...LOOT_ITEMS];
const ITEM_WIDTH = 120;
const CONTAINER_WIDTH = ITEM_WIDTH * 5;
const MIDDLE_START = LOOT_ITEMS.length;

const easeOutCirc = (x) => Math.sqrt(1 - Math.pow(x - 1, 2));

export default function SpinModal({ caseItem, onSpinComplete, onClose, isSpinning }) {
  const [hasSpun, setHasSpun] = useState(false);
  const [selectedItem, setSelectedItem] = useState(null);
  const controls = useAnimation();
  const ribbonRef = useRef(null);

  useEffect(() => {
    if (isSpinning && !hasSpun && caseItem) {
      const items = caseItem?.items || LOOT_ITEMS;
      const winIndex = Math.floor(Math.random() * items.length);
      const wonItem = items[winIndex];
      const targetIndex = MIDDLE_START + winIndex;
      const itemCenterPos = targetIndex * ITEM_WIDTH + ITEM_WIDTH / 2;
      const containerCenter = CONTAINER_WIDTH / 2;
      const targetX = -(itemCenterPos - containerCenter);
      const startX = containerCenter + 3000;

      controls.set({ x: startX });
      const timer = setTimeout(() => {
        controls.start({
          x: targetX,
          transition: { duration: 6, ease: (t) => easeOutCirc(t) }
        }).then(() => {
          setSelectedItem(wonItem);
          setHasSpun(true);
          onSpinComplete(wonItem);
        });
      }, 100);
      return () => clearTimeout(timer);
    }
  }, [isSpinning, hasSpun, caseItem, controls, onSpinComplete]);

  useEffect(() => {
    if (!isSpinning) { setHasSpun(false); setSelectedItem(null); }
  }, [isSpinning]);

  if (!caseItem && isSpinning) {
    return (
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm">
        <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} className="w-12 h-12 border-4 border-white/20 border-t-white rounded-full" />
      </div>
    );
  }

  return (
    <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-center justify-center">
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} onClick={!isSpinning && hasSpun ? onClose : undefined} className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
      <motion.div initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} className="relative z-10 w-full max-w-lg mx-4">
        <div className="glass-panel p-6 space-y-6">
          <div className="text-center">
            <h2 className="text-2xl font-black text-white mb-1 uppercase tracking-tight text-glow">{caseItem?.name || 'Opening Case...'}</h2>
            <p className="text-white/50 text-[10px] font-black uppercase tracking-widest">{isSpinning && !hasSpun ? 'Крутим рулетку...' : 'Готово!'}</p>
          </div>
          <div className="relative">
            <div className="absolute left-1/2 top-0 transform -translate-x-1/2 z-30"><div className="w-0 h-0 border-l-4 border-r-4 border-t-8 border-l-transparent border-r-transparent border-t-white" /></div>
            <div className="absolute left-1/2 top-8 bottom-0 transform -translate-x-1/2 w-0.5 bg-white/40 z-20 pointer-events-none" />
            <div className="overflow-hidden rounded-2xl bg-white/[0.02] border border-white/10 backdrop-blur-xl p-4">
              <motion.div ref={ribbonRef} className="flex gap-3" animate={controls}>
                {TRIPLE_LOOT.map((item, idx) => (
                  <div key={idx} className="flex-shrink-0 w-28 h-28 rounded-xl border-2 flex flex-col items-center justify-center p-2" style={{ borderColor: (item.color || '#ffffff') + '40', backgroundColor: (item.color || '#ffffff') + '10' }}>
                    <img src={getDynamicGiftImage(item)} alt={item.name} className="w-14 h-14 object-contain mb-1" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} loading="lazy" />
                    <span className="text-white/70 text-[10px] text-center font-semibold uppercase">{item.rarity}</span>
                  </div>
                ))}
              </motion.div>
            </div>
          </div>
          <AnimatePresence>
            {hasSpun && selectedItem && (
              <motion.div initial={{ opacity: 0, scale: 0.8, y: 20 }} animate={{ opacity: 1, scale: 1, y: 0 }} exit={{ opacity: 0, scale: 0.8 }} className="text-center p-6 rounded-3xl border relative overflow-hidden bg-white/[0.02]" style={{ borderColor: (selectedItem.color || '#ffffff') + '30' }}>
                <p className="text-white/50 text-[10px] mb-3 uppercase tracking-[0.3em] font-black">Вы выиграли!</p>
                <motion.img animate={{ y: [0, -8, 0] }} transition={{ duration: 2, repeat: Infinity, ease: "easeInOut" }} src={getDynamicGiftImage(selectedItem)} alt={selectedItem.name} className="h-28 w-28 object-contain mx-auto mb-4 relative z-10" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} style={{ filter: `drop-shadow(0 0 25px ${(selectedItem.color || '#ffffff')}80)` }} />
                <p className="text-white font-black text-2xl mb-2 font-rounded" style={{ color: selectedItem.color }}>{selectedItem.name}</p>
                <span className="inline-block px-4 py-1.5 rounded-xl text-[10px] font-black uppercase tracking-widest" style={{ backgroundColor: (selectedItem.color || '#ffffff') + '20', color: selectedItem.color, border: `1px solid ${(selectedItem.color || '#ffffff')}40` }}>{selectedItem.rarity}</span>
              </motion.div>
            )}
          </AnimatePresence>
          <div className="flex gap-3">
            {!isSpinning && hasSpun && (
              <motion.button whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }} onClick={onClose} className="flex-1 py-4 rounded-2xl bg-white/10 border border-white/20 text-white font-black uppercase tracking-widest hover:bg-white/15 transition-all shadow-xl">ЗАБРАТЬ</motion.button>
            )}
            {isSpinning && !hasSpun && (
              <div className="w-full text-center py-4"><div className="inline-flex items-center gap-3 text-white/40"><motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} className="w-5 h-5 border-2 border-white/20 border-t-white rounded-full" /><span className="text-xs font-black uppercase tracking-widest">Открываем...</span></div></div>
            )}
          </div>
        </div>
      </motion.div>
    </motion.div>
  );
}
