import React, { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CasePreview from './CasePreview';
import { getGiftsInRange } from '../giftData';
import { DEFAULT_GIFT_IMAGE, getDynamicGiftImage } from '../giftUtils';
import { fetchCases } from '../api';

const CASES_DATA = [
  { id: 1, name: 'Promo Case', price: 0, glowColor: '#3b82f6', badge: 'Бесплатно', minPrice: 1, maxPrice: 600, stock: 100, image: '/asset/Gifts/50S_GiftBox_Original_GiftBox.webp' },
  { id: 2, name: 'Daily Case', price: 1, glowColor: '#dc2626', badge: '1 звезда', minPrice: 1, maxPrice: 500, stock: 50, image: '/asset/Gifts/100S_Red_Star_Original_Red_Star.webp' },
  { id: 3, name: 'Snoop Case', price: 667, glowColor: '#22c55e', badge: 'Премиум', minPrice: 15, maxPrice: 2000, stock: 100, image: '/asset/Gifts/1188S_Snoop_Cigar_Original_Snoop_Cigar.webp' },
  { id: 4, name: "Lover's Case", price: 599, glowColor: '#ec4899', badge: 'Романтик', minPrice: 15, maxPrice: 1500, stock: 80, image: '/asset/Gifts/2S_I_love_you_Original_I_love_you.webp' },
  { id: 5, name: 'Hobo Case', price: 199, glowColor: '#78350f', badge: 'Бюджет', minPrice: 15, maxPrice: 400, stock: 200, image: '/asset/Gifts/370S_Instant_Ramen_Original_Instant_Ramen.webp' },
  { id: 6, name: 'Risky Box', price: 50, glowColor: '#eab308', badge: 'Рискованный', minPrice: 15, maxPrice: 250, stock: 150, image: '/asset/Gifts/800S_Evil_Eye_Original_Evil_Eye.webp' },
  { id: 7, name: 'Scam Box', price: 111, glowColor: '#4b5563', badge: 'Мистический', minPrice: 15, maxPrice: 300, stock: 300, image: '/asset/Gifts/850S_Trojan_Horse_Original_Trojan_Horse.webp' },
  { id: 8, name: 'Ebati Case', price: 444, glowColor: '#3b82f6', badge: 'Элитный', minPrice: 15, maxPrice: 1000, stock: 120, image: '/asset/Gifts/7942S_Diamond_Ring_Original_Diamond_Ring.webp' },
  { id: 9, name: 'Pussy Case', price: 222, glowColor: '#ec4899', badge: '💝 Подарки', minPrice: 15, maxPrice: 500, stock: 100, image: '/asset/Gifts/3579S_Pink_Bear_Original_Pink_Bear.webp' },
  { id: 10, name: 'Skolnik Case', price: 250, glowColor: '#f97316', badge: 'Яркий', minPrice: 15, maxPrice: 600, stock: 150, image: '/asset/Gifts/2500S_Pen_Original_Pen.webp' },
];

const getRandomFlashDiscount = () => {
  const discountableCases = CASES_DATA.filter(c => c.id !== 1 && c.id !== 2);
  const discountCaseId = discountableCases[Math.floor(Math.random() * discountableCases.length)].id;
  return discountCaseId;
};

const CaseCard = ({ caseItem, onClick, isFlashDiscount }) => {
  const triggerHaptic = () => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      window.Telegram.WebApp.HapticFeedback.impactOccurred('heavy');
    }
  };

  const discountedPrice = useMemo(() => {
    if (!isFlashDiscount) return caseItem?.price || 0;
    return Math.floor((caseItem?.price || 0) * 0.85);
  }, [caseItem?.price, isFlashDiscount]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      className="group relative cursor-pointer"
      onClick={() => {
        onClick();
        triggerHaptic();
      }}
    >
      <div className="glass-panel p-4 h-full flex flex-col gap-3 overflow-hidden relative">
        <div
          className="absolute inset-0 rounded-3xl opacity-30 pointer-events-none"
          style={{
            background: `radial-gradient(ellipse at 50% 40%, ${caseItem?.glowColor || '#ffffff'}25, transparent 70%)`,
          }}
        />

        <div className="relative flex-1 flex items-center justify-center py-2 min-h-[120px] w-full overflow-visible">
          <img
            src={caseItem?.image || '/asset/Case/CaseBlack.png'}
            alt={caseItem?.name || 'Case'}
            className="w-24 h-24 object-contain relative z-10"
            onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }}
            loading="lazy"
            style={{
              filter: `drop-shadow(0 0 20px ${caseItem?.glowColor || '#ffffff'}80)`,
            }}
          />
        </div>

        <div className="flex items-center justify-between gap-2 relative z-10">
          <div className="flex-1 min-w-0">
            <h3 className="text-white font-bold text-xs truncate uppercase tracking-tighter">{caseItem?.name || 'Case'}</h3>
            <p className="text-white/40 text-[9px] uppercase font-black tracking-widest">
                {caseItem.total_limit === -1 ? 'Бесконечно' : `Осталось: ${caseItem?.remaining_limit ?? '?'} / ${caseItem?.total_limit ?? '?'}`}
            </p>
          </div>
          {isFlashDiscount ? (
            <span className="px-1.5 py-0.5 rounded-lg text-[10px] font-black bg-red-500/20 border border-red-500/40 text-red-400 whitespace-nowrap font-rounded animate-pulse">
              🔥 -15%
            </span>
          ) : (
            <span className="px-1.5 py-0.5 rounded-lg text-[10px] font-black bg-white/5 border border-white/10 text-white/40 whitespace-nowrap uppercase tracking-tighter">
                {caseItem?.badge || 'N/A'}
            </span>
          )}
        </div>

        <motion.button
          whileHover={{ backgroundColor: 'rgba(255, 255, 255, 0.15)' }}
          whileTap={{ scale: 0.95 }}
          onClick={(e) => {
            e.stopPropagation();
            onClick();
            triggerHaptic();
          }}
          className="w-full py-3 rounded-2xl border border-white/10 bg-white/5 text-white font-black text-xs transition-all hover:border-white/20 flex items-center justify-center gap-2 font-rounded uppercase tracking-widest"
        >
          {caseItem?.price === 0 ? 'БЕСПЛАТНО' : (
            <div className="flex items-center justify-center gap-2">
              {isFlashDiscount && (caseItem?.price || 0) > 1 && (
                <span className="line-through text-white/20 text-[10px]">{caseItem?.price}</span>
              )}
              <span className={`flex items-center gap-1 ${isFlashDiscount ? 'text-red-400' : 'text-white'}`}>
                {isFlashDiscount && (caseItem?.price || 0) > 1 ? discountedPrice : (caseItem?.price || 0)}
                <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
              </span>
            </div>
          )}
        </motion.button>
      </div>
    </motion.div>
  );
};

export default function CasesGrid({ user, onBuy, onWin, balance, setBalance, setSpent, promoOpened, setPromoOpened, onTopUpRequest }) {
  const [selectedCase, setSelectedCase] = useState(null);
  const [view, setView] = useState('grid');
  const [flashDiscountCaseId, setFlashDiscountCaseId] = useState(() => getRandomFlashDiscount());
  const [dbCases, setDbCases] = useState([]);

  useEffect(() => {
    const loadDbCases = async () => {
      const casesFromApi = await fetchCases();
      setDbCases(casesFromApi);
    };
    loadDbCases();
  }, []);

  const mergedCases = useMemo(() => {
    return CASES_DATA.map(localCase => {
      const dbMatch = dbCases.find(db => db.id === localCase.id);
      return {
        ...localCase,
        total_limit: dbMatch?.total_limit ?? -1,
        remaining_limit: dbMatch?.remaining_limit ?? -1,
      };
    });
  }, [dbCases]);

  const sortedCases = useMemo(() => [...mergedCases].sort((a, b) => a.price - b.price), [mergedCases]);

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
            className="h-full overflow-y-auto"
          >
            <div className="grid grid-cols-2 gap-3 p-4 pb-24">
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
              user={user}
              caseItem={selectedCase}
              onClose={handleClosePreview}
              onWin={handleWin}
              balance={balance}
              setBalance={setBalance}
              setSpent={setSpent}
              flashDiscount={getCaseFlashDiscount(selectedCase.id)}
              promoOpened={promoOpened}
              setPromoOpened={setPromoOpened}
              onTopUpRequest={onTopUpRequest}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
