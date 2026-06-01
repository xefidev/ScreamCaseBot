import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { DEFAULT_GIFT_IMAGE, getDynamicGiftImage } from '../giftUtils';
import { redeemPromo } from '../api';

const PAGE_BG = '#1a1b1e';

const formatValue = (value) => {
  if (value === undefined || value === null) return '0';
  if (value >= 1000) return `${(value / 1000).toFixed(1).replace('.0', '')}k`;
  return value.toString();
};

export default function ProfilePage({
  isPage,
  inventory = [],
  setInventory,
  balance,
  setBalance
}) {
  const [user, setUser] = React.useState(null);
  const [sellingIds, setSellingIds] = useState(new Set());
  const [isSellingAll, setIsSellingAll] = useState(false);
  const [promoCode, setPromoCode] = useState('');
  const [promoLoading, setPromoLoading] = useState(false);
  const [promoMessage, setPromoMessage] = useState(null); // { type: 'success'|'error', text }

  React.useEffect(() => {
    const userData = window.Telegram?.WebApp?.initDataUnsafe?.user;
    if (userData) setUser(userData);
  }, []);

  const triggerHaptic = (type = 'heavy') => {
    const haptic = window.Telegram?.WebApp?.HapticFeedback;
    if (!haptic) return;
    if (type === 'success') haptic.notificationOccurred('success');
    else haptic.impactOccurred(type);
  };

  const handleSell = (item) => {
    if (sellingIds.has(item.id)) return;
    
    triggerHaptic();
    if (!setInventory || !setBalance || !item?.id) return;
    
    setSellingIds(prev => new Set(prev).add(item.id));
    
    setInventory((prev) => {
      const itemExists = prev.some(i => i.id === item.id);
      if (!itemExists) return prev;
      return prev.filter((currentItem) => currentItem.id !== item.id);
    });
    
    const sellPrice = Number(item.price || item.cost) || 0;
    if (sellPrice > 0) {
      setBalance((prev) => prev + sellPrice);
      triggerHaptic('success');
    }
  };

  const handleSellAll = () => {
    if (inventory.length === 0 || isSellingAll) return;
    
    triggerHaptic('heavy');
    setIsSellingAll(true);
    
    const totalValue = inventory.reduce((sum, item) => sum + (Number(item.price || item.cost) || 0), 0);
    
    setInventory([]);
    setBalance(prev => prev + totalValue);
    triggerHaptic('success');
    
    setTimeout(() => setIsSellingAll(false), 1000);
  };

  const handleRedeemPromo = async () => {
    const code = promoCode.trim().toUpperCase();
    if (!code) {
      setPromoMessage({ type: 'error', text: 'Введите промокод' });
      return;
    }
    const uid = window.Telegram?.WebApp?.initDataUnsafe?.user?.id;
    if (!uid) {
      setPromoMessage({ type: 'error', text: 'Не удалось определить пользователя' });
      return;
    }
    setPromoLoading(true);
    setPromoMessage(null);
    triggerHaptic('medium');
    try {
      const res = await redeemPromo(uid, code);
      if (res?.success) {
        setBalance(prev => (Number(prev) || 0) + Number(res.reward_stars || 0));
        setPromoMessage({ type: 'success', text: `+${res.reward_stars} ⭐ зачислено` });
        setPromoCode('');
        triggerHaptic('success');
      }
    } catch (err) {
      setPromoMessage({ type: 'error', text: err?.message || 'Ошибка активации' });
    } finally {
      setPromoLoading(false);
      setTimeout(() => setPromoMessage(null), 4000);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4 pb-24" style={{ backgroundColor: PAGE_BG }}>
      <div className="mb-6 flex justify-between items-center">
        <h2 className="text-2xl font-black uppercase tracking-widest text-white">Профиль</h2>
        {inventory.length > 0 && (
          <button 
            onClick={handleSellAll}
            disabled={isSellingAll}
            className="px-4 py-2 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-[10px] font-black uppercase tracking-widest disabled:opacity-50"
          >
            {isSellingAll ? 'ПРОДАЖА...' : 'ПРОДАТЬ ВСЕ'}
          </button>
        )}
      </div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="glass-panel relative mb-6 overflow-hidden p-6 bg-white/[0.02] border-white/10">
        <div className="relative z-10 flex items-center gap-4">
          <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-white/5 shadow-2xl">
            {user?.photo_url ? (
              <img src={user.photo_url} alt="Avatar" className="h-full w-full object-cover" onError={(e) => { e.currentTarget.style.display='none'; }} />
            ) : (
              <span className="text-3xl font-black text-white/20">{user?.first_name?.charAt(0) || '?'}</span>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-xl font-black uppercase leading-tight tracking-tight text-white">{user?.first_name || 'Игрок'}</h3>
            <div className="mt-2 flex items-center gap-1.5 px-3 py-1 rounded-lg bg-yellow-500/10 border border-yellow-500/20 w-fit">
               <span className="text-sm font-black text-yellow-500">{formatValue(balance)}</span>
               <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} />
            </div>
            <p className="mt-2 text-[8px] text-white/20 font-black uppercase tracking-widest">ID: {user?.id || '0'}</p>
          </div>
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.05 }} className="glass-panel mb-6 p-5 bg-white/[0.02] border-white/10">
        <h4 className="mb-3 text-xs font-black uppercase tracking-widest text-white/40">🎟 Промокод</h4>
        <div className="flex gap-2">
          <input
            type="text"
            value={promoCode}
            onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
            onKeyDown={(e) => { if (e.key === 'Enter') handleRedeemPromo(); }}
            placeholder="ВВЕДИТЕ КОД"
            maxLength={32}
            disabled={promoLoading}
            className="flex-1 rounded-xl bg-white/5 border border-white/10 px-4 py-3 text-sm font-black uppercase tracking-widest text-white placeholder-white/20 focus:outline-none focus:border-yellow-500/40 disabled:opacity-50"
          />
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={handleRedeemPromo}
            disabled={promoLoading || !promoCode.trim()}
            className="px-5 py-3 rounded-xl bg-yellow-500/15 border border-yellow-500/30 text-yellow-400 text-[10px] font-black uppercase tracking-widest disabled:opacity-40"
          >
            {promoLoading ? '...' : 'АКТИВИРОВАТЬ'}
          </motion.button>
        </div>
        {promoMessage && (
          <motion.div
            initial={{ opacity: 0, y: -4 }}
            animate={{ opacity: 1, y: 0 }}
            className={`mt-3 rounded-lg px-3 py-2 text-[10px] font-black uppercase tracking-widest ${
              promoMessage.type === 'success'
                ? 'bg-green-500/10 border border-green-500/30 text-green-400'
                : 'bg-red-500/10 border border-red-500/30 text-red-400'
            }`}
          >
            {promoMessage.text}
          </motion.div>
        )}
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.1 }} className="glass-panel p-6 bg-white/[0.02] border-white/10">
        <h4 className="mb-4 text-xs font-black uppercase tracking-widest text-white/40">Инвентарь ({inventory?.length || 0})</h4>
        {!inventory || inventory.length === 0 ? (
          <div className="py-12 text-center border border-dashed border-white/5 rounded-3xl"><p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/10">Пусто</p></div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {inventory.map((item) => (
              <motion.div key={item.id} initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center justify-between rounded-3xl border border-white/5 bg-white/[0.02] p-4 shadow-xl group">
                <img src={getDynamicGiftImage(item)} alt="Gift" className="mb-3 h-20 w-20 object-contain transition-transform group-hover:scale-110" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} loading="lazy" />
                <p className="mb-3 w-full truncate text-center text-[9px] font-black uppercase tracking-tight text-white/60">{item.name || 'Gift'}</p>
                <motion.button 
                  whileTap={{ scale: 0.95 }} 
                  onClick={() => handleSell(item)} 
                  disabled={sellingIds.has(item.id)}
                  className="w-full rounded-xl border border-red-500/30 bg-red-500/10 py-2 text-[8px] font-black uppercase tracking-widest text-red-400 disabled:opacity-50"
                >
                  {sellingIds.has(item.id) ? 'ПРОДАНО' : `Продать: ${Number(item.price || item.cost) || 0}`}
                </motion.button>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
