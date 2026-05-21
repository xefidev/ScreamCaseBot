import React from 'react';
import { motion } from 'framer-motion';
import { DEFAULT_GIFT_IMAGE, getDynamicGiftImage } from '../giftUtils';

const PAGE_BG = '#22242a';

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
    triggerHaptic();
    if (!setInventory || !setBalance) return;
    setInventory((prev) => prev.filter((currentItem) => currentItem.id !== item.id));
    setBalance((prev) => prev + (Number(item.price || item.cost) || 0));
    triggerHaptic('success');
  };

  return (
    <div className="h-full overflow-y-auto p-6 pb-24" style={{ backgroundColor: PAGE_BG }}>
      <div className="mb-8">
        <h2 className="text-3xl font-black uppercase tracking-widest text-white text-glow">Профиль</h2>
      </div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }} className="glass-panel relative mb-8 overflow-hidden p-8 bg-[#1a1b1f] border-white/10">
        <div className="relative z-10 flex items-center gap-6">
          <div className="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-white/5 shadow-2xl">
            {user?.photo_url ? (
              <img src={user.photo_url} alt="Avatar" className="h-full w-full object-cover" onError={(e) => { e.currentTarget.style.display='none'; }} />
            ) : (
              <span className="text-4xl font-black text-white/20">{user?.first_name?.charAt(0) || '?'}</span>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-3xl font-black uppercase leading-tight tracking-tight text-white">{user?.first_name || 'Игрок'}</h3>
            <div className="mt-2 flex items-center gap-1.5 px-3 py-1 rounded-lg bg-yellow-500/10 border border-yellow-500/20 w-fit">
               <span className="text-sm font-black text-yellow-500">{formatValue(balance)}</span>
               <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} />
            </div>
            <p className="mt-2 text-[10px] text-white/20 font-black uppercase tracking-widest">ID: {user?.id || '0'}</p>
          </div>
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.1 }} className="glass-panel p-8 bg-[#1a1b1f] border-white/10">
        <h4 className="mb-6 text-lg font-black uppercase tracking-widest text-white/40">Инвентарь ({inventory?.length || 0})</h4>
        {!inventory || inventory.length === 0 ? (
          <div className="py-16 text-center border-2 border-dashed border-white/5 rounded-3xl"><p className="text-xs font-black uppercase tracking-[0.2em] text-white/10">Пусто</p></div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {inventory.map((item) => (
              <motion.div key={item.id} initial={{ opacity: 0, scale: 0.94 }} animate={{ opacity: 1, scale: 1 }} className="flex flex-col items-center justify-between rounded-3xl border border-white/5 bg-white/[0.02] p-5 shadow-xl group">
                <img src={getDynamicGiftImage(item)} alt="Gift" className="mb-4 h-24 w-24 object-contain transition-transform group-hover:scale-110" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} />
                <p className="mb-4 w-full truncate text-center text-[10px] font-black uppercase tracking-tight text-white/60">{item.name || 'Gift'}</p>
                <motion.button whileTap={{ scale: 0.95 }} onClick={() => handleSell(item)} className="w-full rounded-xl border border-red-500/30 bg-red-500/10 py-2.5 text-[9px] font-black uppercase tracking-widest text-red-400">Продать: {Number(item.price || item.cost) || 0}</motion.button>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
