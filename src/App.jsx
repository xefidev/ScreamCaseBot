import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CountUp from 'react-countup';
import CasesGrid from './components/CasesGrid';
import WheelGame from './components/games/WheelGame';
import UpgradeGame from './components/games/UpgradeGame';
import ProfilePage from './components/ProfilePage';
import { useTonConnectUI } from '@tonconnect/ui-react';
import { fetchBalance, addStars, createInvoice } from './api';

const LoadingSpinner = () => (
  <div className="flex flex-col items-center justify-center h-full">
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      className="w-12 h-12 border-4 border-white/10 border-t-white rounded-full mb-4"
    />
    <p className="text-white/50 font-rounded animate-pulse uppercase tracking-widest text-xs">Loading Balance...</p>
  </div>
);

const TABS = {
  cases: 'Cases',
  fortune: 'Fortune',
  upgrade: 'Upgrade',
  profile: 'Profile',
};

const ADMIN_IDS = [7782281997, 5396975347];
const CHANNEL_LINK = 'https://t.me/ScreamCase';
const TON_WALLET = 'UQA312HDuwVR-RtbUD6u05RAXF-ExIHxExeCZP32RciryUrp';
const PRODUCTION_URL = 'https://scream-case-bot.vercel.app';

const TAB_COLORS = {
  cases: { bubble: 'rgba(255, 255, 255, 0.15)', icon: '#ffffff' },
  fortune: { bubble: 'rgba(168, 85, 247, 0.15)', icon: '#a855f7' },
  upgrade: { bubble: 'rgba(34, 197, 94, 0.15)', icon: '#22c55e' },
  profile: { bubble: 'rgba(59, 130, 246, 0.15)', icon: '#3b82f6' },
};

export default function App() {
  const [activeTab, setActiveTab] = useState('cases');
  const [showTopUp, setShowTopUp] = useState(false);
  const [starsAmount, setStarsAmount] = useState('100');
  const [tonAmount, setTonAmount] = useState('1');
  const [tonConnectUI] = useTonConnectUI();
  const [showSubscriptionPopup, setShowSubscriptionPopup] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(() => {
    const saved = localStorage.getItem('isSubscribed');
    return saved === 'true';
  });

  const [user, setUser] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  const triggerHaptic = (type = 'light') => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      if (type === 'success') {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
      } else {
        window.Telegram.WebApp.HapticFeedback.impactOccurred(type === 'heavy' ? 'heavy' : 'light');
      }
    }
  };

  const syncBalance = async (userId) => {
    if (!userId) return;
    const b = await fetchBalance(userId);
    setBalance(b);
    return b;
  };

  const handleChannelLink = () => {
    triggerHaptic();
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.openTelegramLink(CHANNEL_LINK);
    } else {
      window.open(CHANNEL_LINK, '_blank');
    }
  };

  // Initialize Telegram User
  React.useEffect(() => {
    const init = async () => {
      if (window.Telegram?.WebApp) {
        const tg = window.Telegram.WebApp;
        tg.ready();
        tg.expand();
        const userData = tg.initDataUnsafe?.user;
        if (userData) {
          setUser(userData);
          setIsAdmin(ADMIN_IDS.includes(userData.id));
          await syncBalance(userData.id);
          
          // Track Referral
          const startParam = tg.initDataUnsafe?.start_param;
          if (startParam) {
            console.log('Referrer ID:', startParam);
          }
        }
      }
      setLoading(false);
    };
    init();
  }, []);

  // Check subscription on mount
  React.useEffect(() => {
    if (!isSubscribed) {
      const timer = setTimeout(() => {
        setShowSubscriptionPopup(true);
      }, 2000);
      return () => clearTimeout(timer);
    }
  }, [isSubscribed]);

  const handleCheckSubscription = async () => {
    triggerHaptic();
    // In a real app, you'd fetch this from your backend which uses the bot token
    // Example: const res = await fetch(`${API_URL}/check-sub?user_id=${user.id}`)
    
    // Simulate check
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.showConfirm("Вы действительно подписаны на @ScreamCase?", (ok) => {
        if (ok) {
          setIsSubscribed(true);
          localStorage.setItem('isSubscribed', 'true');
          setShowSubscriptionPopup(false);
          window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
        }
      });
    } else {
      setIsSubscribed(true);
      localStorage.setItem('isSubscribed', 'true');
      setShowSubscriptionPopup(false);
    }
  };

  const handleStarsPayment = async () => {
    triggerHaptic();
    if (!user?.id) return;
    try {
      const { link } = await createInvoice(user.id, starsAmount);
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.openTelegramLink(link);
        setShowTopUp(false);
      }
    } catch (e) {
      console.error(e);
      if (window.Telegram?.WebApp) window.Telegram.WebApp.showAlert("Ошибка при создании инвойса");
    }
  };

  const handleTonPayment = async () => {
    triggerHaptic();
    const amount = 0.1; // Фиксированная сумма 0.1 TON как в ТЗ
    const nanotons = (amount * 1000000000).toString();
    
    const transaction = {
      validUntil: Math.floor(Date.now() / 1000) + 600, // 10 minutes
      messages: [
        {
          address: TON_WALLET,
          amount: nanotons,
        },
      ],
    };

    try {
      await tonConnectUI.sendTransaction(transaction);
      triggerHaptic('success');
      setShowTopUp(false);
      if (window.Telegram?.WebApp) window.Telegram.WebApp.showAlert("Транзакция отправлена!");
    } catch (e) {
      console.error(e);
      if (window.Telegram?.WebApp) window.Telegram.WebApp.showAlert("Ошибка или отмена транзакции");
    }
  };

  const [inventory, setInventory] = useState(() => {
    const saved = localStorage.getItem('inventory');
    return saved ? JSON.parse(saved) : [];
  });

  const [transactions, setTransactions] = useState(() => {
    const saved = localStorage.getItem('transactions');
    return saved ? JSON.parse(saved) : [];
  });

  const [balance, setBalance] = useState(() => {
    const saved = localStorage.getItem('balance');
    return saved ? parseInt(saved) : 0;
  });
  const [spent, setSpent] = useState(() => {
    const saved = localStorage.getItem('spent');
    return saved ? parseInt(saved) : 0;
  });
  const [donor, setDonor] = useState(() => {
    const saved = localStorage.getItem('donor');
    return saved ? parseInt(saved) : 0;
  });

  React.useEffect(() => {
    localStorage.setItem('inventory', JSON.stringify(inventory));
    localStorage.setItem('transactions', JSON.stringify(transactions));
    localStorage.setItem('balance', balance.toString());
    localStorage.setItem('spent', spent.toString());
    localStorage.setItem('donor', donor.toString());
  }, [inventory, transactions, balance, spent, donor]);

  const handleSpinComplete = (item, caseItem) => {
    const newItem = {
      id: Date.now(),
      name: item.name,
      image: item.image,
      price: item.price,
    };
    setInventory(prev => [...prev, newItem]);

    if (caseItem) {
      setSpent(prev => prev + caseItem.price);
    }

    const newTransaction = {
      id: Date.now(),
      type: 'win',
      amount: caseItem ? caseItem.price : 0,
      description: caseItem ? caseItem.name : 'Wheel Spin',
      item: item.name,
    };
    setTransactions(prev => [newTransaction, ...prev]);
    
    // Refresh balance from server
    syncBalance(user?.id);
  };

  const handleWheelWin = (segment) => {
    const newItem = {
      id: Date.now(),
      name: segment.label,
      image: segment.image,
      price: segment.price || parseInt(segment.label) || 100,
    };
    setInventory(prev => [...prev, newItem]);
    setSpent(prev => prev + 50);

    const newTransaction = {
      id: Date.now(),
      type: 'win',
      amount: 50,
      description: 'Wheel of Fortune',
      item: segment.label,
    };
    setTransactions(prev => [...prev, newTransaction]);
    setBalance(prev => Math.max(0, prev - 50));
    
    // Refresh balance from server
    syncBalance(user?.id);
  };

  const renderContent = () => {
    if (loading) return <LoadingSpinner />;
    
    switch (activeTab) {
      case 'cases':
        return <CasesGrid onBuy={handleBuy} onWin={handleSpinComplete} balance={balance} setBalance={setBalance} />;
      case 'fortune':
        return <WheelGame isPage={true} onWin={handleWheelWin} balance={balance} setBalance={setBalance} />;
      case 'upgrade':
        return <UpgradeGame isPage={true} inventory={inventory} setInventory={setInventory} balance={balance} setBalance={setBalance} setSpent={setSpent} />;
      case 'profile':
        return (
          <div className="flex flex-col h-full overflow-y-auto">
            <ProfilePage
              isPage={true}
              inventory={inventory}
              setInventory={setInventory}
              transactions={transactions}
              setTransactions={setTransactions}
              balance={balance}
              setBalance={setBalance}
              spent={spent}
              donor={donor}
            />
            {isAdmin && (
              <div className="p-6 pb-24">
                <div className="glass-panel p-4 border-red-500/20 bg-red-500/5">
                  <h3 className="text-red-400 font-bold text-sm mb-4 uppercase tracking-widest flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                    Admin Debug Panel
                  </h3>
                  <div className="grid grid-cols-2 gap-3">
                    <motion.button
                      whileTap={{ scale: 0.95 }}
                      onClick={async () => {
                        triggerHaptic('heavy');
                        try {
                          await addStars(user.id, 100);
                          await syncBalance(user.id);
                          triggerHaptic('success');
                        } catch (e) {
                          window.Telegram?.WebApp?.showAlert('Error adding stars');
                        }
                      }}
                      className="glass-button py-3 text-[10px] font-black uppercase tracking-tighter border-red-500/30 text-red-400"
                    >
                      Add +100 Stars
                    </motion.button>
                    <motion.button
                      whileTap={{ scale: 0.95 }}
                      onClick={() => {
                        triggerHaptic('heavy');
                        localStorage.clear();
                        window.location.reload();
                      }}
                      className="glass-button py-3 text-[10px] font-black uppercase tracking-tighter border-white/20 text-white/50"
                    >
                      Clear Cache
                    </motion.button>
                  </div>
                </div>
              </div>
            )}
          </div>
        );
      default:
        return <CasesGrid onBuy={handleBuy} onWin={handleSpinComplete} balance={balance} setBalance={setBalance} />;
    }
  };

  const handleBuy = (caseItem) => {
    setSelectedCase(caseItem);
    setIsSpinning(true);
  };

  const [selectedCase, setSelectedCase] = useState(null);
  const [isSpinning, setIsSpinning] = useState(false);

  return (
    <div className="min-h-screen w-full bg-black text-white overflow-hidden">
      {/* Animated background elements */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <motion.div
          className="absolute top-0 left-1/4 w-96 h-96 rounded-full bg-white/5 blur-3xl"
          animate={{
            opacity: [0.1, 0.3, 0.1],
            scale: [0.8, 1.2, 0.8],
          }}
          transition={{ duration: 8, repeat: Infinity }}
        />
        <motion.div
          className="absolute bottom-0 right-1/4 w-96 h-96 rounded-full bg-white/5 blur-3xl"
          animate={{
            opacity: [0.1, 0.3, 0.1],
            scale: [1.2, 0.8, 1.2],
          }}
          transition={{ duration: 8, repeat: Infinity, delay: 1 }}
        />
      </div>

      {/* Main content */}
      <div className="relative z-10 flex flex-col h-screen">
        {/* Header */}
        <motion.div
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          className="glass-panel border-b border-white/10 px-6 py-4"
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full border border-white/10 bg-white/5 backdrop-blur-xl flex items-center justify-center">
                <div className="w-10 h-10 rounded-full bg-gradient-to-br from-white/30 to-white/10 overflow-hidden">
                  {user?.photo_url ? (
                    <img src={user.photo_url} alt="User" className="w-full h-full object-cover" />
                  ) : (
                    <div className="w-full h-full flex items-center justify-center text-white/30 font-bold">
                      {user?.first_name?.charAt(0) || 'U'}
                    </div>
                  )}
                </div>
              </div>
              <div>
                <h1 className="text-white font-black text-xl font-rounded">{user?.first_name || 'GUEST'} {isAdmin && <span className="text-[10px] bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded border border-green-500/30 ml-1">ADMIN</span>}</h1>
                <p className="text-white/50 text-xs flex items-center gap-1.5">
                  Donor: {donor}
                  <img src="/asset/Icons/TelegramStar.png" className="h-5 w-5" alt="Stars" />
                  <span className="mx-1">|</span>
                  Spent: {spent}
                  <img src="/asset/Icons/TelegramStar.png" className="h-5 w-5" alt="Stars" />
                </p>
              </div>
            </div>
            <motion.button
              whileHover={{ scale: 1.05 }}
              whileTap={{ scale: 0.95 }}
              onClick={() => {
                setShowTopUp(true);
                triggerHaptic();
              }}
              className="glass-button flex items-center gap-3 px-5 py-2.5"
            >
              <img src="/asset/Icons/TelegramStar.png" alt="Stars" className="w-7 h-7" />
              <span className="text-white font-black text-xl font-rounded">
                <CountUp end={balance} duration={0.5} />
              </span>
              <div className="w-7 h-7 rounded-full border border-white/30 flex items-center justify-center">
                <span className="text-white/70 text-lg font-bold">+</span>
              </div>
            </motion.button>
          </div>
        </motion.div>

        {/* Tab Content */}
        <div className="flex-1 overflow-y-auto framer-motion-fix">
          {renderContent()}
        </div>

        {/* Navigation bar - TG Liquid Glass Style with animated pill */}
        <div className="glass-panel border-t border-white/10 px-4 py-3 safe-area-inset-bottom">
          <div className="flex justify-around items-center relative h-16">
            {Object.entries(TABS).map(([key, label]) => {
              const isActive = activeTab === key;
              const tabColor = TAB_COLORS[key];
              return (
                <motion.button
                  key={key}
                  className="relative w-16 h-12 flex flex-col items-center justify-center z-10 cursor-pointer"
                  onClick={() => {
                    setActiveTab(key);
                    triggerHaptic();
                  }}
                  whileTap={{ scale: 0.9 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                >
                  {/* The Pill (КАПЛЯ) - Only rendered inside the active tab */}
                  {isActive && (
                    <motion.div
                      layoutId="activeTabPill"
                      className="absolute inset-[-4px] rounded-2xl z-0"
                      style={{ 
                        backgroundColor: 'rgba(74, 222, 128, 0.15)',
                        backdropFilter: 'blur(8px)',
                        border: '1px solid rgba(74, 222, 128, 0.2)',
                      }}
                      transition={{ 
                        type: 'spring', 
                        stiffness: 400, 
                        damping: 30,
                        mass: 0.8
                      }}
                    />
                  )}

                  <motion.div
                    animate={{
                      color: isActive ? tabColor.icon : 'rgba(255,255,255,0.5)',
                      scale: isActive ? 1.15 : 1,
                    }}
                    transition={{ duration: 0.2 }}
                    className="relative z-10 pointer-events-none"
                  >
                    {key === 'cases' && (
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="3" y="3" width="7" height="7" rx="1" />
                        <rect x="14" y="3" width="7" height="7" rx="1" />
                        <rect x="14" y="14" width="7" height="7" rx="1" />
                        <rect x="3" y="14" width="7" height="7" rx="1" />
                      </svg>
                    )}
                    {key === 'fortune' && (
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <path d="M12 6v6l4 2" />
                      </svg>
                    )}
                    {key === 'upgrade' && (
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M12 3v18M3 12h18M8 8l-4 4 4 4M16 8l4 4-4 4" />
                      </svg>
                    )}
                    {key === 'profile' && (
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    )}
                  </motion.div>

                  <span className={`relative z-10 text-[10px] mt-0.5 pointer-events-none ${isActive ? 'text-white font-semibold' : 'text-white/40'}`}>
                    {label}
                  </span>
                </motion.button>
              );
            })}
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
            className="fixed inset-0 z-50 flex items-end justify-center bg-black/80 backdrop-blur-sm"
            onClick={() => setShowTopUp(false)}
          >
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-md glass-panel rounded-t-3xl p-6 pb-8"
            >
              <div className="w-12 h-1 bg-white/20 rounded-full mx-auto mb-6" />
              <h2 className="text-white font-bold text-xl mb-2 text-center">Пополнение</h2>
              <p className="text-white/50 text-sm text-center mb-6">Выберите способ пополнения баланса</p>

              <div className="space-y-4">
                {/* Stars */}
                <div className="glass-panel p-4 space-y-3">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-yellow-500/10 border border-yellow-500/20 flex items-center justify-center">
                      <img src="/asset/Icons/TelegramStar.png" alt="Stars" className="w-8 h-8" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-white font-bold">Stars</p>
                      <p className="text-white/50 text-[10px] uppercase">Telegram Stars</p>
                    </div>
                    <div className="w-24">
                      <input
                        type="number"
                        value={starsAmount}
                        onChange={(e) => setStarsAmount(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-right text-yellow-400 font-bold font-rounded"
                        placeholder="100"
                      />
                    </div>
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleStarsPayment}
                    className="w-full py-2.5 rounded-xl bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 font-black text-sm uppercase tracking-widest font-rounded"
                  >
                    ПОПОЛНИТЬ
                  </motion.button>
                </div>

                {/* TON */}
                <div className="glass-panel p-4 space-y-3 border-blue-500/20 bg-blue-500/5">
                  <div className="flex items-center gap-4">
                    <div className="w-12 h-12 rounded-2xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center">
                      <img src="/asset/Icons/TonCoin.png" alt="TON" className="w-8 h-8" />
                    </div>
                    <div className="flex-1 text-left">
                      <p className="text-white font-bold">TON Crystal</p>
                      <p className="text-white/50 text-[10px] uppercase tracking-tighter truncate w-32">{TON_WALLET}</p>
                    </div>
                    <div className="w-24">
                      <input
                        type="number"
                        value={tonAmount}
                        onChange={(e) => setTonAmount(e.target.value)}
                        className="w-full bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-right text-blue-400 font-bold font-rounded"
                        placeholder="1"
                        step="0.1"
                      />
                    </div>
                  </div>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleTonPayment}
                    className="w-full py-2.5 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 font-black text-sm uppercase tracking-widest font-rounded"
                  >
                    ПЕРЕВЕСТИ
                  </motion.button>
                </div>

                {/* Info Box */}
                <div className="p-4 rounded-2xl bg-white/5 border border-white/10 mt-4">
                  <p className="text-white/40 text-[10px] text-center uppercase tracking-widest leading-relaxed">
                    После перевода средства зачислятся автоматически в течение 5-10 минут. 
                    Обязательно подпишитесь на наш канал для получения уведомлений.
                  </p>
                  <motion.button
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={handleChannelLink}
                    className="w-full mt-3 py-2 rounded-xl bg-white/10 text-white text-xs font-bold uppercase tracking-widest flex items-center justify-center gap-2"
                  >
                    Перейти в канал <img src="/asset/Icons/TelegramStar.png" className="w-4 h-4" />
                  </motion.button>
                </div>
              </div>

              <motion.button
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                onClick={() => {
                  setShowTopUp(false);
                  triggerHaptic();
                }}
                className="w-full mt-4 py-3 rounded-xl border border-white/10 text-white/50 font-semibold"
              >
                Отмена
              </motion.button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Subscription Popup */}
      <AnimatePresence>
        {showSubscriptionPopup && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-[100] flex items-center justify-center bg-black/90 backdrop-blur-md p-6"
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              className="w-full max-w-sm glass-panel p-8 text-center relative overflow-hidden"
            >
              {/* Decorative elements */}
              <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-transparent via-blue-500 to-transparent" />
              
              <div className="w-24 h-24 rounded-full bg-blue-500/10 border border-blue-500/20 flex items-center justify-center mx-auto mb-6 relative">
                <img src="/asset/Icons/TelegramStar.png" alt="Telegram" className="w-12 h-12" />
                <motion.div 
                  animate={{ scale: [1, 1.2, 1], opacity: [0.5, 0.8, 0.5] }}
                  transition={{ duration: 2, repeat: Infinity }}
                  className="absolute inset-0 rounded-full bg-blue-400/20 blur-xl"
                />
              </div>

              <h2 className="text-white font-black text-2xl mb-3 font-rounded uppercase tracking-tight">Подписка обязательна</h2>
              <p className="text-white/60 text-sm mb-8 font-rounded leading-relaxed">
                Чтобы продолжить использовать приложение и получать бонусы, подпишитесь на наш официальный канал.
              </p>

              <div className="space-y-3">
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleChannelLink}
                  className="w-full py-4 rounded-2xl bg-white text-black font-black uppercase tracking-widest text-sm shadow-xl shadow-white/10"
                >
                  ПОДПИСАТЬСЯ
                </motion.button>
                
                <motion.button
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  onClick={handleCheckSubscription}
                  className="w-full py-4 rounded-2xl bg-white/5 border border-white/10 text-white font-black uppercase tracking-widest text-sm"
                >
                  Я ПОДПИСАЛСЯ
                </motion.button>
              </div>

              <p className="text-white/20 text-[10px] mt-6 uppercase tracking-[0.2em]">ScreamCase Official</p>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
