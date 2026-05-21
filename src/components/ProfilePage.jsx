import React from 'react';
import { motion } from 'framer-motion';
import { DEFAULT_GIFT_IMAGE, useDefaultGiftImage, getDynamicGiftImage } from '../giftUtils';

const PAGE_BG = '#22242a';

const formatValue = (value) => {
  if (value === undefined || value === null) return '0';
  if (value >= 1000) return `${(value / 1000).toFixed(1).replace('.0', '')}k`;
  return value.toString();
};

export default function ProfilePage({
  onClose,
  isPage,
  inventory = [],
  setInventory,
  balance,
  setBalance,
  spent = 0,
  donor = 0
}) {
  const [user, setUser] = React.useState(null);

  React.useEffect(() => {
    const userData = window.Telegram?.WebApp?.initDataUnsafe?.user;
    if (userData) setUser(userData);
  }, []);

  const triggerHaptic = (type = 'heavy') => {
    const haptic = window.Telegram?.WebApp?.HapticFeedback;
    if (!haptic) return;

    if (type === 'success') {
      haptic.notificationOccurred('success');
      return;
    }

    haptic.impactOccurred(type);
  };

  const handleSell = (item) => {
    triggerHaptic();
    if (!setInventory || !setBalance) return;

    setInventory((prev) => prev.filter((currentItem) => currentItem.id !== item.id));
    setBalance((prev) => prev + (Number(item.price || item.cost) || 0));
    triggerHaptic('success');
  };

  return (
    <div
      className={`${isPage ? 'h-full overflow-y-auto p-6 pb-24' : 'min-h-screen w-full overflow-y-auto p-6'}`}
      style={{ backgroundColor: PAGE_BG }}
    >
      {!isPage && onClose && (
        <div className="mb-8 flex items-center justify-between">
          <h2 className="text-3xl font-black uppercase tracking-widest text-white">Профиль</h2>
          <button onClick={onClose} className="text-3xl text-white/50 transition-colors hover:text-white">
            x
          </button>
        </div>
      )}

      {isPage && (
        <div className="mb-8">
          <h2 className="text-3xl font-black uppercase tracking-widest text-white">Профиль</h2>
        </div>
      )}

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="glass-panel relative mb-8 overflow-hidden p-8"
        style={{ backgroundColor: 'rgba(34, 36, 42, 0.92)', borderColor: 'rgba(255, 255, 255, 0.1)' }}
      >
        <div className="relative z-10 mb-8 flex items-center gap-6">
          <div className="flex h-24 w-24 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/20 bg-white/5">
            {user?.photo_url ? (
              <img src={user.photo_url} alt="Avatar" className="h-full w-full object-cover" onError={(e) => { e.currentTarget.style.display='none'; }} />
            ) : (
              <span className="text-4xl font-black text-white/30">{user?.first_name?.charAt(0) || '?'}</span>
            )}
          </div>

          <div className="min-w-0 flex-1">
            <h3 className="truncate text-3xl font-black uppercase leading-tight tracking-tight text-white">
              {user?.first_name || 'Игрок'}
            </h3>
            <p className="mt-2 text-sm text-white/40">ID: {user?.id || '0'}</p>
          </div>
        </div>

        <div className="relative z-10 grid grid-cols-2 gap-4">
          <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
            <p className="mb-3 text-xs font-bold uppercase tracking-widest text-white/60">Донор</p>
            <div className="flex items-center gap-2">
              <span className="text-3xl font-black text-white">{formatValue(donor)}</span>
              <img src="/asset/Icons/TelegramStar.png" className="h-6 w-6" alt="Stars" />
            </div>
          </div>

          <div className="rounded-2xl border border-white/10 bg-white/5 p-5">
            <p className="mb-3 text-xs font-bold uppercase tracking-widest text-white/60">Слито</p>
            <div className="flex items-center gap-2">
              <span className="text-3xl font-black text-white">{formatValue(spent)}</span>
              <img src="/asset/Icons/TelegramStar.png" className="h-6 w-6" alt="Stars" />
            </div>
          </div>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3, delay: 0.1 }}
        className="glass-panel p-8"
        style={{ backgroundColor: 'rgba(34, 36, 42, 0.92)', borderColor: 'rgba(255, 255, 255, 0.1)' }}
      >
        <h4 className="mb-6 text-lg font-black uppercase tracking-widest text-white">
          Мои подарки ({inventory?.length || 0})
        </h4>

        {!inventory || inventory.length === 0 ? (
          <div className="py-12 text-center">
            <p className="text-sm text-white/30">Инвентарь пуст</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {inventory.map((item) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, scale: 0.94 }}
                animate={{ opacity: 1, scale: 1 }}
                className="flex flex-col items-center justify-between rounded-2xl border border-white/10 bg-white/5 p-4"
              >
                <img
                  src={getDynamicGiftImage(item)}
                  alt={item.name || 'Gift'}
                  className="mb-3 h-20 w-20 object-contain"
                  onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }}
                />

                <p className="mb-3 w-full truncate text-center text-xs font-bold text-white">
                  {item.name || 'Gift'}
                </p>

                <motion.button
                  whileTap={{ scale: 0.95 }}
                  onClick={() => handleSell(item)}
                  className="w-full rounded-lg border border-red-500/30 bg-red-500/20 py-2 text-xs font-black uppercase text-red-400"
                >
                  Продать: {Number(item.price || item.cost) || 0}
                </motion.button>
              </motion.div>
            ))}
          </div>
        )}
      </motion.div>
    </div>
  );
}
