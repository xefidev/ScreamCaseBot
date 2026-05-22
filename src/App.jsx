import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import CountUp from 'react-countup';
import { useTonConnectUI } from '@tonconnect/ui-react';
import CasesGrid from './components/CasesGrid';
import WheelGame from './components/games/WheelGame';
import UpgradeGame from './components/games/UpgradeGame';
import ProfilePage from './components/ProfilePage';
import { createInvoice, fetchBalance, fetchAchievements, claimAchievement, notifyTonSuccess } from './api';

const PAGE_BG = '#22242a';
const TON_WALLET = 'UQA312HDuwVR-RtbUD6u05RAXF-ExIHxExeCZP32RciryUrp';

const TABS = {
  cases: { label: 'Кейсы', icon: '📦' },
  achievements: { label: 'Достижения', icon: '🏆' },
  games: { label: 'Игры', icon: '🎮' },
  profile: { label: 'Профиль', icon: '👤' },
};

const TAB_COLORS = {
  cases: '#ffffff',
  achievements: '#eab308',
  games: '#a855f7',
  profile: '#3b82f6',
};

const LoadingSpinner = () => (
  <div className="flex h-full flex-col items-center justify-center" style={{ backgroundColor: PAGE_BG }}>
    <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} className="mb-4 h-12 w-12 rounded-full border-4 border-white/10 border-t-white" />
    <p className="font-rounded text-xs uppercase tracking-widest text-white/50">Загрузка...</p>
  </div>
);

const formatValue = (value) => {
  if (value === undefined || value === null) return '0';
  if (value >= 1000) return `${(value / 1000).toFixed(1).replace('.0', '')}k`;
  return value.toString();
};

export default function App() {
  const [activeTab, setActiveTab] = useState('cases');
  const [activeGame, setActiveGame] = useState(null);
  const [showTopUp, setShowTopUp] = useState(false);
  const [starsAmount, setStarsAmount] = useState('100');
  const [tonAmount, setTonAmount] = useState('0.1');
  const [tonConnectUI] = useTonConnectUI();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [achievements, setAchievements] = useState([]);
  const [promoOpened, setPromoOpened] = useState(false);
  const [inventory, setInventory] = useState(() => {
    try {
      return JSON.parse(localStorage?.getItem('inventory') || '[]');
    } catch {
      return [];
    }
  });
  const [transactions, setTransactions] = useState(() => {
    try {
      return JSON.parse(localStorage?.getItem('transactions') || '[]');
    } catch {
      return [];
    }
  });
  const [balance, setBalance] = useState(() => {
    try {
      return Number(localStorage?.getItem('balance') || 0);
    } catch {
      return 0;
    }
  });
  const [tickets, setTickets] = useState(0);

  const triggerHaptic = (type = 'light') => {
    try {
      const haptic = window?.Telegram?.WebApp?.HapticFeedback;
      if (haptic) {
        if (type === 'success') haptic.notificationOccurred('success');
        else haptic.impactOccurred(type === 'heavy' ? 'heavy' : 'light');
      }
    } catch (e) {
      console.warn('Haptic not available:', e);
    }
  };

  const syncBalance = async (userId) => {
    if (!userId) return null;
    try {
      const data = await fetchBalance(userId);
      setBalance(data?.stars || 0);
      setTickets(data?.tickets || 0);
      setPromoOpened(!!data?.promo_opened);
      return data;
    } catch (error) {
      console.error('Sync balance error:', error);
      return null;
    }
  };

  const loadAchievements = async (userId = user?.id) => {
    if (!userId) return;
    try {
      const data = await fetchAchievements(userId);
      setAchievements(Array.isArray(data) ? data : []);
    } catch (error) {
      console.error('Load achievements error:', error);
    }
  };

  useEffect(() => {
    const init = async () => {
      try {
        const tg = window?.Telegram?.WebApp;
        if (tg) {
          tg.ready?.();
          tg.expand?.();
          const userData = tg.initDataUnsafe?.user;
          if (userData) {
            setUser(userData);
            await syncBalance(userData.id);
          }
        }
      } catch (e) {
        console.warn('Telegram init error:', e);
      }
      setLoading(false);
    };
    init();
  }, []);

  useEffect(() => {
    if (activeTab === 'achievements') loadAchievements();
  }, [activeTab]);

  useEffect(() => {
    try {
      localStorage?.setItem('inventory', JSON.stringify(inventory));
      localStorage?.setItem('transactions', JSON.stringify(transactions));
      localStorage?.setItem('balance', balance.toString());
    } catch (e) {
      console.warn('localStorage error:', e);
    }
  }, [inventory, transactions, balance]);

  const handleStarsPayment = async () => {
    triggerHaptic();
    if (!user?.id) {
      window?.Telegram?.WebApp?.showAlert?.('❌ Пользователь не определен');
      return;
    }
    try {
      const { link } = await createInvoice(user.id, starsAmount);
      window?.Telegram?.WebApp?.openTelegramLink?.(link);
      setShowTopUp(false);
    } catch (error) {
      console.error('Invoice error:', error);
      window?.Telegram?.WebApp?.showAlert?.('❌ Ошибка при создании инвойса');
    }
  };

  const handleTonPayment = async () => {
    triggerHaptic();
    if (!user?.id) {
      window?.Telegram?.WebApp?.showAlert?.('❌ Пользователь не определен');
      return;
    }
    const amount = parseFloat(tonAmount) || 0.1;
    const nanotons = (amount * 1000000000).toString();
    try {
      const result = await tonConnectUI?.sendTransaction?.({
        validUntil: Math.floor(Date.now() / 1000) + 600,
        messages: [{ address: TON_WALLET, amount: nanotons }],
      });
      triggerHaptic('success');
      setShowTopUp(false);
      if (user?.id && result) {
        await notifyTonSuccess(user.id, amount, result.boc);
        await syncBalance(user.id);
      }
      window?.Telegram?.WebApp?.showAlert?.('✅ Пополнение успешно!');
    } catch (e) {
      console.error('TON payment error:', e);
      window?.Telegram?.WebApp?.showAlert?.('❌ Ошибка или отмена транзакции');
    }
  };

  const handleClaimAchievement = async (aid) => {
    triggerHaptic();
    if (!user?.id) return;
    try {
      const res = await claimAchievement(user.id, aid);
      if (res?.success) {
        triggerHaptic('success');
        await syncBalance(user.id);
        await loadAchievements();
      }
    } catch (e) {
      console.error('Claim achievement error:', e);
    }
  };

  const handleSpinComplete = (item, caseItem) => {
    if (user?.id) syncBalance(user.id);
    const inventoryItem = {
      id: Date.now(),
      name: item?.name || 'Item',
      image: item?.image || '',
      price: item?.price || 0,
      caseName: caseItem?.name
    };
    setInventory((prev) => [inventoryItem, ...prev]);
  };

  const renderAchievements = () => (
    <div className="h-full overflow-y-auto p-6 pb-24" style={{ backgroundColor: PAGE_BG }}>
      <h2 className="mb-6 font-rounded text-2xl font-black uppercase tracking-tight text-white">Достижения</h2>
      <div className="space-y-4">
        {achievements?.map?.((a) => {
          const progress = Math.min(a?.progress || 0, a?.goal || 1);
          const percent = (progress / (a?.goal || 1)) * 100;
          const isComplete = progress >= (a?.goal || 1);
          return (
            <div key={a?.id} className="glass-panel p-5 border-white/10 bg-white/[0.02] relative overflow-hidden">
              {isComplete && !a?.is_claimed && (
                <div className="absolute inset-0 bg-yellow-500/5 animate-pulse-slow pointer-events-none" />
              )}
              <div className="flex justify-between items-start mb-3">
                <div>
                  <h3 className="font-black text-sm uppercase tracking-tight text-white">
                    {a?.title || 'Достижение'}
                  </h3>
                  <p className="text-[10px] text-white/40 font-bold uppercase">
                    Награда: {a?.reward || 0} ⭐
                  </p>
                </div>
                <span className="text-[10px] font-black text-white/20 uppercase tracking-widest">
                  {progress}/{a?.goal || 1}
                </span>
              </div>
              <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden mb-4">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${percent}%` }}
                  className="h-full bg-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)]"
                />
              </div>
              {a?.is_claimed ? (
                <div className="w-full py-2 rounded-xl bg-white/5 border border-white/5 text-center">
                  <span className="text-[10px] font-black uppercase text-white/20">Награда получена</span>
                </div>
              ) : (
                <button
                  onClick={() => handleClaimAchievement(a?.id)}
                  disabled={!isComplete}
                  className={`w-full py-2.5 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all ${
                    isComplete
                      ? 'bg-yellow-500 text-black shadow-lg shadow-yellow-500/20 cursor-pointer hover:bg-yellow-600'
                      : 'bg-white/5 text-white/20 cursor-not-allowed'
                  }`}
                >
                  Забрать награду
                </button>
              )}
            </div>
          );
        }) || <p className="text-white/50 text-center">Загрузка достижений...</p>}
      </div>
    </div>
  );

  const renderContent = () => {
    if (loading) return <LoadingSpinner />;

    switch (activeTab) {
      case 'cases':
        return (
          <CasesGrid
            user={user}
            onWin={handleSpinComplete}
            balance={balance}
            setBalance={setBalance}
            promoOpened={promoOpened}
            setPromoOpened={setPromoOpened}
          />
        );
      case 'achievements':
        return renderAchievements();
      case 'games':
        if (activeGame === 'wheel') {
          return (
            <div className="h-full overflow-y-auto" style={{ backgroundColor: PAGE_BG }}>
              <div className="p-4">
                <button
                  onClick={() => setActiveGame(null)}
                  className="glass-button p-2 text-white/70 rounded-lg hover:bg-white/10"
                >
                  Назад
                </button>
              </div>
              <WheelGame
                isPage
                onWin={() => syncBalance(user?.id)}
                balance={balance}
                setBalance={setBalance}
              />
            </div>
          );
        }
        if (activeGame === 'upgrade') {
          return (
            <div className="h-full overflow-y-auto" style={{ backgroundColor: PAGE_BG }}>
              <div className="p-4">
                <button
                  onClick={() => setActiveGame(null)}
                  className="glass-button p-2 text-white/70 rounded-lg hover:bg-white/10"
                >
                  Назад
                </button>
              </div>
              <UpgradeGame
                isPage
                inventory={inventory}
                setInventory={setInventory}
                balance={balance}
                setBalance={setBalance}
              />
            </div>
          );
        }
        return (
          <div className="h-full overflow-y-auto p-6 pb-24 text-white" style={{ backgroundColor: PAGE_BG }}>
            <h2 className="mb-2 font-rounded text-2xl font-black uppercase tracking-tight">Мини-игры</h2>
            <div className="grid grid-cols-1 gap-4 mt-6">
              <button
                onClick={() => {
                  triggerHaptic();
                  setActiveGame('wheel');
                }}
                className="relative h-40 overflow-hidden rounded-3xl border border-purple-500/30 text-left bg-gradient-to-br from-purple-600/10 to-black/20 shadow-[0_0_30px_rgba(168,85,247,0.15)] hover:shadow-[0_0_50px_rgba(168,85,247,0.3)] transition-shadow duration-500"
              >
                <img
                  src="/asset/Icons/WheelGameIcon.gif"
                  alt="wheel"
                  className="absolute right-2 top-2 h-24 w-24 object-contain opacity-40 pointer-events-none"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-purple-500/5 to-transparent pointer-events-none" />
                <div className="relative z-10 flex h-full flex-col justify-between p-6">
                  <div>
                    <h3 className="font-rounded text-xl font-black uppercase">Колесо Фортуны</h3>
                    <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-purple-400">
                      Выигрыш до 500 звезд
                    </p>
                  </div>
                  <span className="text-xs font-black uppercase text-white/60">Играть →</span>
                </div>
              </button>

              <button
                onClick={() => {
                  triggerHaptic();
                  setActiveGame('upgrade');
                }}
                className="relative h-40 overflow-hidden rounded-3xl border border-green-500/30 text-left bg-gradient-to-br from-green-600/10 to-black/20 shadow-[0_0_30px_rgba(34,197,94,0.15)] hover:shadow-[0_0_50px_rgba(34,197,94,0.3)] transition-shadow duration-500"
              >
                <img
                  src="/asset/Icons/UpgradeGameIcon.gif"
                  alt="upgrade"
                  className="absolute right-2 top-2 h-24 w-24 object-contain opacity-40 pointer-events-none"
                  onError={(e) => {
                    e.currentTarget.style.display = 'none';
                  }}
                />
                <div className="absolute inset-0 bg-gradient-to-t from-green-500/5 to-transparent pointer-events-none" />
                <div className="relative z-10 flex h-full flex-col justify-between p-6">
                  <div>
                    <h3 className="font-rounded text-xl font-black uppercase">Апгрейд</h3>
                    <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-green-400">
                      Улучшай свои предметы
                    </p>
                  </div>
                  <span className="text-xs font-black uppercase text-white/60">Играть →</span>
                </div>
              </button>
            </div>
          </div>
        );
      case 'profile':
        return (
          <ProfilePage
            isPage
            inventory={inventory}
            setInventory={setInventory}
            balance={balance}
            setBalance={setBalance}
          />
        );
      default:
        return <LoadingSpinner />;
    }
  };

  return (
    /* Главный контейнер на всю высоту — скролл тут запрещен */
    <div className="h-screen w-full overflow-hidden flex justify-center items-center bg-[#050505] text-white font-rounded select-none">
      
      {/* Адаптивное окно: на ПК max-w-md по центру, на смартфонах во весь экран. Скролл тут тоже запрещен */}
      <div className="relative z-10 flex flex-col h-screen w-full max-w-md bg-black md:border-x md:border-white/10 overflow-hidden">
        
        {/* Шапка — жестко зафиксирована, не сжимается */}
        <div className="shrink-0">
          <div className="glass-panel border-b border-white/10 px-6 py-4" style={{ backgroundColor: PAGE_BG }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-white/5">
                {user?.photo_url ? (
                  <img
                    src={user?.photo_url}
                    alt="profile"
                    className="h-full w-full object-cover"
                    onError={(e) => {
                      e.currentTarget.style.display = 'none';
                    }}
                  />
                ) : (
                  <span className="font-bold text-white/30">{user?.first_name?.charAt(0) || 'U'}</span>
                )}
              </div>
              <h1 className="text-lg font-black uppercase text-white truncate max-w-[120px]">
                {user?.first_name || 'Игрок'}
              </h1>
            </div>
            <button
              onClick={() => {
                setShowTopUp(true);
                triggerHaptic();
              }}
              className="glass-button flex items-center gap-2 border-yellow-500/30 bg-yellow-500/5 px-4 py-2 rounded-lg hover:bg-yellow-500/10 transition-colors"
            >
              <img
                src="/asset/Icons/TelegramStar.png"
                alt="star"
                className="h-6 w-6"
                onError={(e) => {
                  e.currentTarget.src = '/asset/Gifts/Case.webp';
                }}
              />
              <span className="text-lg font-black text-yellow-400">
                <CountUp end={balance} duration={0.5} />
              </span>
              <span className="text-xs font-bold text-yellow-400/50">+</span>
            </button>
          </div>
          </div>
        </div>

        {/* Контентная часть — единственный блок, которому РАЗРЕШЕН вертикальный скролл. Скроллбар скрыт */}
        <div className="flex-1 overflow-y-auto px-4 py-2 [&::-webkit-scrollbar]:hidden [-ms-overflow-style:'none'] [scrollbar-width:'none']">
          {renderContent()}
        </div>

        {/* Нижнее меню (Navbar) — жестко зафиксировано снизу, не сжимается */}
        <div className="shrink-0 pb-safe">
          <div className="glass-panel border-t border-white/10 px-4 py-2" style={{ backgroundColor: PAGE_BG }}>
          <div className="flex h-16 items-center justify-around">
            {Object.entries(TABS).map(([key, tabData]) => (
              <button
                key={key}
                className="relative flex h-12 w-16 flex-col items-center justify-center transition-all gap-0.5"
                onClick={() => {
                  setActiveTab(key);
                  setActiveGame(null);
                  triggerHaptic();
                }}
                title={tabData.label}
              >
                {activeTab === key && (
                  <motion.div
                    layoutId="pill"
                    className="absolute inset-[-4px] rounded-2xl border border-white/10 bg-white/5"
                  />
                )}
                <span
                  className={`z-10 text-lg transition-all ${
                    activeTab === key ? 'text-white scale-110' : 'text-white/40'
                  }`}
                >
                  {tabData.icon}
                </span>
                <span
                  className={`z-10 text-[7px] font-black uppercase tracking-tighter whitespace-nowrap transition-all ${
                    activeTab === key ? 'text-white' : 'text-white/30'
                  }`}
                >
                  {tabData.label}
                </span>
              </button>
            ))}
          </div>
        </div>
        </div>
      </div>

      {/* Top-Up Modal */}
      <AnimatePresence>
        {showTopUp && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 backdrop-blur-sm"
            onClick={() => setShowTopUp(false)}
          >
            <motion.div
              initial={{ scale: 0.95, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.95, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="glass-panel w-full max-w-sm mx-4 rounded-3xl border border-white/20 p-0 overflow-hidden"
              style={{ backgroundColor: PAGE_BG }}
            >
              {/* Заголовок с красивым фоном */}
              <div className="relative p-8 pb-6 bg-gradient-to-b from-white/5 to-transparent border-b border-white/10">
                <div className="absolute top-0 right-0 w-32 h-32 bg-yellow-500/10 rounded-full blur-2xl -mr-16 -mt-8 pointer-events-none" />
                <div className="relative z-10">
                  <h2 className="text-center text-2xl font-black uppercase tracking-widest text-white mb-2">
                    Пополнить Баланс
                  </h2>
                  <p className="text-center text-[10px] font-black uppercase tracking-[0.2em] text-white/40">
                    Выбери удобный способ платежа
                  </p>
                </div>
              </div>

              {/* Содержимое */}
              <div className="p-6 space-y-4">
                {/* Telegram Stars */}
                <motion.div
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="glass-panel p-6 border border-yellow-500/30 bg-gradient-to-br from-yellow-500/10 to-transparent cursor-pointer hover:border-yellow-500/50 transition-all"
                >
                  <div className="flex items-start gap-4 mb-4">
                    <div className="p-3 rounded-2xl bg-yellow-500/20">
                      <img
                        src="/asset/Icons/TelegramStar.png"
                        className="h-8 w-8"
                        alt="stars"
                        onError={(e) => {
                          e.currentTarget.src = '/asset/Gifts/Case.webp';
                        }}
                      />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-black text-sm uppercase text-white tracking-tight">Telegram Звёзды</h3>
                      <p className="text-[9px] text-white/40 font-bold">Мгновенное пополнение</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mb-4">
                    <input
                      type="number"
                      value={starsAmount}
                      onChange={(e) => setStarsAmount(e.target.value)}
                      className="flex-1 bg-white/5 border border-yellow-500/20 rounded-xl p-3 text-right font-black text-yellow-400 placeholder-white/20 focus:outline-none focus:border-yellow-500/50"
                      placeholder="100"
                      min="1"
                    />
                    <span className="text-white/40 text-sm font-black">⭐</span>
                  </div>
                  <button
                    onClick={handleStarsPayment}
                    disabled={!user?.id}
                    className="w-full py-3 rounded-xl bg-yellow-500 text-black font-black uppercase tracking-widest text-sm hover:bg-yellow-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-yellow-500/20"
                  >
                    Купить за {starsAmount} ⭐
                  </button>
                  <p className="text-[8px] text-white/30 font-black uppercase text-center mt-2">Конвертируется по курсу 1:1</p>
                </motion.div>

                {/* TON */}
                <motion.div
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className="glass-panel p-6 border border-blue-500/30 bg-gradient-to-br from-blue-500/10 to-transparent cursor-pointer hover:border-blue-500/50 transition-all"
                >
                  <div className="flex items-start gap-4 mb-4">
                    <div className="p-3 rounded-2xl bg-blue-500/20">
                      <img
                        src="/asset/Icons/TonCoin.png"
                        className="h-8 w-8"
                        alt="ton"
                        onError={(e) => {
                          e.currentTarget.src = '/asset/Gifts/Case.webp';
                        }}
                      />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-black text-sm uppercase text-white tracking-tight">TON Blockchain</h3>
                      <p className="text-[9px] text-white/40 font-bold">100 ⭐ = 1 TON</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 mb-4">
                    <input
                      type="number"
                      value={tonAmount}
                      onChange={(e) => setTonAmount(e.target.value)}
                      className="flex-1 bg-white/5 border border-blue-500/20 rounded-xl p-3 text-right font-black text-blue-400 placeholder-white/20 focus:outline-none focus:border-blue-500/50"
                      placeholder="0.1"
                      step="0.1"
                      min="0.1"
                    />
                    <span className="text-white/40 text-sm font-black">TON</span>
                  </div>
                  <button
                    onClick={handleTonPayment}
                    disabled={!user?.id}
                    className="w-full py-3 rounded-xl bg-blue-500 text-white font-black uppercase tracking-widest text-sm hover:bg-blue-600 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20"
                  >
                    Отправить {(parseFloat(tonAmount) || 0.1) * 100} ⭐
                  </button>
                  <p className="text-[8px] text-white/30 font-black uppercase text-center mt-2">Безопасно через тон-кошелёк</p>
                </motion.div>

                {/* Информация */}
                <div className="p-4 rounded-2xl bg-white/[0.02] border border-white/10">
                  <div className="space-y-2 text-[9px] text-white/50 font-bold uppercase tracking-wide">
                    <div className="flex items-start gap-2">
                      <span className="text-white/30 mt-0.5">✓</span>
                      <span>Средства зачислятся мгновенно</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="text-white/30 mt-0.5">✓</span>
                      <span>100% безопасно и зашифровано</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="text-white/30 mt-0.5">✓</span>
                      <span>Без скрытых комиссий и платежей</span>
                    </div>
                  </div>
                </div>
              </div>

              {/* Кнопка закрытия */}
              <div className="px-6 pb-6 pt-0">
                <button
                  onClick={() => setShowTopUp(false)}
                  className="w-full py-3 rounded-xl border border-white/10 bg-white/5 text-white font-black uppercase tracking-widest text-[10px] hover:bg-white/10 transition-colors"
                >
                  Отмена
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
