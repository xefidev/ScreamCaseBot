import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { claimPromo, fetchBalance, adminCreatePromo, fetchLeaderboard, fetchReferrals } from '../api';

const ADMIN_IDS = [7782281997, 5396975347];

const formatValue = (val) => {
  if (val === undefined || val === null) return '0';
  if (val >= 1000) return (val / 1000).toFixed(1).replace('.0', '') + 'k';
  return val.toString();
};

export default function ProfilePage({ onClose, isPage, inventory, setInventory, transactions, setTransactions, balance, setBalance, tickets, spent, donor }) {
  const [user, setUser] = React.useState(null);
  const [leaderboard, setLeaderboard] = React.useState([]);
  const [referralCount, setReferralCount] = React.useState(0);
  
  const [mgrCode, setMgrCode] = React.useState('');
  const [mgrReward, setMgrReward] = React.useState('100');
  const [mgrHours, setMgrHours] = React.useState('24');
  const [mgrMinDonation, setMgrMinDonation] = React.useState('0');

  React.useEffect(() => {
    if (window.Telegram?.WebApp) {
      const userData = window.Telegram.WebApp.initDataUnsafe?.user;
      setUser(userData);
      if (userData?.id) {
          loadReferrals(userData.id);
      }
    }
    loadLeaderboard();
  }, []);

  const loadLeaderboard = async () => {
    try {
      const data = await fetchLeaderboard();
      setLeaderboard(Array.isArray(data) ? data : []);
    } catch (e) {
      console.error(e);
      setLeaderboard([]);
    }
  };

  const loadReferrals = async (userId) => {
    try {
        const data = await fetchReferrals(userId);
        setReferralCount(data?.count || 0);
    } catch (e) {
        console.error(e);
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

  const handleCreatePromo = async () => {
      if (!user?.id || !ADMIN_IDS.includes(user.id)) return;
      if (!mgrCode.trim()) {
          window.Telegram?.WebApp?.showAlert?.("❌ Введите код промокода");
          return;
      }

      try {
          triggerHaptic('impact');
          // Using bot command logic simulation via API if exists, 
          // but usually this is done via bot. Here we use the existing API function.
          await adminCreatePromo(user.id, {
              code: mgrCode.trim().toUpperCase(),
              reward: parseInt(mgrReward),
              hours: parseInt(mgrHours) || 24,
              min_donation: parseInt(mgrMinDonation) || 0,
              type: 'stars'
          });
          
          setMgrCode('');
          setMgrReward('100');
          setMgrHours('24');
          setMgrMinDonation('0');
          triggerHaptic('success');
          window.Telegram?.WebApp?.showAlert?.("✅ Промокод успешно создан!");
      } catch (error) {
          console.error("Error creating promo:", error);
      }
  };

  const handleSell = (item) => {
    triggerHaptic();
    if (!setInventory || !setBalance) return;
    setInventory(prev => prev.filter(i => i.id !== item.id));
    setBalance(prev => prev + item.price);
    if (setTransactions) {
      setTransactions(prev => [{
        id: Date.now(),
        type: 'sell',
        amount: item.price,
        description: 'Продажа предмета',
        item: item.name,
      }, ...prev]);
    }
    triggerHaptic('success');
  };

  const handleCopyReferral = () => {
    triggerHaptic();
    const userId = user?.id || 'guest';
    const refLink = `https://t.me/ScreamCase_bot?start=${userId}`;
    
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(refLink).then(() => {
            window.Telegram?.WebApp?.showPopup?.({
                title: 'Успех',
                message: 'Реферальная ссылка скопирована!',
                buttons: [{ type: 'ok' }]
            });
            triggerHaptic('success');
        });
    } else {
        // Fallback
        const textArea = document.createElement("textarea");
        textArea.value = refLink;
        document.body.appendChild(textArea);
        textArea.select();
        try {
            document.execCommand('copy');
            window.Telegram?.WebApp?.showPopup?.({
                title: 'Успех',
                message: 'Реферальная ссылка скопирована!',
                buttons: [{ type: 'ok' }]
            });
            triggerHaptic('success');
        } catch (err) {
            console.error('Fallback: Oops, unable to copy', err);
        }
        document.body.removeChild(textArea);
    }
  };

  const content = (
    <div className={`${isPage ? 'min-h-full pb-24' : 'max-w-md mx-auto p-6 min-h-screen'}`}>
      <div className="mb-8">
        <h2 className="text-2xl font-black text-white uppercase tracking-widest">Профиль</h2>
      </div>

      <div className="glass-panel p-6 mb-6 relative overflow-hidden">
        <div className="absolute top-0 right-0 w-32 h-32 bg-blue-500/10 blur-3xl rounded-full -mr-16 -mt-16" />
        <div className="flex items-center gap-4 mb-6 relative z-10">
          <div className="w-20 h-20 rounded-full border-2 border-white/10 bg-white/5 flex items-center justify-center overflow-hidden">
            {user?.photo_url ? (
              <img src={user.photo_url} alt="Avatar" className="w-full h-full object-cover" />
            ) : (
              <span className="text-3xl text-white/20 font-black">{user?.first_name?.charAt(0) || 'U'}</span>
            )}
          </div>
          <div>
            <h3 className="text-white font-black text-2xl font-rounded uppercase tracking-tight">
              {user?.first_name || 'ИГРОК'}
              {ADMIN_IDS.includes(user?.id) && <span className="text-[10px] bg-green-500/20 text-green-400 px-1.5 py-0.5 rounded border border-green-500/30 ml-2 align-middle">ADMIN</span>}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span className="text-white/40 text-[10px] font-bold">ID: {user?.id || '0'}</span>
              <div className="flex items-center gap-1 bg-white/5 border border-white/10 px-2 py-0.5 rounded-lg">
                <span className="text-[10px]">🏆</span>
                <span className="text-[10px] font-black text-white/90 uppercase tracking-tight">{formatValue(donor)}</span>
              </div>
              <div className="flex items-center gap-1 bg-white/5 border border-white/10 px-2 py-0.5 rounded-lg">
                <span className="text-[10px]">💸</span>
                <span className="text-[10px] font-black text-white/90 uppercase tracking-tight">{formatValue(spent)}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="grid grid-cols-2 gap-4 relative z-10">
          <div className="p-4 rounded-3xl bg-white/5 border border-white/10 text-center">
            <p className="text-white/50 text-[10px] mb-1 uppercase tracking-widest font-bold">Баланс</p>
            <p className="text-white font-black text-xl flex items-center justify-center gap-1">
              {balance} <img src="/asset/Icons/TelegramStar.png" className="h-5 w-5" alt="Stars" />
            </p>
          </div>
          <div className="p-4 rounded-3xl bg-white/5 border border-white/10 text-center">
            <p className="text-white/50 text-[10px] mb-1 uppercase tracking-widest font-bold">Потрачено</p>
            <p className="text-white font-black text-xl flex items-center justify-center gap-1">
              {spent} <img src="/asset/Icons/TelegramStar.png" className="h-5 w-5" alt="Stars" />
            </p>
          </div>
        </div>
      </div>

      {ADMIN_IDS.includes(user?.id) && (
        <div className="glass-panel p-6 border-red-500/20 bg-red-500/5 mb-6">
            <h4 className="text-red-400 font-black text-lg mb-4 uppercase tracking-widest flex items-center gap-2">
                MANAGER PANEL <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            </h4>
            <div className="space-y-3">
                <input type="text" value={mgrCode} onChange={e => setMgrCode(e.target.value.toUpperCase())} placeholder="PROMO CODE" className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-2 text-white font-bold text-sm" />
                <div className="grid grid-cols-3 gap-2">
                    <input type="number" value={mgrReward} onChange={e => setMgrReward(e.target.value)} placeholder="Reward" className="bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-white text-xs" title="Награда" />
                    <input type="number" value={mgrHours} onChange={e => setMgrHours(e.target.value)} placeholder="Hours" className="bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-white text-xs" title="Часы" />
                    <input type="number" value={mgrMinDonation} onChange={e => setMgrMinDonation(e.target.value)} placeholder="Min Don" className="bg-black/40 border border-white/10 rounded-xl px-3 py-2 text-white text-xs" title="Мин. пополнение" />
                </div>
                <motion.button whileTap={{ scale: 0.95 }} onClick={handleCreatePromo} className="w-full py-3 rounded-xl bg-red-500/20 border border-red-500/30 text-red-400 font-black uppercase tracking-widest text-xs">CREATE PROMO</motion.button>
            </div>
        </div>
      )}

      <div className="glass-panel p-6 mb-6">
          <h4 className="text-white font-black text-xl mb-4 uppercase tracking-widest">Таблица лидеров</h4>
          <div className="space-y-3">
              {leaderboard.length > 0 ? leaderboard.slice(0, 10).map((item, idx) => (
                  <div key={idx} className="flex justify-between items-center p-3 rounded-2xl bg-white/5 border border-white/5">
                      <div className="flex items-center gap-3">
                          <span className={`w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-black ${idx === 0 ? 'bg-yellow-500 text-black' : 'bg-white/10 text-white'}`}>{idx + 1}</span>
                          <span className="text-white font-bold truncate max-w-[120px]">{item.username ? `@${item.username}` : (item.first_name || `ID: ${item.user_id}`)}</span>
                      </div>
                      <span className="text-yellow-400 font-black flex items-center gap-1">{item.donated} <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" /></span>
                  </div>
              )) : <p className="text-white/30 text-center py-4 text-sm">Загрузка...</p>}
          </div>
      </div>

      <div className="glass-panel p-6 mb-6 relative overflow-hidden group">
        <div className="flex justify-between items-start mb-4 relative z-10">
            <h4 className="text-white font-black text-lg uppercase tracking-widest">Рефералы</h4>
            <div className="px-3 py-1 rounded-full bg-blue-500/20 border border-blue-500/30 text-blue-400 text-[10px] font-black">{referralCount} РЕФ</div>
        </div>
        <p className="text-white/50 text-xs mb-4 relative z-10">Получайте <span className="text-white font-bold">10%</span> от пополнений друзей и <span className="text-white font-bold">+1 билет</span> 🎫 за каждого!</p>
        <motion.button whileTap={{ scale: 0.98 }} onClick={handleCopyReferral} className="w-full py-4 rounded-2xl bg-white text-black font-black uppercase tracking-widest text-xs flex items-center justify-center gap-2">СКОПИРОВАТЬ ССЫЛКУ</motion.button>
      </div>

      <div className="glass-panel p-6 mb-6">
        <h4 className="text-white font-black text-xl mb-4 uppercase tracking-widest">Инвентарь ({inventory?.length || 0})</h4>
        {!inventory || inventory.length === 0 ? (
          <div className="text-center py-8 opacity-30"><p className="text-white">Пусто</p></div>
        ) : (
          <div className="grid grid-cols-2 gap-4">
            {inventory.map((item) => (
              <div key={item.id} className="p-3 rounded-2xl bg-white/5 border border-white/10 flex flex-col items-center">
                <img src={item.image} alt={item.name} className="w-16 h-16 object-contain mb-2" />
                <p className="text-white text-[10px] font-bold text-center truncate w-full mb-2">{item.name}</p>
                <motion.button whileTap={{ scale: 0.95 }} onClick={() => handleSell(item)} className="w-full py-2 rounded-xl text-[8px] font-black uppercase bg-red-500/10 border border-red-500/20 text-red-500 flex items-center justify-center gap-1">ПРОДАТЬ ЗА {item.price} <img src="/asset/Icons/TelegramStar.png" className="h-3 w-3" alt="Stars" /></motion.button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );

  return <div className="p-4 h-full overflow-y-auto">{content}</div>;
}
