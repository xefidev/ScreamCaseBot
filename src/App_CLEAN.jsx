import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import CasesGrid from './components/CasesGrid';
import WheelGame from './components/games/WheelGame';
import UpgradeGame from './components/games/UpgradeGame';
import ProfilePage from './components/ProfilePage';
import { useTonConnectUI } from '@tonconnect/ui-react';
import { fetchBalance, createInvoice, notifyTonSuccess } from './api';

const LoadingSpinner = () => (
  <div className="flex flex-col items-center justify-center h-full">
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
      className="w-12 h-12 border-4 border-white/10 border-t-white rounded-full mb-4"
    />
    <p className="text-white/50 font-rounded animate-pulse uppercase tracking-widest text-xs">Загрузка...</p>
  </div>
);

const TABS = {
  cases: '🎁 КЕЙСЫ',
  games: '🎮 ИГРЫ',
  profile: '👤 ПРОФИЛЬ',
};

const CHANNEL_LINK = 'https://t.me/ScreamCase';
const TON_WALLET = 'UQA312HDuwVR-RtbUD6u05RAXF-ExIHxExeCZP32RciryUrp';

const TAB_COLORS = {
  cases: { bubble: 'rgba(255, 255, 255, 0.15)', icon: '#ffffff' },
  games: { bubble: 'rgba(168, 85, 247, 0.15)', icon: '#a855f7' },
  profile: { bubble: 'rgba(59, 130, 246, 0.15)', icon: '#3b82f6' },
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

  const [inventory, setInventory] = useState(() => {
    const saved = localStorage.getItem('inventory');
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
    try {
      const data = await fetchBalance(userId);
      setBalance(data?.stars || 0);
      setDonor(data?.donor || 0);
      setSpent(data?.spent || 0);
      return data;
    } catch (e) {
      console.error('Sync balance error:', e);
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
          await syncBalance(userData.id);
        }
      }
      setLoading(false);
    };
    init();
  }, []);

  // Persist state
  React.useEffect(() => {
    localStorage.setItem('inventory', JSON.stringify(inventory));
    localStorage.setItem('balance', balance.toString());
    localStorage.setItem('spent', spent.toString());
    localStorage.setItem('donor', donor.toString());
  }, [inventory, balance, spent, donor]);

  const handleChannelLink = () => {
    triggerHaptic();
    if (window.Telegram?.WebApp) {
      window.Telegram.WebApp.openTelegramLink(CHANNEL_LINK);
    } else {
      window.open(CHANNEL_LINK, '_blank');
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
      window.Telegram?.WebApp?.showAlert?.("❌ Ошибка при создании инвойса");
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
      window.Telegram?.WebApp?.showAlert?.("✅ Пополнение успешно!");
    } catch (e) {
      console.error(e);
      window.Telegram?.WebApp?.showAlert?.("❌ Ошибка или отмена транзакции");
    }
  };

  const handleSpinComplete = (item, caseItem) => {
    if (user?.id) syncBalance(user.id);

    const newItem = {
      id: Date.now(),
      name: item?.name || 'Item',
      image: `/asset/Gifts/${item?.image || 'default.webp'}`,
      price: item?.price || 0,
      caseName: caseItem?.name
    };
    setInventory(prev => [newItem, ...prev]);

    setSpent(prev => prev + (caseItem?.price || 0));
  };

  const handleWheelWin = (segment) => {
    if (user?.id) syncBalance(user.id);
    const newItem = {
      id: Date.now(),
      name: segment?.label || 'Prize',
      image: `/asset/Gifts/${segment?.image || 'default.webp'}`,
      price: segment?.price || parseInt(segment?.label) || 0,
    };
    setInventory(prev => [newItem, ...prev]);
  };

  const renderGamesHub = () => (
    <div className="p-6 space-y-6 pb-24 h-full overflow-y-auto" style={{ backgroundColor: '#22242a' }}>
      <h2 className="text-3xl font-black font-rounded uppercase tracking-tight">🎮 МИНИ-ИГРЫ</h2>
      <p className="text-white/40 text-xs uppercase tracking-widest">Испытай свою удачу</p>

      <div className="grid grid-cols-1 gap-4">
        {/* Wheel of Fortune */}
        <motion.div
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => { triggerHaptic(); setActiveGame('wheel'); }}
          className="relative overflow-hidden rounded-3xl h-40 group cursor-pointer border border-purple-500/20 transition-all"
          style={{ backgroundColor: 'rgba(34, 36, 42, 0.5)' }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-purple-600/10 to-black z-0" />
          <div className="relative z-10 p-6 flex flex-col justify-between h-full">
            <div>
              <h3 className="text-2xl font-black uppercase">🎡 Колесо</h3>
              <p className="text-purple-400 text-xs font-bold uppercase tracking-widest mt-2">Выигрыш до 500 ⭐</p>
            </div>
            <div className="flex items-center gap-2 text-white/60 font-black text-sm uppercase">
              Играть →
            </div>
          </div>
        </motion.div>

        {/* Upgrade Game */}
        <motion.div
          whileHover={{ scale: 1.02 }}
          whileTap={{ scale: 0.98 }}
          onClick={() => { triggerHaptic(); setActiveGame('upgrade'); }}
          className="relative overflow-hidden rounded-3xl h-40 group cursor-pointer border border-green-500/20 transition-all"
          style={{ backgroundColor: 'rgba(34, 36, 42, 0.5)' }}
        >
          <div className="absolute inset-0 bg-gradient-to-br from-green-600/10 to-black z-0" />
          <div className="relative z-10 p-6 flex flex-col justify-between h-full">
            <div>
              <h3 className="text-2xl font-black uppercase">⬆️ Улучшай</h3>
              <p className="text-green-400 text-xs font-bold uppercase tracking-widest mt-2">Получи призы</p>
            </div>
            <div className="flex items-center gap-2 text-white/60 font-black text-sm uppercase">
              Играть →
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );

  if (loading) return <LoadingSpinner />;

  return (
    <div className="relative w-full h-screen overflow-hidden" style={{ backgroundColor: '#22242a' }}>
      <AnimatePresence>
        {/* Main Content */}
        {activeGame === null && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="w-full h-full flex flex-col"
          >
            {/* Header */}
            <div className="sticky top-0 z-50 p-4 flex items-center justify-between border-b" style={{ backgroundColor: '#22242a', borderColor: 'rgba(255, 255, 255, 0.1)' }}>
              <div className="flex items-center gap-3">
                <div className="w-12 h-12 rounded-full border-2 border-white/20 flex items-center justify-center bg-white/5 overflow-hidden text-sm font-bold">
                  {user?.first_name?.charAt(0) || '?'}
                </div>
                <div>
                  <p className="text-white font-black text-sm">{user?.first_name || 'Player'}</p>
                  <div className="flex items-center gap-2 mt-0.5">
                    <span className="flex items-center gap-1 px-2 py-0.5 rounded bg-white/10 text-white font-black text-xs">
                      {balance} <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3" alt="⭐" />
                    </span>
                  </div>
                </div>
              </div>
              <motion.button
                whileTap={{ scale: 0.95 }}
                onClick={() => setShowTopUp(true)}
                className="px-4 py-2 rounded-lg font-black text-xs uppercase transition-all"
                style={{ backgroundColor: 'white', color: '#22242a' }}
              >
                + ПОПОЛНИТЬ
              </motion.button>
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto">
              {activeTab === 'cases' && <CasesGrid user={user} onSpinComplete={handleSpinComplete} onClose={() => {}} />}
              {activeTab === 'games' && renderGamesHub()}
              {activeTab === 'profile' && (
                <ProfilePage
                  isPage={true}
                  inventory={inventory}
                  setInventory={setInventory}
                  balance={balance}
                  setBalance={setBalance}
                  spent={spent}
                  donor={donor}
                />
              )}
            </div>

            {/* Bottom Navigation */}
            <div className="sticky bottom-0 z-50 grid grid-cols-3 gap-2 p-4 border-t" style={{ backgroundColor: '#22242a', borderColor: 'rgba(255, 255, 255, 0.1)' }}>
              {Object.entries(TABS).map(([key, label]) => (
                <motion.button
                  key={key}
                  whileTap={{ scale: 0.95 }}
                  onClick={() => { triggerHaptic(); setActiveTab(key); }}
                  className={`py-3 rounded-2xl font-black uppercase text-xs transition-all ${
                    activeTab === key
                      ? 'text-black'
                      : 'text-white/70 hover:text-white'
                  }`}
                  style={{
                    backgroundColor: activeTab === key ? 'white' : 'transparent',
                    border: activeTab === key ? 'none' : '1px solid rgba(255, 255, 255, 0.2)'
                  }}
                >
                  {label}
                </motion.button>
              ))}
            </div>
          </motion.div>
        )}

        {/* Game Views */}
        {activeGame === 'wheel' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 z-40"
            style={{ backgroundColor: '#22242a' }}
          >
            <WheelGame
              user={user}
              onWin={handleWheelWin}
              onClose={() => setActiveGame(null)}
            />
          </motion.div>
        )}

        {activeGame === 'upgrade' && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2 }}
            className="absolute inset-0 z-40"
            style={{ backgroundColor: '#22242a' }}
          >
            <UpgradeGame
              user={user}
              onClose={() => setActiveGame(null)}
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Top-Up Modal */}
      <AnimatePresence>
        {showTopUp && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 backdrop-blur-sm"
            style={{ backgroundColor: 'rgba(0, 0, 0, 0.7)' }}
            onClick={() => setShowTopUp(false)}
          >
            <motion.div
              initial={{ scale: 0.9, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.9, opacity: 0 }}
              className="rounded-3xl p-8 w-full max-w-sm max-h-[90vh] overflow-y-auto"
              style={{ backgroundColor: '#22242a' }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center justify-between mb-6">
                <h2 className="text-2xl font-black text-white uppercase">ПОПОЛНИТЬ</h2>
                <button
                  onClick={() => setShowTopUp(false)}
                  className="text-white/50 hover:text-white text-2xl transition-colors"
                >
                  ✕
                </button>
              </div>

              {/* Stars Tab */}
              <div className="mb-6">
                <h3 className="text-white font-black text-sm uppercase mb-4">📱 ЧЕРЕЗ ТЕЛЕГРАМ</h3>
                <div className="space-y-3">
                  <input
                    type="number"
                    value={starsAmount}
                    onChange={(e) => setStarsAmount(e.target.value)}
                    placeholder="Кол-во звёзд"
                    className="w-full px-4 py-3 rounded-xl text-white font-black text-sm"
                    style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}
                  />
                  <motion.button
                    whileTap={{ scale: 0.98 }}
                    onClick={handleStarsPayment}
                    className="w-full py-3 rounded-xl font-black uppercase text-sm transition-all"
                    style={{ backgroundColor: 'white', color: '#22242a' }}
                  >
                    КУПИТЬ ЗВЁЗДЫ
                  </motion.button>
                </div>
              </div>

              {/* TON Tab */}
              <div>
                <h3 className="text-white font-black text-sm uppercase mb-4">⚡ ЧЕРЕЗ TON</h3>
                <div className="space-y-3">
                  <input
                    type="number"
                    step="0.1"
                    value={tonAmount}
                    onChange={(e) => setTonAmount(e.target.value)}
                    placeholder="TON"
                    className="w-full px-4 py-3 rounded-xl text-white font-black text-sm"
                    style={{ backgroundColor: 'rgba(255, 255, 255, 0.05)', border: '1px solid rgba(255, 255, 255, 0.1)' }}
                  />
                  <motion.button
                    whileTap={{ scale: 0.98 }}
                    onClick={handleTonPayment}
                    className="w-full py-3 rounded-xl font-black uppercase text-sm transition-all"
                    style={{ backgroundColor: 'white', color: '#22242a' }}
                  >
                    ОТПРАВИТЬ
                  </motion.button>
                </div>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
