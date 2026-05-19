import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CountUp from 'react-countup';
import CasesGrid from './components/CasesGrid';
import WheelGame from './components/games/WheelGame';
import UpgradeGame from './components/games/UpgradeGame';
import ProfilePage from './components/ProfilePage';
import { useTonConnectUI } from '@tonconnect/ui-react';
import { fetchBalance, createInvoice, notifyTonSuccess, checkSubscription, fetchTasks, verifyTask } from './api';

const LoadingSpinner = () => (
  <div className="flex flex-col items-center justify-center h-full">
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      className="w-12 h-12 border-4 border-white/10 border-t-white rounded-full mb-4"
    />
    <p className="text-white/50 font-rounded animate-pulse uppercase tracking-widest text-xs">Loading...</p>
  </div>
);

const TABS = {
  cases: 'Кейсы',
  tasks: 'Задания',
  games: 'Игры',
  profile: 'Профиль',
};

const ADMIN_IDS = [7782281997, 5396975347];
const CHANNEL_LINK = 'https://t.me/ScreamCase';
const TON_WALLET = 'UQA312HDuwVR-RtbUD6u05RAXF-ExIHxExeCZP32RciryUrp';

const formatValue = (val) => {
  if (val === undefined || val === null) return '0';
  if (val >= 1000) return (val / 1000).toFixed(1).replace('.0', '') + 'k';
  return val.toString();
};

const TAB_COLORS = {
  cases: { bubble: 'rgba(255, 255, 255, 0.15)', icon: '#ffffff' },
  tasks: { bubble: 'rgba(234, 179, 8, 0.15)', icon: '#eab308' },
  games: { bubble: 'rgba(168, 85, 247, 0.15)', icon: '#a855f7' },
  profile: { bubble: 'rgba(59, 130, 246, 0.15)', icon: '#3b82f6' },
};

export default function App() {
  const [activeTab, setActiveTab] = useState('cases');
  const [activeGame, setActiveGame] = useState(null); // null, 'wheel', 'upgrade'
  const [showTopUp, setShowTopUp] = useState(false);
  const [starsAmount, setStarsAmount] = useState('100');
  const [tonAmount, setTonAmount] = useState('0.1');
  const [tonConnectUI] = useTonConnectUI();
  const [showSubscriptionPopup, setShowSubscriptionPopup] = useState(false);
  const [isSubscribed, setIsSubscribed] = useState(true);
  const [tasks, setTasks] = useState([]);
  const [user, setUser] = useState(null);
  const [isAdmin, setIsAdmin] = useState(false);
  const [loading, setLoading] = useState(true);

  // Stats from DB/Local
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
  const [tickets, setTickets] = useState(0);
  const [spent, setSpent] = useState(() => {
    const saved = localStorage.getItem('spent');
    return saved ? parseInt(saved) : 0;
  });
  const [donor, setDonor] = useState(() => {
    const saved = localStorage.getItem('donor');
    return saved ? parseInt(saved) : 0;
  });

  const triggerHaptic = (type = 'light') => {
    if (window.Telegram?.WebApp?.HapticFeedback) {
      if (type === 'success') {
        window.Telegram.WebApp.HapticFeedback.notificationOccurred('success');
      } else {
        window.Telegram.WebApp.HapticFeedback.impactOccurred(type === 'heavy' ? 'heavy' : 'light');
      }
    }
  };

  const handleChannelLink = () => {
    triggerHaptic();
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.openTelegramLink(CHANNEL_LINK);
    } else {
      window.open(CHANNEL_LINK, '_blank');
    }
  };

  const syncBalance = async (userId) => {
    if (!userId) return;
    try {
      const data = await fetchBalance(userId);
      setBalance(data?.stars || 0);
      setTickets(data?.tickets || 0);
      setDonor(data?.donor || 0);
      setSpent(data?.spent || 0);
      return data;
    } catch (e) {
      console.error('Sync balance error:', e);
    }
  };

  const loadTasks = async () => {
    if (!user?.id) return;
    try {
      const data = await fetchTasks(user.id);
      setTasks(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error('Load tasks error:', e);
      setTasks([]);
    }
  };

  // Persist state
  React.useEffect(() => {
    localStorage.setItem('inventory', JSON.stringify(inventory));
    localStorage.setItem('transactions', JSON.stringify(transactions));
    localStorage.setItem('balance', balance.toString());
    localStorage.setItem('spent', spent.toString());
    localStorage.setItem('donor', donor.toString());
  }, [inventory, transactions, balance, spent, donor]);

  // Init
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
          
          const sub = await checkSubscription(userData.id);
          setIsSubscribed(sub);
          if (!sub) setShowSubscriptionPopup(true);
        }
      }
      setLoading(false);
    };
    init();
  }, []);

  React.useEffect(() => {
    if (activeTab === 'tasks') {
      loadTasks();
    }
  }, [activeTab]);

  const handleCheckSubscription = async () => {
    triggerHaptic();
    if (!user?.id) return;
    const sub = await checkSubscription(user.id);
    if (sub) {
      setIsSubscribed(true);
      setShowSubscriptionPopup(false);
      triggerHaptic('success');
    } else {
      window.Telegram?.WebApp?.showAlert?.("Вы ещё не подписались на канал @ScreamCase!");
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
      window.Telegram?.WebApp?.showAlert?.("Ошибка при создании инвойса");
    }
  };

  const handleTonPayment = async () => {
    triggerHaptic();
    if (!user?.id) return;
    const amount = parseFloat(tonAmount) || 0.1;
    const nanotons = (amount * 1000000000).toString();
    const transaction = {
      validUntil: Math.floor(Date.now() / 1000) + 600,
      messages: [{ address: TON_WALLET, amount: nanotons }],
    };

    try {
      const result = await tonConnectUI.sendTransaction(transaction);
      triggerHaptic('success');
      setShowTopUp(false);
      await notifyTonSuccess(user.id, amount, result.boc);
      await syncBalance(user.id);
      window.Telegram?.WebApp?.showAlert?.("Транзакция отправлена и баланс обновлен!");
    } catch (e) {
      console.error(e);
      window.Telegram?.WebApp?.showAlert?.("Ошибка или отмена транзакции");
    }
  };

  const handleVerifyTask = async (taskId) => {
    triggerHaptic();
    if (!user?.id) return;
    try {
      const res = await verifyTask(user.id, taskId);
      if (res?.success) {
        triggerHaptic('success');
        setTasks(prev => prev.filter(t => t.id !== taskId));
        await syncBalance(user.id);
      }
    } catch (e) {
      console.error(e);
    }
  };

  const handleSpinComplete = (item, caseItem) => {
    if (user?.id) syncBalance(user.id);
    
    const newItem = {
      id: Date.now(),
      name: item?.name || 'Item',
      image: item?.image || '',
      price: item?.price || 0,
      caseName: caseItem?.name
    };
    setInventory(prev => [newItem, ...prev]);
    
    const newTransaction = {
      id: Date.now(),
      type: 'case_open',
      amount: caseItem?.price || 0,
      description: `Открытие ${caseItem?.name || 'кейса'}`,
      item: item?.name
    };
    setTransactions(prev => [newTransaction, ...prev]);
  };

  const handleWheelWin = (segment) => {
    if (user?.id) syncBalance(user.id);
    const newItem = {
      id: Date.now(),
      name: segment?.label || 'Prize',
      image: segment?.image || '',
      price: segment?.price || parseInt(segment?.label) || 0,
    };
    setInventory(prev => [newItem, ...prev]);
    const newTransaction = {
      id: Date.now(),
      type: 'win',
      amount: 50,
      description: 'Колесо Фортуны',
      item: segment?.label,
    };
    setTransactions(prev => [newTransaction, ...prev]);
  };

  const renderGamesHub = () => (
    <div className="p-6 space-y-6 pb-24 h-full overflow-y-auto">
      <h2 className="text-2xl font-black font-rounded uppercase tracking-tight mb-2">Мини-Игры</h2>
      <p className="text-white/40 text-xs uppercase tracking-widest mb-6">Испытай свою удачу</p>
      
      <div className="grid grid-cols-1 gap-4">
        {/* Wheel of Fortune Card */}
        <motion.div
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => { triggerHaptic(); setActiveGame('wheel'); }}
          className="relative overflow-hidden rounded-3xl h-40 group cursor-pointer border border-purple-500/20"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/20 to-black z-0" />
          <div className="relative z-10 p-6 flex flex-col justify-between h-full">
            <div>
              <h3 className="text-xl font-black font-rounded uppercase italic">Колесо Фортуны</h3>
              <p className="text-purple-400 text-[10px] font-bold uppercase tracking-widest mt-1">Шанс выиграть до 500 ⭐</p>
            </div>
            <div className="flex items-center gap-2 text-white/60 font-black text-xs uppercase">
              Играть <span className="text-lg">→</span>
            </div>
          </div>
          <div className="absolute -right-4 -bottom-4 opacity-20 group-hover:opacity-40 transition-opacity">
             <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="text-purple-500 animate-spin">
                <circle cx="12" cy="12" r="10" />
                <path d="M12 2v20M2 12h20M5.6 5.6l12.8 12.8M5.6 18.4L18.4 5.6" />
             </svg>
          </div>
        </motion.div>

        {/* Upgrade Card */}
        <motion.div
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => { triggerHaptic(); setActiveGame('upgrade'); }}
          className="relative overflow-hidden rounded-3xl h-40 group cursor-pointer border border-green-500/20"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-green-600/20 to-black z-0" />
          <div className="relative z-10 p-6 flex flex-col justify-between h-full">
            <div>
              <h3 className="text-xl font-black font-rounded uppercase italic">Апгрейд</h3>
              <p className="text-green-400 text-[10px] font-bold uppercase tracking-widest mt-1">Улучшай свои предметы</p>
            </div>
            <div className="flex items-center gap-2 text-white/60 font-black text-xs uppercase">
              Играть <span className="text-lg">→</span>
            </div>
          </div>
          <div className="absolute -right-4 -bottom-4 opacity-20 group-hover:opacity-40 transition-opacity">
             <svg width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" className="text-green-500">
                <path d="M12 3v18M3 12h18M8 8l-4 4 4 4M16 8l4 4-4 4" />
             </svg>
          </div>
        </motion.div>
      </div>
    </div>
  );

  const renderContent = () => {
    if (loading) return <LoadingSpinner />;
    
    switch (activeTab) {
      case 'cases':
        return <CasesGrid user={user} onWin={handleSpinComplete} balance={balance} setBalance={setBalance} setSpent={setSpent} />;
      case 'tasks':
        return (
          <div className="p-6 space-y-4 pb-24 h-full overflow-y-auto">
            <h2 className="text-2xl font-black font-rounded uppercase tracking-tight mb-6">Задания</h2>
            {!tasks || tasks.length === 0 ? (
              <div className="glass-panel p-8 text-center">
                <p className="text-white/30 font-rounded uppercase tracking-widest text-xs">Все задания выполнены!</p>
              </div>
            ) : (
              tasks.map(task => (
                <motion.div key={task.id} initial={{ opacity: 0, x: -20 }} animate={{ opacity: 1, x: 0 }} className="glass-panel p-4 flex items-center justify-between gap-4">
                  <div className="flex-1">
                    <h3 className="font-bold text-sm text-white/90">{task?.title}</h3>
                    <div className="flex items-center gap-2 mt-1">
                      <img src="/asset/Icons/TelegramStar.png" className="w-4 h-4" alt="Reward" />
                      <span className="text-yellow-400 font-bold text-xs">+{task?.reward}</span>
                    </div>
                  </div>
                  <div className="flex items-center gap-2">
                    {task?.url && (
                      <motion.button whileTap={{ scale: 0.95 }} onClick={() => { triggerHaptic(); window.Telegram?.WebApp?.openTelegramLink(task.url); }} className="glass-button p-2 border-white/10">
                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6M15 3h6v6M10 14L21 3" /></svg>
                      </motion.button>
                    )}
                    <motion.button whileTap={{ scale: 0.95 }} onClick={() => handleVerifyTask(task.id)} className="glass-button px-4 py-2 bg-white/5 border-white/20 text-[10px] font-black uppercase tracking-widest">ПРОВЕРИТЬ</motion.button>
                  </div>
                </motion.div>
              ))
            )}
          </div>
        );
      case 'games':
        return (
          <div className="flex flex-col h-full relative">
            <AnimatePresence mode="wait">
              {!activeGame ? (
                <motion.div
                  key="hub"
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, x: -100 }}
                  className="h-full"
                >
                  {renderGamesHub()}
                </motion.div>
              ) : (
                <motion.div
                  key="game"
                  initial={{ opacity: 0, x: 100 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: 100 }}
                  className="flex-1 h-full overflow-y-auto"
                >
                  <div className="p-4 flex items-center gap-3">
                    <motion.button
                      whileTap={{ scale: 0.9 }}
                      onClick={() => { triggerHaptic(); setActiveGame(null); }}
                      className="glass-button p-2 text-white/50"
                    >
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
                        <path d="M19 12H5M12 19l-7-7 7-7" />
                      </svg>
                    </motion.button>
                    <span className="text-xs font-black uppercase tracking-widest text-white/30">Назад в хаб</span>
                  </div>
                  {activeGame === 'wheel' && (
                    <WheelGame 
                      isPage={true} 
                      onWin={handleWheelWin} 
                      balance={balance} 
                      setBalance={setBalance} 
                    />
                  )}
                  {activeGame === 'upgrade' && (
                    <UpgradeGame 
                      isPage={true} 
                      inventory={inventory} 
                      setInventory={setInventory} 
                      balance={balance} 
                      setBalance={setBalance} 
                      setSpent={setSpent} 
                    />
                  )}
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        );
      case 'profile':
        return (
          <div className="flex flex-col h-full overflow-y-auto">
            <ProfilePage isPage={true} inventory={inventory} setInventory={setInventory} transactions={transactions} setTransactions={setTransactions} balance={balance} setBalance={setBalance} tickets={tickets} spent={spent} donor={donor} />
            {isAdmin && (
              <div className="p-6 pb-24">
                <div className="glass-panel p-4 border-red-500/20 bg-red-500/5">
                  <h3 className="text-red-400 font-bold text-sm mb-4 uppercase tracking-widest flex items-center gap-2"><span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />Admin Manager</h3>
                  <motion.button whileTap={{ scale: 0.95 }} onClick={() => { triggerHaptic('heavy'); localStorage.clear(); window.location.reload(); }} className="glass-button w-full py-3 text-[10px] font-black uppercase tracking-tighter border-white/20 text-white/50">Reset Local Cache</motion.button>
                </div>
              </div>
            )}
          </div>
        );
      default:
        return null;
    }
  };

  return (
    <div className="min-h-screen w-full bg-black text-white overflow-hidden font-rounded">
      {/* Background */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <motion.div className="absolute top-0 left-1/4 w-96 h-96 rounded-full bg-white/5 blur-3xl" animate={{ opacity: [0.1, 0.3, 0.1], scale: [0.8, 1.2, 0.8] }} transition={{ duration: 8, repeat: Infinity }} />
        <motion.div className="absolute bottom-0 right-1/4 w-96 h-96 rounded-full bg-white/5 blur-3xl" animate={{ opacity: [0.1, 0.3, 0.1], scale: [1.2, 0.8, 1.2] }} transition={{ duration: 8, repeat: Infinity, delay: 1 }} />
      </div>

      <div className="relative z-10 flex flex-col h-screen">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="glass-panel border-b border-white/10 px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="w-12 h-12 rounded-full border border-white/10 bg-white/5 flex items-center justify-center overflow-hidden">
                {user?.photo_url ? (
                  <img src={user.photo_url} alt="User" className="w-full h-full object-cover" />
                ) : (
                  <div className="w-full h-full flex items-center justify-center text-white/30 font-bold">{user?.first_name?.charAt(0) || 'U'}</div>
                )}
              </div>
              <div>
                <h1 className="text-white font-black text-lg leading-tight uppercase tracking-tight">{user?.first_name || 'ИГРОК'} {isAdmin && <span className="text-[8px] bg-green-500/20 text-green-400 px-1 py-0.5 rounded ml-1 border border-green-500/30">ADMIN</span>}</h1>
                <div className="flex items-center gap-2 mt-0.5">
                    <span className="text-[10px] font-bold text-white/40 uppercase tracking-tighter">🏆 {formatValue(donor)}</span>
                    <span className="text-[10px] font-bold text-white/40 uppercase tracking-tighter">💸 {formatValue(spent)}</span>
                </div>
              </div>
            </div>
            <motion.button whileTap={{ scale: 0.95 }} onClick={() => { setShowTopUp(true); triggerHaptic(); }} className="glass-button flex items-center gap-2 px-4 py-2 border-yellow-500/30 bg-yellow-500/5">
              <img src="/asset/Icons/TelegramStar.png" alt="Stars" className="w-6 h-6" />
              <span className="text-yellow-400 font-black text-lg"><CountUp end={balance} duration={0.5} /></span>
              <span className="text-yellow-400/50 text-xs font-bold">+</span>
            </motion.button>
          </div>
        </motion.div>

        {/* Content */}
        <div className="flex-1 overflow-hidden relative">
          {renderContent()}
        </div>

        {/* Navigation */}
        <div className="glass-panel border-t border-white/10 px-4 py-2 safe-area-inset-bottom">
          <div className="flex justify-around items-center h-16">
            {Object.entries(TABS).map(([key, label]) => {
              const isActive = activeTab === key;
              const tabColor = TAB_COLORS[key];
              return (
                <motion.button key={key} className="relative w-16 h-12 flex flex-col items-center justify-center z-10" onClick={() => { setActiveTab(key); setActiveGame(null); triggerHaptic(); }} whileTap={{ scale: 0.9 }}>
                  {isActive && (
                    <motion.div layoutId="activeTabPill" className="absolute inset-[-4px] rounded-2xl z-0" style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', backdropFilter: 'blur(8px)', border: '1px solid rgba(255, 255, 255, 0.1)' }} />
                  )}
                  <div style={{ color: isActive ? tabColor.icon : 'rgba(255,255,255,0.3)' }} className="mb-0.5">
                    {key === 'cases' && <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /></svg>}
                    {key === 'tasks' && <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M9 11l3 3L22 4" /><path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" /></svg>}
                    {key === 'games' && <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><circle cx="12" cy="12" r="10" /><path d="M12 6v6l4 2" /></svg>}
                    {key === 'profile' && <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>}
                  </div>
                  <span className={`text-[9px] font-bold uppercase tracking-tighter ${isActive ? 'text-white' : 'text-white/30'}`}>{label}</span>
                </motion.button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Top-Up Modal */}
      <AnimatePresence>
        {showTopUp && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-end justify-center bg-black/80 backdrop-blur-sm" onClick={() => setShowTopUp(false)}>
            <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} onClick={(e) => e.stopPropagation()} className="w-full max-w-md glass-panel rounded-t-3xl p-6 pb-8 border-t border-white/20">
              <div className="w-12 h-1 bg-white/20 rounded-full mx-auto mb-6" />
              <h2 className="text-xl font-black text-center uppercase mb-6">Пополнение</h2>
              <div className="space-y-4">
                <div className="glass-panel p-4 space-y-3">
                  <div className="flex items-center gap-4">
                    <img src="/asset/Icons/TelegramStar.png" alt="Stars" className="w-10 h-10" />
                    <div className="flex-1"><p className="font-bold text-sm">Stars</p></div>
                    <input type="number" value={starsAmount} onChange={(e) => setStarsAmount(e.target.value)} className="w-20 bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-right text-yellow-400 font-bold" />
                  </div>
                  <motion.button whileTap={{ scale: 0.98 }} onClick={handleStarsPayment} className="w-full py-3 rounded-xl bg-yellow-500/10 border border-yellow-500/20 text-yellow-500 font-black uppercase text-xs tracking-widest">ПОПОЛНИТЬ</motion.button>
                </div>
                <div className="glass-panel p-4 space-y-3 border-blue-500/20 bg-blue-500/5">
                  <div className="flex items-center gap-4">
                    <img src="/asset/Icons/TonCoin.png" alt="TON" className="w-10 h-10" />
                    <div className="flex-1"><p className="font-bold text-sm">TON Crystal</p></div>
                    <input type="number" value={tonAmount} onChange={(e) => setTonAmount(e.target.value)} className="w-20 bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-right text-blue-400 font-bold" />
                  </div>
                  <motion.button whileTap={{ scale: 0.98 }} onClick={handleTonPayment} className="w-full py-3 rounded-xl bg-blue-500/10 border border-blue-500/20 text-blue-400 font-black uppercase text-xs tracking-widest">ПЕРЕВЕСТИ</motion.button>
                </div>
              </div>
              <motion.button whileTap={{ scale: 0.98 }} onClick={() => setShowTopUp(false)} className="w-full mt-4 py-3 text-white/40 font-bold uppercase text-[10px] tracking-widest">Отмена</motion.button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Subscription Modal */}
      <AnimatePresence>
        {showSubscriptionPopup && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="fixed inset-0 z-[100] flex items-center justify-center bg-black/95 backdrop-blur-xl p-6 text-center">
            <div className="w-full max-w-sm glass-panel p-8">
              <div className="w-20 h-20 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-6"><img src="/asset/Icons/TelegramStar.png" alt="Star" className="w-10 h-10" /></div>
              <h2 className="text-2xl font-black uppercase mb-4">Подписка обязательна</h2>
              <p className="text-white/50 text-sm mb-8">Для использования приложения подпишитесь на наш официальный канал.</p>
              <div className="space-y-3">
                <motion.button whileTap={{ scale: 0.98 }} onClick={handleChannelLink} className="w-full py-4 rounded-2xl bg-white text-black font-black uppercase tracking-widest text-sm">ПОДПИСАТЬСЯ</motion.button>
                <motion.button whileTap={{ scale: 0.98 }} onClick={handleCheckSubscription} className="w-full py-4 rounded-2xl bg-white/5 border border-white/10 text-white font-black uppercase tracking-widest text-sm">Я ПОДПИСАЛСЯ</motion.button>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
