import React, { useEffect, useState } from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import CountUp from 'react-countup';
import { useTonConnectUI } from '@tonconnect/ui-react';
import CasesGrid from './components/CasesGrid';
import WheelGame from './components/games/WheelGame';
import UpgradeGame from './components/games/UpgradeGame';
import ProfilePage from './components/ProfilePage';
import { createInvoice, fetchBalance, fetchTasks, notifyTonSuccess, verifyTask } from './api';

const PAGE_BG = '#22242a';
const TON_WALLET = 'UQA312HDuwVR-RtbUD6u05RAXF-ExIHxExeCZP32RciryUrp';

const TABS = {
  cases: 'Кейсы',
  tasks: 'Задания',
  games: 'Игры',
  profile: 'Профиль',
};

const TAB_COLORS = {
  cases: '#ffffff',
  tasks: '#eab308',
  games: '#a855f7',
  profile: '#3b82f6',
};

const LoadingSpinner = () => (
  <div className="flex h-full flex-col items-center justify-center" style={{ backgroundColor: PAGE_BG }}>
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      className="mb-4 h-12 w-12 rounded-full border-4 border-white/10 border-t-white"
    />
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
  const [tasks, setTasks] = useState([]);

  const [inventory, setInventory] = useState(() => {
    const saved = localStorage.getItem('inventory');
    return saved ? JSON.parse(saved) : [];
  });
  const [transactions, setTransactions] = useState(() => {
    const saved = localStorage.getItem('transactions');
    return saved ? JSON.parse(saved) : [];
  });
  const [balance, setBalance] = useState(() => Number(localStorage.getItem('balance') || 0));
  const [tickets, setTickets] = useState(0);
  const [spent, setSpent] = useState(() => Number(localStorage.getItem('spent') || 0));
  const [donor, setDonor] = useState(() => Number(localStorage.getItem('donor') || 0));

  const triggerHaptic = (type = 'light') => {
    const haptic = window.Telegram?.WebApp?.HapticFeedback;
    if (!haptic) return;

    if (type === 'success') {
      haptic.notificationOccurred('success');
      return;
    }

    haptic.impactOccurred(type === 'heavy' ? 'heavy' : 'light');
  };

  const syncBalance = async (userId) => {
    if (!userId) return null;

    try {
      const data = await fetchBalance(userId);
      setBalance(data?.stars || 0);
      setTickets(data?.tickets || 0);
      setDonor(data?.donor || 0);
      setSpent(data?.spent || 0);
      return data;
    } catch (error) {
      console.error('Sync balance error:', error);
      return null;
    }
  };

  const loadTasks = async (userId = user?.id) => {
    if (!userId) return;

    try {
      const data = await fetchTasks(userId);
      setTasks(Array.isArray(data) ? data.filter((task) => task.type?.startsWith('referral_')) : []);
    } catch (error) {
      console.error('Load tasks error:', error);
      setTasks([]);
    }
  };

  useEffect(() => {
    const init = async () => {
      const tg = window.Telegram?.WebApp;

      if (tg) {
        tg.ready();
        tg.expand();

        const userData = tg.initDataUnsafe?.user;
        if (userData) {
          setUser(userData);
          await syncBalance(userData.id);
        }
      }

      setLoading(false);
    };

    init();
  }, []);

  useEffect(() => {
    if (activeTab === 'tasks' || activeTab === 'profile') {
      loadTasks();
    }
  }, [activeTab]);

  useEffect(() => {
    localStorage.setItem('inventory', JSON.stringify(inventory));
    localStorage.setItem('transactions', JSON.stringify(transactions));
    localStorage.setItem('balance', balance.toString());
    localStorage.setItem('spent', spent.toString());
    localStorage.setItem('donor', donor.toString());
  }, [inventory, transactions, balance, spent, donor]);

  const handleStarsPayment = async () => {
    triggerHaptic();
    if (!user?.id) return;

    try {
      const { link } = await createInvoice(user.id, starsAmount);
      window.Telegram?.WebApp?.openTelegramLink(link);
      setShowTopUp(false);
    } catch (error) {
      console.error(error);
      window.Telegram?.WebApp?.showAlert?.('Ошибка при создании инвойса');
    }
  };

  const handleTonPayment = async () => {
    triggerHaptic();
    if (!user?.id) return;

    const amount = parseFloat(tonAmount) || 0.1;
    const transaction = {
      validUntil: Math.floor(Date.now() / 1000) + 600,
      messages: [{ address: TON_WALLET, amount: Math.round(amount * 1000000000).toString() }],
    };

    try {
      const result = await tonConnectUI.sendTransaction(transaction);
      await notifyTonSuccess(user.id, amount, result.boc);
      await syncBalance(user.id);
      setShowTopUp(false);
      triggerHaptic('success');
      window.Telegram?.WebApp?.showAlert?.('Баланс обновлен');
    } catch (error) {
      console.error(error);
      window.Telegram?.WebApp?.showAlert?.('Ошибка или отмена транзакции');
    }
  };

  const handleVerifyTask = async (taskId) => {
    triggerHaptic();
    if (!user?.id) return;

    try {
      const result = await verifyTask(user.id, taskId);
      if (result?.success) {
        setTasks((prev) => prev.filter((task) => task.id !== taskId));
        await syncBalance(user.id);
        triggerHaptic('success');
      }
    } catch (error) {
      console.error(error);
    }
  };

  const handleSpinComplete = (item, caseItem) => {
    if (user?.id) syncBalance(user.id);

    const inventoryItem = {
      id: Date.now(),
      name: item?.name || 'Item',
      image: item?.image || '',
      price: item?.price || 0,
      caseName: caseItem?.name,
    };

    setInventory((prev) => [inventoryItem, ...prev]);
    setTransactions((prev) => [
      {
        id: Date.now(),
        type: 'case_open',
        amount: caseItem?.price || 0,
        description: `Открытие ${caseItem?.name || 'кейса'}`,
        item: item?.name,
      },
      ...prev,
    ]);
  };

  const handleWheelWin = (segment) => {
    if (user?.id) syncBalance(user.id);

    setInventory((prev) => [
      {
        id: Date.now(),
        name: segment?.label || 'Prize',
        image: segment?.image || '',
        price: segment?.price || parseInt(segment?.label, 10) || 0,
      },
      ...prev,
    ]);
  };

  const renderTasks = () => (
    <div className="h-full overflow-y-auto p-6 pb-24" style={{ backgroundColor: PAGE_BG }}>
      <h2 className="mb-6 font-rounded text-2xl font-black uppercase tracking-tight text-white">Задания</h2>

      {!tasks.length ? (
        <div className="glass-panel p-8 text-center">
          <p className="font-rounded text-xs uppercase tracking-widest text-white/30">Все задания выполнены</p>
        </div>
      ) : (
        <div className="space-y-4">
          {tasks.map((task) => (
            <motion.div
              key={task.id}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              className="glass-panel flex items-center justify-between gap-4 p-4"
            >
              <div className="min-w-0 flex-1">
                <h3 className="text-sm font-bold text-white/90">{task.title}</h3>
                <div className="mt-1 flex items-center gap-2">
                  <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Reward" />
                  <span className="text-xs font-bold text-yellow-400">+{task.reward}</span>
                </div>
              </div>

              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={() => handleVerifyTask(task.id)}
                className="glass-button px-4 py-2 text-[10px] font-black uppercase tracking-widest text-white"
              >
                Проверить
              </motion.button>
            </motion.div>
          ))}
        </div>
      )}
    </div>
  );

  const renderGamesHub = () => (
    <div className="h-full overflow-y-auto p-6 pb-24 text-white" style={{ backgroundColor: PAGE_BG }}>
      <h2 className="mb-2 font-rounded text-2xl font-black uppercase tracking-tight">Мини-игры</h2>
      <p className="mb-6 text-xs uppercase tracking-widest text-white/40">Испытай свою удачу</p>

      <div className="grid grid-cols-1 gap-4">
        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => {
            triggerHaptic();
            setActiveGame('wheel');
          }}
          className="relative h-40 overflow-hidden rounded-3xl border border-purple-500/20 text-left"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/20 to-black/20" />
          <div className="relative z-10 flex h-full flex-col justify-between p-6">
            <div>
              <h3 className="font-rounded text-xl font-black uppercase">Колесо Фортуны</h3>
              <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-purple-400">Выигрыш до 500 звезд</p>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-black uppercase text-white/60">Играть</span>
              <img src="/asset/Icons/WheelIcon.png" className="h-12 w-12 opacity-50" alt="" onError={(e) => e.currentTarget.style.display='none'} />
            </div>
          </div>
        </motion.button>

        <motion.button
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => {
            triggerHaptic();
            setActiveGame('upgrade');
          }}
          className="relative h-40 overflow-hidden rounded-3xl border border-green-500/20 text-left"
        >
          <div className="absolute inset-0 bg-gradient-to-br from-green-600/20 to-black/20" />
          <div className="relative z-10 flex h-full flex-col justify-between p-6">
            <div>
              <h3 className="font-rounded text-xl font-black uppercase">Апгрейд</h3>
              <p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-green-400">Улучшай свои предметы</p>
            </div>
            <div className="flex items-center justify-between">
              <span className="text-xs font-black uppercase text-white/60">Играть</span>
              <img src="/asset/Icons/UpgradeIcon.png" className="h-12 w-12 opacity-50" alt="" onError={(e) => e.currentTarget.style.display='none'} />
            </div>
          </div>
        </motion.button>
      </div>
    </div>
  );

  const renderContent = () => {
    if (loading) return <LoadingSpinner />;

    if (activeTab === 'cases') {
      return <CasesGrid user={user} onWin={handleSpinComplete} balance={balance} setBalance={setBalance} setSpent={setSpent} />;
    }

    if (activeTab === 'tasks') return renderTasks();

    if (activeTab === 'games') {
      if (activeGame === 'wheel') {
        return (
          <div className="h-full overflow-y-auto" style={{ backgroundColor: PAGE_BG }}>
            <div className="p-4">
              <button onClick={() => setActiveGame(null)} className="glass-button p-2 text-white/70">Назад</button>
            </div>
            <WheelGame isPage onWin={handleWheelWin} balance={balance} setBalance={setBalance} />
          </div>
        );
      }

      if (activeGame === 'upgrade') {
        return (
          <div className="h-full overflow-y-auto" style={{ backgroundColor: PAGE_BG }}>
            <div className="p-4">
              <button onClick={() => setActiveGame(null)} className="glass-button p-2 text-white/70">Назад</button>
            </div>
            <UpgradeGame
              isPage
              inventory={inventory}
              setInventory={setInventory}
              balance={balance}
              setBalance={setBalance}
              setSpent={setSpent}
            />
          </div>
        );
      }

      return renderGamesHub();
    }

    if (activeTab === 'profile') {
      return (
        <ProfilePage
          isPage
          inventory={inventory}
          setInventory={setInventory}
          transactions={transactions}
          setTransactions={setTransactions}
          balance={balance}
          setBalance={setBalance}
          tickets={tickets}
          spent={spent}
          donor={donor}
          tasks={tasks}
          onVerifyTask={handleVerifyTask}
        />
      );
    }

    return null;
  };

  return (
    <div className="min-h-screen w-full overflow-hidden text-white font-rounded" style={{ backgroundColor: PAGE_BG }}>
      <div className="flex h-screen flex-col" style={{ backgroundColor: PAGE_BG }}>
        <div className="glass-panel border-b border-white/10 px-6 py-4" style={{ backgroundColor: PAGE_BG }}>
          <div className="flex items-center justify-between">
            <div className="flex min-w-0 items-center gap-4">
              <div className="flex h-12 w-12 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-white/5">
                {user?.photo_url ? (
                  <img src={user.photo_url} alt="User" className="h-full w-full object-cover" />
                ) : (
                  <span className="font-bold text-white/30">{user?.first_name?.charAt(0) || 'U'}</span>
                )}
              </div>

              <div className="min-w-0">
                <h1 className="truncate text-lg font-black uppercase leading-tight tracking-tight text-white">
                  {user?.first_name || 'Игрок'}
                </h1>
                <div className="mt-0.5 flex items-center gap-2">
                  <span className="text-[10px] font-bold uppercase tracking-tighter text-white/40">Донор {formatValue(donor)}</span>
                  <span className="text-[10px] font-bold uppercase tracking-tighter text-white/40">Слито {formatValue(spent)}</span>
                </div>
              </div>
            </div>

            <motion.button
              whileTap={{ scale: 0.95 }}
              onClick={() => {
                setShowTopUp(true);
                triggerHaptic();
              }}
              className="glass-button flex items-center gap-2 border-yellow-500/30 bg-yellow-500/5 px-4 py-2"
            >
              <img src="/asset/Icons/TelegramStar.png" alt="Stars" className="h-6 w-6" />
              <span className="text-lg font-black text-yellow-400"><CountUp end={balance} duration={0.5} /></span>
              <span className="text-xs font-bold text-yellow-400/50">+</span>
            </motion.button>
          </div>
        </div>

        <div className="relative flex-1 overflow-hidden" style={{ backgroundColor: PAGE_BG }}>
          {renderContent()}
        </div>

        <div className="glass-panel safe-area-inset-bottom border-t border-white/10 px-4 py-2" style={{ backgroundColor: PAGE_BG }}>
          <div className="flex h-16 items-center justify-around">
            {Object.entries(TABS).map(([key, label]) => {
              const isActive = activeTab === key;

              return (
                <motion.button
                  key={key}
                  className="relative z-10 flex h-12 w-16 flex-col items-center justify-center"
                  onClick={() => {
                    setActiveTab(key);
                    setActiveGame(null);
                    triggerHaptic();
                  }}
                  whileTap={{ scale: 0.9 }}
                >
                  {isActive && (
                    <motion.div
                      layoutId="activeTabPill"
                      className="absolute inset-[-4px] z-0 rounded-2xl border border-white/10 bg-white/5"
                    />
                  )}

                  <div className="z-10 mb-0.5" style={{ color: isActive ? TAB_COLORS[key] : 'rgba(255,255,255,0.3)' }}>
                    {key === 'cases' && (
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <rect x="3" y="3" width="7" height="7" rx="1" />
                        <rect x="14" y="3" width="7" height="7" rx="1" />
                        <rect x="14" y="14" width="7" height="7" rx="1" />
                        <rect x="3" y="14" width="7" height="7" rx="1" />
                      </svg>
                    )}
                    {key === 'tasks' && (
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M9 11l3 3L22 4" />
                        <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11" />
                      </svg>
                    )}
                    {key === 'games' && (
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <circle cx="12" cy="12" r="10" />
                        <path d="M12 6v6l4 2" />
                      </svg>
                    )}
                    {key === 'profile' && (
                      <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                        <path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2" />
                        <circle cx="12" cy="7" r="4" />
                      </svg>
                    )}
                  </div>

                  <span className={`z-10 text-[9px] font-bold uppercase tracking-tighter ${isActive ? 'text-white' : 'text-white/30'}`}>
                    {label}
                  </span>
                </motion.button>
              );
            })}
          </div>
        </div>
      </div>

      <AnimatePresence>
        {showTopUp && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-end justify-center bg-black/80 p-0 backdrop-blur-sm"
            onClick={() => setShowTopUp(false)}
          >
            <motion.div
              initial={{ y: '100%' }}
              animate={{ y: 0 }}
              exit={{ y: '100%' }}
              onClick={(event) => event.stopPropagation()}
              className="glass-panel w-full max-w-md rounded-t-3xl border-t border-white/20 p-6 pb-8"
              style={{ backgroundColor: PAGE_BG }}
            >
              <div className="mx-auto mb-6 h-1 w-12 rounded-full bg-white/20" />
              <h2 className="mb-6 text-center text-xl font-black uppercase">Пополнение</h2>

              <div className="space-y-4">
                <div className="glass-panel space-y-3 p-4">
                  <div className="flex items-center gap-4">
                    <img src="/asset/Icons/TelegramStar.png" alt="Stars" className="h-10 w-10" />
                    <p className="flex-1 text-sm font-bold">Stars</p>
                    <input
                      type="number"
                      value={starsAmount}
                      onChange={(event) => setStarsAmount(event.target.value)}
                      className="w-20 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-right font-bold text-yellow-400"
                    />
                  </div>
                  <motion.button
                    whileTap={{ scale: 0.98 }}
                    onClick={handleStarsPayment}
                    className="w-full rounded-xl border border-yellow-500/20 bg-yellow-500/10 py-3 text-xs font-black uppercase tracking-widest text-yellow-500"
                  >
                    Пополнить
                  </motion.button>
                </div>

                <div className="glass-panel space-y-3 border-blue-500/20 bg-blue-500/5 p-4">
                  <div className="flex items-center gap-4">
                    <img src="/asset/Icons/TonCoin.png" alt="TON" className="h-10 w-10" />
                    <p className="flex-1 text-sm font-bold">TON Crystal</p>
                    <input
                      type="number"
                      value={tonAmount}
                      onChange={(event) => setTonAmount(event.target.value)}
                      className="w-20 rounded-lg border border-white/10 bg-white/5 px-2 py-1 text-right font-bold text-blue-400"
                    />
                  </div>
                  <motion.button
                    whileTap={{ scale: 0.98 }}
                    onClick={handleTonPayment}
                    className="w-full rounded-xl border border-blue-500/20 bg-blue-500/10 py-3 text-xs font-black uppercase tracking-widest text-blue-400"
                  >
                    Перевести
                  </motion.button>
                </div>
              </div>

              <motion.button
                whileTap={{ scale: 0.98 }}
                onClick={() => setShowTopUp(false)}
                className="mt-4 w-full py-3 text-[10px] font-bold uppercase tracking-widest text-white/40"
              >
                Отмена
              </motion.button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
