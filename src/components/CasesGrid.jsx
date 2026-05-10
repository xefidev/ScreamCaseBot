import React, { useState, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CasePreview from './CasePreview';
import { ALL_GIFTS, getGiftsInRange, getTopGift } from '../giftData';

const CASES_DATA = [
  { id: 1, name: 'Promo Case', price: 0, glowColor: '#ffffff', badge: 'Free', minPrice: 0, maxPrice: 667, stock: 999 },
  { id: 2, name: 'Daily Case', price: 1, glowColor: '#dc2626', badge: 'Free', minPrice: 0, maxPrice: 100, stock: 50 },
  { id: 3, name: 'Snoop Case', price: 667, glowColor: '#22c55e', badge: 'Random', minPrice: 100, maxPrice: 667, stock: 100 },
  { id: 4, name: "Lover's Case", price: 599, glowColor: '#ec4899', badge: 'Random', minPrice: 200, maxPrice: 599, stock: 80 },
  { id: 5, name: 'Hobo Case', price: 199, glowColor: '#78350f', badge: 'Any', minPrice: 0, maxPrice: 199, stock: 200 },
  { id: 6, name: 'Risky Box', price: 50, glowColor: '#eab308', badge: 'Extreme', minPrice: 0, maxPrice: 50, stock: 150 },
  { id: 7, name: 'Scam Box', price: 111, glowColor: '#4b5563', badge: 'Hidden', minPrice: 0, maxPrice: 599, stock: 300 },
  { id: 8, name: 'Ebati Case', price: 444, glowColor: '#3b82f6', badge: 'FN/MW', minPrice: 100, maxPrice: 444, stock: 120 },
  { id: 9, name: 'Pussy Case', price: 222, glowColor: '#ec4899', badge: '💝 Gifts', minPrice: 50, maxPrice: 222, stock: 100 },
  { id: 10, name: 'Skolnik Case', price: 250, glowColor: '#f97316', badge: 'BS', minPrice: 100, maxPrice: 250, stock: 150 },
];

const getRandomFlashDiscount = () => {
  const discountCaseId = CASES_DATA[Math.floor(Math.random() * CASES_DATA.length)].id;
  return discountCaseId;
};

const CaseCard = ({ caseItem, onClick, isFlashDiscount }) => {
  const dropItems = useMemo(() =>
    getGiftsInRange(caseItem.minPrice, caseItem.maxPrice),
    [caseItem.minPrice, caseItem.maxPrice]
  );

  const topGift = useMemo(() => getTopGift(dropItems), [dropItems]);

  const previewGift = useMemo(() => {
    if (!dropItems || dropItems.length === 0) return null;
    if (dropItems.length === 1) return dropItems[0];
    const shuffled = [...dropItems].sort(() => Math.random() - 0.5);
    return shuffled.slice(0, 2);
  }, [dropItems]);

  const discountedPrice = useMemo(() => {
    if (!isFlashDiscount) return caseItem.price;
    return Math.floor(caseItem.price * 0.85);
  }, [caseItem.price, isFlashDiscount]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="group relative cursor-pointer"
      onClick={onClick}
    >
      <div className="glass-panel p-4 h-full flex flex-col gap-3 overflow-hidden relative">
        {/* Radial Glow Behind Gift */}
        <div
          className="absolute inset-0 rounded-3xl opacity-30 pointer-events-none"
          style={{
            background: `radial-gradient(ellipse at 50% 40%, ${caseItem.glowColor}25, transparent 70%)`,
          }}
        />

        {/* Unified Composition: Gift + Case Together */}
        <div className="relative flex-1 flex items-center justify-center py-2 min-h-[120px] w-full overflow-visible">
          {/* Case Image - z-10 so gifts appear above */}
          <img
            src={caseItem.name === 'Pussy Case' ? '/asset/Gifts/50S_GiftBox.png' : '/asset/Case/CaseBlack.png'}
            alt={caseItem.name}
            className={caseItem.name === 'Pussy Case' ? "w-24 h-24 object-contain relative z-10" : "w-full h-28 object-contain relative z-10"}
            style={{
              filter: `drop-shadow(0 0 20px ${caseItem.glowColor}80)`,
            }}
          />

          {/* Floating Gifts inside/above case */}
          {previewGift && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              {Array.isArray(previewGift) ? (
                previewGift.map((gift, idx) => (
                  <motion.div
                    key={gift.price + idx}
                    animate={{
                      y: [0, -12, 0],
                      rotate: [0, 4, -4, 0],
                      scale: [1, 1.05, 1],
                    }}
                    transition={{
                      duration: 3 + idx * 0.4,
                      repeat: Infinity,
                      ease: "easeInOut",
                      delay: idx * 0.6,
                    }}
                    className="absolute"
                    style={{
                      left: idx === 0 ? 'calc(50% - 2.5rem)' : 'calc(50% + 2.5rem)',
                      top: 'calc(50% - 3rem)',
                      transform: 'translate(-50%, -50%)',
                    }}
                  >
                    <img
                      src={gift.image}
                      alt={gift.name}
                      className="w-10 h-10 sm:w-12 sm:h-12 object-contain"
                      loading="lazy"
                      style={{
                        filter: `drop-shadow(0 0 8px ${caseItem.glowColor}70)`,
                      }}
                    />
                  </motion.div>
                ))
              ) : (
                <motion.div
                  animate={{
                    y: [0, -12, 0],
                    rotate: [0, 3, -3, 0],
                    scale: [1, 1.08, 1],
                  }}
                  transition={{ duration: 3, repeat: Infinity, ease: "easeInOut" }}
                  className="absolute"
                  style={{
                    left: '50%',
                    top: 'calc(50% - 3rem)',
                    transform: 'translate(-50%, -50%)',
                  }}
                >
                  <img
                    src={previewGift.image}
                    alt={previewGift.name}
                    className="w-12 h-12 sm:w-14 sm:h-14 object-contain"
                    loading="lazy"
                    style={{
                      filter: `drop-shadow(0 0 10px ${caseItem.glowColor}70)`,
                    }}
                  />
                </motion.div>
              )}
            </div>
          )}
        </div>

        {/* Case Info */}
        <div className="flex items-center justify-between gap-2 relative z-10">
          <div className="flex-1 min-w-0">
            <h3 className="text-white font-bold text-xs truncate">{caseItem.name}</h3>
            <p className="text-white/40 text-[9px] uppercase font-bold">Stock: {caseItem.stock}</p>
          </div>
          <span className="px-1.5 py-0.5 rounded-lg text-[10px] font-semibold bg-white/10 border border-white/20 whitespace-nowrap">
            {caseItem.badge}
          </span>
          {isFlashDiscount && (
            <span className="px-1.5 py-0.5 rounded-lg text-[10px] font-semibold bg-red-500/20 border border-red-500/40 text-red-400 whitespace-nowrap font-rounded animate-pulse">
              🔥 -15%
            </span>
          )}
        </div>

        {/* Buy Button */}
        <motion.button
          whileHover={{ backgroundColor: 'rgba(255, 255, 255, 0.15)' }}
          whileTap={{ scale: 0.95 }}
          onClick={(e) => {
            e.stopPropagation();
            onClick();
          }}
          className="w-full py-3 rounded-2xl border border-white/20 bg-white/10 text-white font-black text-sm transition-all hover:border-white/30 flex items-center justify-center gap-2 font-rounded"
        >
          {caseItem.price === 0 ? 'ОТКРЫТЬ' : (
            <span className="flex items-center justify-center gap-2">
              {isFlashDiscount && caseItem.price > 1 && (
                <span className="line-through text-white/40 text-xs">ОТКРЫТЬ ЗА {caseItem.price}</span>
              )}
              <span className={isFlashDiscount ? 'text-red-400' : ''}>
                {isFlashDiscount && caseItem.price > 1 ? 'ОТКРЫТЬ ЗА ' : 'ОТКРЫТЬ ЗА '}{isFlashDiscount && caseItem.price > 1 ? discountedPrice : caseItem.price}
              </span>
              <img src="/asset/Icons/TelegramStar.png" className="h-6 w-6" alt="Stars" />
            </span>
          )}
        </motion.button>
      </div>
    </motion.div>
  );
};

export default function CasesGrid({ onBuy, onWin, balance, setBalance, setSpent }) {
  const [selectedCase, setSelectedCase] = useState(null);
  const [view, setView] = useState('grid');
  const [flashDiscountCaseId, setFlashDiscountCaseId] = useState(() => getRandomFlashDiscount());

  const sortedCases = useMemo(() => [...CASES_DATA].sort((a, b) => a.price - b.price), []);

  const handlePreview = (caseItem) => {
    setSelectedCase(caseItem);
    setView('preview');
  };

  const handleClosePreview = () => {
    setView('grid');
    setSelectedCase(null);
  };

  const handleWin = (item, caseItem) => {
    if (onWin) {
      onWin(item, caseItem);
    }
  };

  const getCaseFlashDiscount = (caseId) => {
    return flashDiscountCaseId === caseId ? 0.15 : null;
  };

  return (
    <div className="h-full overflow-hidden relative">
      <AnimatePresence mode="wait">
        {view === 'grid' && (
          <motion.div
            key="grid"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0, x: -100 }}
            className="h-full overflow-y-auto p-4"
          >
            <div className="grid grid-cols-2 gap-3">
              {sortedCases.map((caseItem, index) => (
                <motion.div
                  key={caseItem.id}
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: index * 0.05 }}
                >
                  <CaseCard
                    caseItem={caseItem}
                    onClick={() => handlePreview(caseItem)}
                    isFlashDiscount={flashDiscountCaseId === caseItem.id}
                  />
                </motion.div>
              ))}
            </div>
          </motion.div>
        )}

        {view === 'preview' && selectedCase && (
          <motion.div
            key="preview"
            initial={{ opacity: 0, x: 100 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: -100 }}
            className="h-full"
          >
            <CasePreview
              caseItem={selectedCase}
              onClose={handleClosePreview}
              onWin={handleWin}
              balance={balance}
              setBalance={setBalance}
              setSpent={setSpent}
              flashDiscount={getCaseFlashDiscount(selectedCase.id)}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
