import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { fetchDailyInfo, claimDaily, claimPromo, fetchBalance } from '../api';

const ADMIN_IDS = [7782281997, 5396975347];

export default function ProfilePage({ onClose, isPage, inventory, setInventory, transactions, setTransactions, balance, setBalance, spent, donor }) {
  const [user, setUser] = React.useState(null);
  const [adminCommand, setAdminCommand] = React.useState('');
  const [promoCode, setPromoCode] = React.useState('');
  const [dailyStatus, setDailyStatus] = React.useState({ status: 'loading' });
  const [timer, setTimer] = React.useState('');

  React.useEffect(() => {
    if (window.Telegram?.WebApp) {
      const userData = window.Telegram.WebApp.initDataUnsafe?.user;
      setUser(userData);
      if (userData) {
          updateDailyStatus(userData.id);
      }
    }
  }, []);

  const updateDailyStatus = async (uid) => {
      const info = await fetchDailyInfo(uid);
      setDailyStatus(info);
  };

  React.useEffect(() => {
      if (dailyStatus.status === 'cooldown' && dailyStatus.remaining > 0) {
          const interval = setInterval(() => {
              setDailyStatus(prev => {
                  if (prev.remaining <= 1) {
                      clearInterval(interval);
                      return { status: 'ready' };
                  }
                  return { ...prev, remaining: prev.remaining - 1 };
              });
          }, 1000);
          return () => clearInterval(interval);
      }
  }, [dailyStatus]);

  const formatTime = (seconds) => {
      const h = Math.floor(seconds / 3600);
      const m = Math.floor((seconds % 3600) / 60);
      const s = seconds % 60;
      return `${h.toString().padStart(2, '0')}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
  };

  const handleClaimDaily = async () => {
      if (!user?.id) return;
      try {
          const res = await claimDaily(user.id);
          if (res.success) {
              setBalance(prev => prev + res.reward);
              updateDailyStatus(user.id);
              triggerHaptic('success');
              if (window.Telegram?.WebApp) window.Telegram.WebApp.showAlert(`Вы получили ${res.reward} Stars!`);
          }
      } catch (e) {
          if (window.Telegram?.WebApp) window.Telegram.WebApp.showAlert("Кулдаун еще не прошел");
      }
  };

  const handleClaimPromo = async () => {
      if (!user?.id || !promoCode) return;
      try {
          const res = await claimPromo(user.id, promoCode);
          if (res.success) {
              if (res.type === 'stars') {
                  setBalance(prev => prev + res.reward);
              }
              setPromoCode('');
              triggerHaptic('success');
              if (window.Telegram?.WebApp) window.Telegram.WebApp.showAlert(`Промокод активирован! Награда: ${res.reward} ${res.type}`);
          }
      } catch (e) {
          if (window.Telegram?.WebApp) window.Telegram.WebApp.showAlert(e.message || "Ошибка активации промокода");
      }
  };

  const triggerHaptic = (type = 'heavy') => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
        if (type === 'success') {
            window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
        } else {
            window.Telegram.WebApp.HapticFeedback.impactOccurred(type);
        }
    }
  };

  const handleSell = (item) => {
    triggerHaptic();
    if (!setInventory || !setBalance) return;

    setInventory(prev => prev.filter(i => i.id !== item.id));
    setBalance(prev => prev + item.price);

    if (setTransactions) {
      const newTransaction = {
        id: Date.now(),
        type: 'sell',
        amount: item.price,
        description: 'Продажа предмета',
        item: item.name,
      };
      setTransactions(prev => [newTransaction, ...prev]);
    }
    
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
    }
  };

  const handleCopyReferral = () => {
    triggerHaptic();
    const userId = user?.id || 'guest';
    const refLink = `https://t.me/ScreamCase_bot?start=${userId}`;
    navigator.clipboard.writeText(refLink);
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.showPopup({
        title: 'Успех',
        message: 'Реферальная ссылка скопирована!',
        buttons: [{ type: 'ok' }]
      });
      window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
    }
  };

  const handleAdminCommand = (e) => {
    if (e.key === 'Enter') {
      const match = adminCommand.match(/^\+\s*(\d+)$/);
      if (match) {
        const amount = parseInt(match[1]);
        setBalance(prev => prev + amount);
        triggerHaptic();
        if (window.Telegram?.WebApp) {
          window.Telegram.WebApp.showAlert(`Successfully added ${amount} stars!`);
          window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
        }
        setAdminCommand('');
      }
    }
  };

  const content = (
    <div className={`${isPage ? 'min-h-full pb-24' : 'max-w-md mx-auto p-6 min-h-screen'}`}>
      {/* Header */}
      {!isPage && onClose && (
        <div className="flex justify-between items-center mb-8">
          <h2 className="text-2xl font-black text-white">ПРОФИЛЬ</h2>
          <button onClick={onClose} className="text-white/50 hover:text-white text-xl">
            ✕
          </button>
        </div>
      )}
      {isPage && (
        <div className="mb-8">
          <h2 className="text-2xl font-black text-white uppercase tracking-widest">Профиль</h2>
        </div>
      )}

      {/* User Info */}
      <div className="glass-panel p-6 mb-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 blur-3xl rounded-full -mr-16 -mt-16" />
        
        <div className="flex items-center gap-4 mb-6 relative z-10">
          <div className="w-20 h-20 rounded-full border-2 border-white/10 bg-white/5 backdrop-blur-xl flex items-center justify-center overflow-hidden">
            {user?.photo_url ? (
              <img src={user.photo_url} alt="Avatar" className="w-full h-full object-cover" />
            ) : (
              <span className="text-3xl text-white/20 font-black">{user?.first_name?.charAt(0) || 'U'}</span>
            )}
          </div>
          <div>
            <h3 className="text-white font-black text-2xl font-rounded uppercase tracking-tight">
              {user?.first_name || 'GUEST'}
              {ADMIN_IDS.includes(user?.id) && <span className="text-[10px] bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded border border-green-500/30 ml-2 align-middle">ADMIN</span>}
            </h3>
            <p className="text-white/50 text-xs flex items-center gap-1.5 font-rounded font-bold mt-1">
              ID: {user?.id || '000000000'}
              <span className="mx-1 opacity-30">|</span>
              Donor: {donor || 0}
              <img src="/asset/Icons/TelegramStar.png" className="h-5 w-5" alt="Stars" />
            </p>
          </div>
        </div>

        {/* Stats */}
        <div className="grid grid-cols-2 gap-4 relative z-10">
          <div className="p-5 rounded-3xl bg-white/5 border border-white/10 flex flex-col items-center justify-center">
            <p className="text-white/50 text-[10px] mb-1 uppercase tracking-[0.2em] font-rounded font-bold">Баланс</p>
            <p className="text-white font-black text-2xl flex items-center gap-2 font-rounded">
              {balance || 0}
              <img src="/asset/Icons/TelegramStar.png" className="h-7 w-7" alt="Stars" />
            </p>
          </div>
          <div className="p-5 rounded-3xl bg-white/5 border border-white/10 flex flex-col items-center justify-center">
            <p className="text-white/50 text-[10px] mb-1 uppercase tracking-[0.2em] font-rounded font-bold">Потрачено</p>
            <p className="text-white font-black text-2xl flex items-center gap-2 font-rounded">
              {spent || 0}
              <img src="/asset/Icons/TelegramStar.png" className="h-7 w-7" alt="Stars" />
            </p>
          </div>
        </div>
      </div>

      {/* Daily Reward & Promo */}
      <div className="grid grid-cols-1 gap-4 mb-6">
          <div className="glass-panel p-5 relative overflow-hidden group">
            <h4 className="text-white font-black text-sm mb-3 font-rounded uppercase tracking-widest relative z-10">Ежедневный бонус</h4>
            {dailyStatus.status === 'ready' ? (
                <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleClaimDaily}
                    className="w-full py-3 rounded-xl bg-gradient-to-r from-yellow-500 to-orange-500 text-black font-black uppercase tracking-widest text-xs flex items-center justify-center gap-2"
                >
                    ЗАБРАТЬ +10 STARS
                    <img src="/asset/Icons/TelegramStar.png" className="w-4 h-4" />
                </motion.button>
            ) : (
                <div className="w-full py-3 rounded-xl bg-white/5 border border-white/10 text-white/30 font-black uppercase tracking-widest text-xs flex items-center justify-center gap-2">
                    ДОСТУПНО ЧЕРЕЗ {dailyStatus.remaining ? formatTime(dailyStatus.remaining) : '--:--:--'}
                </div>
            )}
          </div>

          <div className="glass-panel p-5 relative overflow-hidden group">
            <h4 className="text-white font-black text-sm mb-3 font-rounded uppercase tracking-widest relative z-10">Промокод</h4>
            <div className="flex gap-2 relative z-10">
                <input
                    type="text"
                    value={promoCode}
                    onChange={(e) => setPromoCode(e.target.value.toUpperCase())}
                    placeholder="ENTER CODE"
                    className="flex-1 bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-white font-bold font-rounded focus:outline-none focus:border-white/30 placeholder:text-white/20 text-sm"
                />
                <motion.button
                    whileTap={{ scale: 0.95 }}
                    onClick={handleClaimPromo}
                    className="px-6 rounded-xl bg-white text-black font-black uppercase tracking-widest text-[10px]"
                >
                    OK
                </motion.button>
            </div>
          </div>
      </div>

      {/* Referral System */}
      <div className="glass-panel p-6 mb-6 relative overflow-hidden group">
        <div className="absolute inset-0 bg-gradient-to-br from-blue-500/5 to-purple-500/5 opacity-0 group-hover:opacity-100 transition-opacity duration-500" />
        <h4 className="text-white font-black text-lg mb-4 font-rounded uppercase tracking-widest relative z-10">Реферальная система</h4>
        
        <div className="space-y-4 relative z-10">
          <p className="text-white/50 text-xs font-rounded leading-relaxed">
            Приглашайте друзей и получайте <span className="text-white font-bold">10%</span> от их пополнений на свой баланс!
          </p>
          
          <motion.button
            whileHover={{ scale: 1.02 }}
            whileTap={{ scale: 0.98 }}
            onClick={handleCopyReferral}
            className="w-full py-4 rounded-2xl bg-white text-black font-black uppercase tracking-widest text-xs flex items-center justify-center gap-2 shadow-lg shadow-white/5"
          >
            СКОПИРОВАТЬ ССЫЛКУ
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
              <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
            </svg>
          </motion.button>
        </div>
      </div>

      {/* Admin Panel */}
      {ADMIN_IDS.includes(user?.id) && (
        <div className="glass-panel p-6 mb-6 border-green-500/20 bg-green-500/5 relative overflow-hidden">
          <div className="absolute top-0 right-0 w-24 h-24 bg-green-500/10 blur-2xl rounded-full -mr-12 -mt-12" />
          <h4 className="text-green-400 font-black text-lg mb-4 font-rounded uppercase tracking-widest relative z-10 flex items-center gap-2">
            Админ-панель
            <span className="w-2 h-2 rounded-full bg-green-500 animate-pulse" />
          </h4>
          
          <div className="space-y-4 relative z-10">
            <div className="space-y-2">
              <p className="text-green-400/50 text-[10px] uppercase font-bold px-1">Команда (в боте: /gen_promo, /clear_cooldown)</p>
              <input
                type="text"
                value={adminCommand}
                onChange={(e) => setAdminCommand(e.target.value)}
                onKeyDown={handleAdminCommand}
                placeholder="+ 500"
                className="w-full bg-black/40 border border-green-500/30 rounded-xl px-4 py-3 text-green-400 font-bold font-rounded focus:outline-none focus:border-green-500/60 placeholder:text-green-900"
              />
            </div>

            <motion.button
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              onClick={() => {
                setBalance(prev => prev + 100);
                triggerHaptic();
                if (window.Telegram?.WebApp) {
                  window.Telegram.WebApp.showAlert("Stars Added by Admin");
                  window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
                }
              }}
              className="w-full py-3 rounded-xl bg-green-500/20 border border-green-500/30 text-green-400 font-black uppercase tracking-widest text-xs flex items-center justify-center gap-2"
            >
              БЫСТРЫЕ +100 STARS
              <img src="/asset/Icons/TelegramStar.png" className="w-4 h-4" />
            </motion.button>
          </div>
        </div>
      )}

      {/* Inventory */}
      <div className="glass-panel p-6 mb-6">
        <h4 className="text-white font-black text-xl mb-4 font-rounded uppercase tracking-widest">Инвентарь ({inventory ? inventory.length : 0})</h4>

        {!inventory || inventory.length === 0 ? (
          <div className="text-center py-12">
            <div className="w-20 h-20 mx-auto mb-4 rounded-3xl bg-white/5 flex items-center justify-center">
              <span className="text-3xl">📦</span>
            </div>
            <p className="text-white/50 font-rounded text-lg">Инвентарь пуст</p>
            <p className="text-white/30 text-sm mt-1 font-rounded">Открывайте ящики!</p>
          </div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {inventory.map((item, index) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className="p-4 rounded-3xl bg-white/5 border border-white/10 flex flex-col items-center relative group"
              >
                <img src={item.image} alt={item.name} className="w-20 h-20 object-contain mb-3" />
                <p className="text-white text-sm font-bold text-center truncate w-full font-rounded mb-1">{item.name}</p>
                <div className="flex items-center gap-1.5 text-white/50 text-xs mb-3 font-rounded font-bold">
                  {item.price}
                  <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" />
                </div>

                {/* Exchange Button */}
                <motion.button
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => handleSell(item)}
                  className="w-full py-2 rounded-xl text-xs font-black uppercase tracking-widest flex items-center justify-center gap-1.5"
                  style={{
                    backgroundColor: 'rgba(239, 68, 68, 0.15)',
                    border: '1px solid rgba(239, 68, 68, 0.3)',
                    color: '#ef4444',
                  }}
                >
                  ОБМЕНЯТЬ ЗА {item.price}
                  <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" />
                </motion.button>
              </motion.div>
            ))}
          </div>
        )}
      </div>

      {/* Transactions */}
      <div className="glass-panel p-6">
        <h4 className="text-white font-black text-xl mb-4 font-rounded uppercase tracking-widest">Транзакции</h4>
        <div className="space-y-4">
          {transactions && transactions.length > 0 ? (
            transactions.map(tx => (
              <div key={tx.id} className="flex justify-between items-center p-3 rounded-2xl bg-white/5 border border-white/5">
                <div>
                  <p className="text-white text-sm font-bold font-rounded uppercase tracking-wide">{tx.description}</p>
                  <p className="text-white/50 text-[10px] font-rounded">
                    {tx.type === 'spend' ? 'Потрачено' : tx.type === 'win' ? 'Выиграно' : 'Пополнение'}
                    {tx.item && ` - ${tx.item}`}
                  </p>
                </div>
                <span className={`font-black text-lg font-rounded flex items-center gap-1.5 ${
                  tx.type === 'spend' ? 'text-red-400' : 'text-green-400'
                }`}>
                  {tx.type === 'spend' ? '-' : '+'}{tx.amount}
                  <img src="/asset/Icons/TelegramStar.png" className="h-5 w-5" alt="Stars" />
                </span>
              </div>
            ))
          ) : (
            <p className="text-white/50 text-sm text-center py-4 font-rounded">Нет транзакций</p>
          )}
        </div>
      </div>
    </div>
  );

  if (isPage) {
    return <div className="p-4 min-h-full overflow-y-auto">{content}</div>;
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: '100%' }}
      animate={{ opacity: 1, x: 0 }}
      exit={{ opacity: 0, x: '100%' }}
      className="fixed inset-0 z-50 bg-black/95 backdrop-blur-sm overflow-y-auto"
    >
      {content}
    </motion.div>
  );
}
