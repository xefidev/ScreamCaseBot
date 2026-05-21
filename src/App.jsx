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
  cases: 'Кейсы',
  achievements: 'Достижения',
  games: 'Игры',
  profile: 'Профиль',
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
  const [inventory, setInventory] = useState(() => JSON.parse(localStorage.getItem('inventory') || '[]'));
  const [transactions, setTransactions] = useState(() => JSON.parse(localStorage.getItem('transactions') || '[]'));
  const [balance, setBalance] = useState(() => Number(localStorage.getItem('balance') || 0));
  const [tickets, setTickets] = useState(0);

  const triggerHaptic = (type = 'light') => {
    const haptic = window.Telegram?.WebApp?.HapticFeedback;
    if (haptic) {
      if (type === 'success') haptic.notificationOccurred('success');
      else haptic.impactOccurred(type === 'heavy' ? 'heavy' : 'light');
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
    } catch (error) { console.error('Sync balance error:', error); return null; }
  };

  const loadAchievements = async (userId = user?.id) => {
    if (!userId) return;
    try {
      const data = await fetchAchievements(userId);
      setAchievements(Array.isArray(data) ? data : []);
    } catch (error) { console.error('Load achievements error:', error); }
  };

  useEffect(() => {
    const init = async () => {
      const tg = window.Telegram?.WebApp;
      if (tg) {
        tg.ready(); tg.expand();
        const userData = tg.initDataUnsafe?.user;
        if (userData) { setUser(userData); await syncBalance(userData.id); }
      }
      setLoading(false);
    };
    init();
  }, []);

  useEffect(() => {
    if (activeTab === 'achievements') loadAchievements();
  }, [activeTab]);

  useEffect(() => {
    localStorage.setItem('inventory', JSON.stringify(inventory));
    localStorage.setItem('transactions', JSON.stringify(transactions));
    localStorage.setItem('balance', balance.toString());
  }, [inventory, transactions, balance]);

  const handleStarsPayment = async () => {
    triggerHaptic(); if (!user?.id) return;
    try {
      const { link } = await createInvoice(user.id, starsAmount);
      window.Telegram?.WebApp?.openTelegramLink(link);
      setShowTopUp(false);
    } catch (error) { window.Telegram?.WebApp?.showAlert?.('Ошибка при создании инвойса'); }
  };

  const handleClaimAchievement = async (aid) => {
    triggerHaptic(); if (!user?.id) return;
    try {
      const res = await claimAchievement(user.id, aid);
      if (res.success) {
        triggerHaptic('success');
        await syncBalance(user.id);
        await loadAchievements();
      }
    } catch (e) { console.error(e); }
  };

  const handleSpinComplete = (item, caseItem) => {
    if (user?.id) syncBalance(user.id);
    const inventoryItem = { id: Date.now(), name: item?.name || 'Item', image: item?.image || '', price: item?.price || 0, caseName: caseItem?.name };
    setInventory((prev) => [inventoryItem, ...prev]);
  };

  const renderAchievements = () => (
    <div className="h-full overflow-y-auto p-6 pb-24" style={{ backgroundColor: PAGE_BG }}>
      <h2 className="mb-6 font-rounded text-2xl font-black uppercase tracking-tight text-white text-glow">Достижения</h2>
      <div className="space-y-4">
        {achievements.map((a) => {
          const progress = Math.min(a.progress, a.goal);
          const percent = (progress / a.goal) * 100;
          const isComplete = progress >= a.goal;
          return (
            <div key={a.id} className="glass-panel p-5 border-white/10 bg-white/[0.02] relative overflow-hidden">
               {isComplete && !a.claimed && <div className="absolute inset-0 bg-yellow-500/5 animate-pulse-slow pointer-events-none" />}
               <div className="flex justify-between items-start mb-3">
                  <div>
                    <h3 className="font-black text-sm uppercase tracking-tight text-white">{a.title}</h3>
                    <p className="text-[10px] text-white/40 font-bold uppercase">Награда: {a.reward} ⭐</p>
                  </div>
                  <span className="text-[10px] font-black text-white/20 uppercase tracking-widest">{progress}/{a.goal}</span>
               </div>
               <div className="h-1.5 w-full bg-white/5 rounded-full overflow-hidden mb-4">
                  <motion.div initial={{ width: 0 }} animate={{ width: `${percent}%` }} className="h-full bg-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.5)]" />
               </div>
               {a.claimed ? (
                 <div className="w-full py-2 rounded-xl bg-white/5 border border-white/5 text-center"><span className="text-[10px] font-black uppercase text-white/20">Награда получена</span></div>
               ) : (
                 <button onClick={() => handleClaimAchievement(a.id)} disabled={!isComplete} className={`w-full py-2.5 rounded-xl font-black text-[10px] uppercase tracking-widest transition-all ${isComplete ? 'bg-yellow-500 text-black shadow-lg shadow-yellow-500/20' : 'bg-white/5 text-white/20 cursor-not-allowed'}`}>Забрать награду</button>
               )}
            </div>
          );
        })}
      </div>
    </div>
  );

  const renderContent = () => {
    if (loading) return <LoadingSpinner />;
    if (activeTab === 'cases') return <CasesGrid user={user} onWin={handleSpinComplete} balance={balance} setBalance={setBalance} promoOpened={promoOpened} setPromoOpened={setPromoOpened} />;
    if (activeTab === 'achievements') return renderAchievements();
    if (activeTab === 'games') {
      if (activeGame === 'wheel') return <div className="h-full overflow-y-auto" style={{ backgroundColor: PAGE_BG }}><div className="p-4"><button onClick={() => setActiveGame(null)} className="glass-button p-2 text-white/70">Назад</button></div><WheelGame isPage onWin={() => syncBalance(user?.id)} balance={balance} setBalance={setBalance} /></div>;
      if (activeGame === 'upgrade') return <div className="h-full overflow-y-auto" style={{ backgroundColor: PAGE_BG }}><div className="p-4"><button onClick={() => setActiveGame(null)} className="glass-button p-2 text-white/70">Назад</button></div><UpgradeGame isPage inventory={inventory} setInventory={setInventory} balance={balance} setBalance={setBalance} /></div>;
      return (
        <div className="h-full overflow-y-auto p-6 pb-24 text-white" style={{ backgroundColor: PAGE_BG }}>
          <h2 className="mb-2 font-rounded text-2xl font-black uppercase tracking-tight">Мини-игры</h2>
          <div className="grid grid-cols-1 gap-4 mt-6">
            <button onClick={() => { triggerHaptic(); setActiveGame('wheel'); }} className="relative h-40 overflow-hidden rounded-3xl border border-purple-500/20 text-left bg-gradient-to-br from-purple-600/10 to-black/20"><div className="relative z-10 flex h-full flex-col justify-between p-6"><div><h3 className="font-rounded text-xl font-black uppercase">Колесо Фортуны</h3><p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-purple-400">Выигрыш до 500 звезд</p></div><span className="text-xs font-black uppercase text-white/60">Играть</span></div></button>
            <button onClick={() => { triggerHaptic(); setActiveGame('upgrade'); }} className="relative h-40 overflow-hidden rounded-3xl border border-green-500/20 text-left bg-gradient-to-br from-green-600/10 to-black/20"><div className="relative z-10 flex h-full flex-col justify-between p-6"><div><h3 className="font-rounded text-xl font-black uppercase">Апгрейд</h3><p className="mt-1 text-[10px] font-bold uppercase tracking-widest text-green-400">Улучшай свои предметы</p></div><span className="text-xs font-black uppercase text-white/60">Играть</span></div></button>
          </div>
        </div>
      );
    }
    if (activeTab === 'profile') return <ProfilePage isPage inventory={inventory} setInventory={setInventory} balance={balance} setBalance={setBalance} />;
    return null;
  };

  return (
    <div className="min-h-screen w-full overflow-hidden text-white font-rounded" style={{ backgroundColor: PAGE_BG }}>
      <div className="flex h-screen flex-col" style={{ backgroundColor: PAGE_BG }}>
        <div className="glass-panel border-b border-white/10 px-6 py-4" style={{ backgroundColor: PAGE_BG }}>
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-white/5">{user?.photo_url ? <img src={user.photo_url} alt="U" className="h-full w-full object-cover" onError={(e) => e.currentTarget.style.display='none'} /> : <span className="font-bold text-white/30">{user?.first_name?.charAt(0) || 'U'}</span>}</div>
              <h1 className="text-lg font-black uppercase text-white truncate max-w-[120px]">{user?.first_name || 'Игрок'}</h1>
            </div>
            <button onClick={() => { setShowTopUp(true); triggerHaptic(); }} className="glass-button flex items-center gap-2 border-yellow-500/30 bg-yellow-500/5 px-4 py-2"><img src="/asset/Icons/TelegramStar.png" alt="S" className="h-6 w-6" onError={(e) => e.currentTarget.src='/asset/Gifts/Case.webp'} /><span className="text-lg font-black text-yellow-400"><CountUp end={balance} duration={0.5} /></span><span className="text-xs font-bold text-yellow-400/50">+</span></button>
          </div>
        </div>
        <div className="relative flex-1 overflow-hidden">{renderContent()}</div>
        <div className="glass-panel border-t border-white/10 px-4 py-2" style={{ backgroundColor: PAGE_BG }}>
          <div className="flex h-16 items-center justify-around">
            {Object.entries(TABS).map(([key, label]) => (
              <button key={key} className="relative flex h-12 w-16 flex-col items-center justify-center" onClick={() => { setActiveTab(key); setActiveGame(null); triggerHaptic(); }}>
                {activeTab === key && <motion.div layoutId="pill" className="absolute inset-[-4px] rounded-2xl border border-white/10 bg-white/5" />}
                <span className={`z-10 text-[9px] font-black uppercase tracking-tighter ${activeTab === key ? 'text-white' : 'text-white/30'}`}>{label}</span>
              </button>
            ))}
          </div>
        </div>
      </div>
      <AnimatePresence>
        {showTopUp && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} className="fixed inset-0 z-50 flex items-end justify-center bg-black/80 backdrop-blur-sm" onClick={() => setShowTopUp(false)}>
            <motion.div initial={{ y: '100%' }} animate={{ y: 0 }} exit={{ y: '100%' }} onClick={e => e.stopPropagation()} className="glass-panel w-full max-w-md rounded-t-3xl border-t border-white/20 p-8 pb-10" style={{ backgroundColor: PAGE_BG }}>
              <h2 className="mb-8 text-center text-xl font-black uppercase tracking-widest text-glow">Пополнение</h2>
              <div className="space-y-4">
                <div className="glass-panel p-6 border-white/10"><div className="flex items-center gap-4 mb-4"><img src="/asset/Icons/TelegramStar.png" className="h-10 w-10" onError={e => e.currentTarget.src='/asset/Gifts/Case.webp'} /><input type="number" value={starsAmount} onChange={e => setStarsAmount(e.target.value)} className="flex-1 bg-white/5 border border-white/10 rounded-xl p-3 text-right font-black text-yellow-400" /></div><button onClick={handleStarsPayment} className="w-full py-4 rounded-xl bg-yellow-500 text-black font-black uppercase tracking-widest">Купить звезды</button></div>
                <div className="glass-panel p-6 border-blue-500/20 bg-blue-500/5"><div className="flex items-center gap-4 mb-4"><img src="/asset/Icons/TonCoin.png" className="h-10 w-10" onError={e => e.currentTarget.src='/asset/Gifts/Case.webp'} /><input type="number" value={tonAmount} onChange={e => setTonAmount(e.target.value)} className="flex-1 bg-white/5 border border-white/10 rounded-xl p-3 text-right font-black text-blue-400" /></div><button onClick={handleTonPayment} className="w-full py-4 rounded-xl bg-blue-500 text-white font-black uppercase tracking-widest">Перевести TON</button></div>
              </div>
              <button onClick={() => setShowTopUp(false)} className="mt-6 w-full py-2 text-[10px] font-black uppercase tracking-[0.4em] text-white/20">Закрыть</button>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
