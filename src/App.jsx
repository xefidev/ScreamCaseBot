import React, { useEffect, useState, useRef } from 'react';
import { AnimatePresence, motion, MotionConfig } from 'framer-motion';
import CountUp from 'react-countup';
import { useTonConnectUI } from '@tonconnect/ui-react';
import { Briefcase, Trophy, Gamepad2, User, Zap, ChevronLeft, Plus } from 'lucide-react';
import CasesGrid from './components/CasesGrid';
import WheelGame from './components/games/WheelGame';
import UpgradeGame from './components/games/UpgradeGame';
import ProfilePage from './components/ProfilePage';
import QuestsTab from './components/QuestsTab';
import { createInvoice, fetchBalance, notifyTonSuccess, sendHeartbeat, sendPing } from './api';
import { getDynamicGiftImage } from './giftUtils';

const PAGE_BG = '#1a1b1e';
const TON_WALLET = import.meta.env.VITE_TON_WALLET;

// Список ID администраторов
const ADMIN_IDS = (import.meta.env.VITE_ADMIN_IDS || '').split(',').map(id => parseInt(id.trim())).filter(id => !isNaN(id));

// Звук через пул переиспользуемых Audio объектов (см. audioPool.js)
import { playSound as poolPlay, stopSound as poolStop } from './audioPool';
import { usePerf } from './perfContext.jsx';
export const playSound = poolPlay;
export const stopSound = poolStop;

const TABS = {
  cases: { label: 'Кейсы', icon: Briefcase },
  achievements: { label: 'Награды', icon: Trophy },
  games: { label: 'Игры', icon: Gamepad2 },
  profile: { label: 'Профиль', icon: User },
};

const LoadingSpinner = () => (
  <div className="flex h-full flex-col items-center justify-center" style={{ backgroundColor: PAGE_BG }}>
    <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }} className="mb-4 h-12 w-12 rounded-full border-4 border-white/10 border-t-white" />
    <p className="font-rounded text-xs uppercase tracking-widest text-white/50">Загрузка...</p>
  </div>
);

export default function App() {
  const { lowPerf } = usePerf();
  const [activeTab, setActiveTab] = useState('cases');
  const [activeGame, setActiveGame] = useState(null);
  const [showTopUp, setShowTopUp] = useState(false);
  const [starsAmount, setStarsAmount] = useState('100');
  const [tonAmount, setTonAmount] = useState('0.1');
  const [tonConnectUI] = useTonConnectUI();
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [promoOpened, setPromoOpened] = useState(false);
  const [inventory, setInventory] = useState(() => {
    try {
      return JSON.parse(localStorage?.getItem('inventory') || '[]');
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

  const isAdmin = user?.id && ADMIN_IDS.includes(user.id);

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
      // fetchBalance возвращает { stars, tickets, donor, spent, promo_opened }
      const data = await fetchBalance(userId);
      const starsValue = typeof data?.stars === 'number' ? data.stars : 0;
      setBalance(starsValue);
      setPromoOpened(!!data?.promo_opened);
      console.log('✅ Баланс синхронизирован:', starsValue, '⭐');
      return data;
    } catch (error) {
      console.error('Sync balance error:', error);
      return null;
    }
  };

  useEffect(() => {
    // Немедленный пинг при загрузке — чтобы разбудить Render если он спит
    sendPing().then(() => {
      console.log('✅ Начальный пинг отправлен — сервер активен');
    }).catch(() => {
      console.warn('⚠️ Начальный пинг не прошёл');
    });

    // Повторный пинг каждые 10 минут (Render засыпает через 15 мин)
    const keepAliveInterval = setInterval(async () => {
      try {
        await sendPing();
        console.log('✅ Keep-alive ping отправлен');
      } catch (error) {
        console.warn('⚠️ Keep-alive ping не прошёл:', error);
      }
    }, 10 * 60 * 1000);
    return () => {
      clearInterval(keepAliveInterval);
    };
  }, []);

  useEffect(() => {
    const init = async () => {
      try {
        const tg = window?.Telegram?.WebApp;
        if (tg) {
          tg.ready?.();
          tg.expand?.();
          
          let userData = tg.initDataUnsafe?.user;
          
          // Test ID fallback for browser development
          if (!userData || !userData.id) {
            console.warn('Telegram initDataUnsafe is empty. Using Test ID.');
            userData = {
              id: 7782281997, // Ваш Test ID
              first_name: 'Test',
              last_name: 'User',
              username: 'test_user',
              photo_url: null
            };
          }
          
          if (userData && userData.id) {
            setUser(userData);
            console.log('App initialized for user:', userData.id);
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

  // Heartbeat to keep Render.com server awake (every 10 minutes)
  useEffect(() => {
    if (!user?.id) return;
    
    const heartbeatInterval = setInterval(() => {
      sendHeartbeat(user.id).catch(err => console.warn('Heartbeat error:', err));
    }, 10 * 60 * 1000); // 10 minutes
    
    return () => clearInterval(heartbeatInterval);
  }, [user?.id]);

  useEffect(() => {
    try {
      localStorage?.setItem('inventory', JSON.stringify(inventory));
      localStorage?.setItem('balance', balance.toString());
    } catch (e) {
      console.warn('localStorage error:', e);
    }
  }, [inventory, balance]);

  const handleStarsPayment = async (customAmount = null) => {
    triggerHaptic();
    if (!user?.id) {
      window?.Telegram?.WebApp?.showAlert?.('❌ Пользователь не определен');
      return;
    }
    const amount = customAmount || starsAmount;
    // Confirm dialog before creating invoice
    const tg = window?.Telegram?.WebApp;
    if (tg?.showConfirm) {
      const confirmed = await new Promise((resolve) => {
        tg.showConfirm(`Пополнить баланс на ${amount} ⭐ через Telegram Stars?`, (ok) => resolve(ok));
      });
      if (!confirmed) return;
    }
    try {
      console.log('Creating invoice for user:', user.id, 'amount:', amount);
      if (!window.Telegram?.WebApp) {
          console.warn('Telegram WebApp is undefined');
      }
      const invoiceResp = await createInvoice(user.id, amount, 'stars');
      const link = invoiceResp?.invoice_link || invoiceResp?.link;
      if (link) {
        window?.Telegram?.WebApp?.openInvoice?.(link, (status) => {
          if (status === 'paid') {
            triggerHaptic('success');
            window?.Telegram?.WebApp?.showAlert?.('✅ Баланс успешно пополнен!');
            // ИСПРАВЛЕНО: fetchBalance возвращает объект, берём .stars
            fetchBalance(user.id).then(balData => {
              if (balData && typeof balData.stars === 'number') {
                setBalance(balData.stars);
              }
            }).catch(console.error);
          } else if (status === 'failed') {
            window?.Telegram?.WebApp?.showAlert?.('❌ Не удалось оплатить счёт');
          }
        });
      } else {
        throw new Error('No invoice link returned from server');
      }
      setShowTopUp(false);
    } catch (error) {
      console.error('Invoice error:', error);
      window?.Telegram?.WebApp?.showAlert?.('❌ Ошибка при создании инвойса');
    }
  };

  const copyToClipboard = (text, label) => {
    navigator.clipboard.writeText(text);
    window?.Telegram?.WebApp?.showAlert?.(`${label} скопирован!`);
  };

  const [tonPaymentData, setTonInvoiceData] = useState(null);

  const handleTonPayment = async () => {
    triggerHaptic();
    if (!user?.id) {
      window?.Telegram?.WebApp?.showAlert?.('❌ Пользователь не определен');
      return;
    }
    
    const amount = parseFloat(tonAmount) || 0.1;
    
    try {
      // 1. Получаем кошелек и уникальный комментарий от бэкенда
      const invoice = await createInvoice(user.id, amount, 'ton');
      
      if (!invoice.wallet || !invoice.comment) {
          throw new Error('Invalid invoice data from server');
      }

      setTonInvoiceData(invoice);

      // 2. Если кошелек подключен через TON Connect, пробуем отправить транзакцию автоматически
      if (tonConnectUI.account) {
        const nanotons = (amount * 1000000000).toString();
        
        const transaction = {
          validUntil: Math.floor(Date.now() / 1000) + 600,
          messages: [
            {
              address: invoice.wallet,
              amount: nanotons,
              payload: invoice.payload_boc || invoice.comment
            },
          ],
        };

        try {
            const txResult = await tonConnectUI.sendTransaction(transaction);
            if (txResult) {
              triggerHaptic('success');
              window?.Telegram?.WebApp?.showAlert?.('🚀 Транзакция отправлена! Баланс обновится автоматически в течение 1-2 минут.');
              setShowTopUp(false);
              setTonInvoiceData(null);
              // Optimistic balance refresh after 30s
              setTimeout(() => {
                fetchBalance(user.id).then(d => { if (d && typeof d.stars === 'number') setBalance(d.stars); }).catch(()=>{});
              }, 30000);
            }
        } catch (err) {
            console.warn('TON auto-transaction declined/failed:', err?.message || err);
            // Don't show alert — user just sees manual payment details modal as fallback
        }
      }
      
    } catch (e) {
      console.error('TON payment error:', e);
      window?.Telegram?.WebApp?.showAlert?.('❌ Ошибка при подготовке платежа');
    }
  };


  const handleSpinComplete = (item, caseItem) => {
    const inventoryItem = {
      id: Date.now() + Math.random(),
      name: item?.name || 'Item',
      image: getDynamicGiftImage(item),
      price: item?.price || 0,
      caseName: caseItem?.name
    };
    setInventory((prev) => [inventoryItem, ...prev]);
  };


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
            onTopUpRequest={(needed) => {
                setShowTopUp(true);
                setStarsAmount(needed.toString());
            }}
          />
        );
      case 'achievements':
        return <QuestsTab userId={user?.id} onBalanceUpdate={() => syncBalance(user?.id)} />;
      case 'games':
        if (activeGame === 'wheel') {
          return (
            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="h-full overflow-y-auto bg-[#1a1b1e]">
              <div className="px-6 py-4">
                <button onClick={() => setActiveGame(null)} className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/5 border border-white/10 text-white hover:bg-white/10 transition-colors">
                  <ChevronLeft size={24} strokeWidth={2.5} />
                </button>
              </div>
              <WheelGame isPage onWin={(seg) => { handleSpinComplete(seg?.item || seg, null); syncBalance(user?.id); }} balance={balance} setBalance={setBalance} />
            </motion.div>
          );
        }
        if (activeGame === 'upgrade') {
          return (
            <motion.div initial={{ opacity: 0, x: 20 }} animate={{ opacity: 1, x: 0 }} className="h-full overflow-y-auto bg-[#1a1b1e]">
              <div className="px-6 py-4">
                <button onClick={() => setActiveGame(null)} className="w-10 h-10 flex items-center justify-center rounded-xl bg-white/5 border border-white/10 text-white hover:bg-white/10 transition-colors">
                  <ChevronLeft size={24} strokeWidth={2.5} />
                </button>
              </div>
              <UpgradeGame isPage inventory={inventory} setInventory={setInventory} balance={balance} setBalance={setBalance} />
            </motion.div>
          );
        }
        return (
          <div className="h-full overflow-y-auto p-6 pb-24 text-white" style={{ backgroundColor: PAGE_BG }}>
            <h2 className="mb-2 font-rounded text-2xl font-black uppercase tracking-tight">Мини-игры</h2>
            <div className="grid grid-cols-1 gap-4 mt-6">
              <button
                onClick={() => { triggerHaptic(); setActiveGame('wheel'); }}
                className="relative h-44 overflow-hidden rounded-[2.5rem] border border-purple-500/30 text-left bg-gradient-to-br from-purple-600/10 to-black/40 shadow-2xl transition-all group"
              >
                <div className="absolute right-[-10%] top-[-10%] h-40 w-40 flex items-center justify-center opacity-20 group-hover:opacity-40 transition-opacity">
                  <Gamepad2 size={120} className="text-purple-400 rotate-12" />
                </div>
                <div className="relative z-10 flex h-full flex-col justify-between p-8">
                  <div>
                    <h3 className="font-rounded text-2xl font-black uppercase tracking-tighter">Колесо Фортуны</h3>
                    <p className="mt-1 text-[10px] font-black uppercase tracking-[0.2em] text-purple-400/80">ВЫИГРЫВАЙ УНИКАЛЬНЫЕ ПОДАРКИ</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-black uppercase text-white/60">Играть</span>
                    <div className="w-6 h-6 rounded-full bg-purple-500/20 flex items-center justify-center">
                        <ChevronLeft size={14} className="rotate-180" />
                    </div>
                  </div>
                </div>
              </button>

              <button
                onClick={() => { triggerHaptic(); setActiveGame('upgrade'); }}
                className="relative h-44 overflow-hidden rounded-[2.5rem] border border-green-500/30 text-left bg-gradient-to-br from-green-600/10 to-black/40 shadow-2xl transition-all group"
              >
                <div className="absolute right-[-10%] top-[-10%] h-40 w-40 flex items-center justify-center opacity-20 group-hover:opacity-40 transition-opacity">
                  <Zap size={120} className="text-green-400 -rotate-12" />
                </div>
                <div className="relative z-10 flex h-full flex-col justify-between p-8">
                  <div>
                    <h3 className="font-rounded text-2xl font-black uppercase tracking-tighter">Апгрейд</h3>
                    <p className="mt-1 text-[10px] font-black uppercase tracking-[0.2em] text-green-400/80">УЛУЧШАЙ СВОИ ПРЕДМЕТЫ</p>
                  </div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-black uppercase text-white/60">Играть</span>
                    <div className="w-6 h-6 rounded-full bg-green-500/20 flex items-center justify-center">
                        <ChevronLeft size={14} className="rotate-180" />
                    </div>
                  </div>
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
    <div className="h-screen w-full overflow-hidden flex justify-center items-center bg-[#1a1b1e] text-white font-rounded select-none">
      <div className="relative z-10 flex flex-col h-screen w-full max-w-md bg-[#1a1b1e] overflow-hidden">
        <div className="shrink-0">
          <div className="px-6 py-4 flex items-center justify-between bg-[#1a1b1e]/80 backdrop-blur-lg border-b border-white/5">
          <div className="flex items-center justify-between w-full">
            <div className="flex items-center gap-4">
              <div className="flex h-12 w-12 items-center justify-center overflow-hidden rounded-2xl border border-white/10 bg-white/5 relative">
                {user?.photo_url ? (
                  <img
                    src={user?.photo_url}
                    alt="profile"
                    className="h-full w-full object-cover"
                    loading="lazy"
                    decoding="async"
                    onError={(e) => { e.currentTarget.style.display = 'none'; }}
                  />
                ) : (
                  <span className="font-black text-white/20 text-xl">{user?.first_name?.charAt(0) || 'U'}</span>
                )}
              </div>
              <div>
                <h1 className="text-lg font-black uppercase tracking-tighter text-white truncate max-w-[120px]">
                  {user?.first_name || 'Игрок'}
                </h1>
                {isAdmin && (
                  <p className="text-[10px] text-yellow-500 font-black uppercase tracking-widest">PREMIUM USER</p>
                )}
              </div>
            </div>
            <button
              onClick={() => { setShowTopUp(true); triggerHaptic(); }}
              className="flex items-center gap-3 bg-white/5 border border-white/10 pl-4 pr-3 py-2 rounded-2xl hover:bg-white/10 transition-all group"
            >
              <div className="flex flex-col items-end">
                <span className="text-lg font-black text-yellow-500 leading-none">
                  <CountUp end={balance} duration={0.5} />
                </span>
                <span className="text-[8px] font-black text-white/30 uppercase tracking-widest">Звёзд</span>
              </div>
              <div className="w-8 h-8 rounded-xl bg-yellow-500/10 flex items-center justify-center group-hover:scale-110 transition-transform relative">
                <img src="/asset/Icons/TelegramStar.png" alt="star" className="h-6 w-6" loading="lazy" decoding="async" />
                <div className="absolute -top-1 -right-1 w-4 h-4 bg-yellow-500 rounded-full flex items-center justify-center border-2 border-[#1a1b1e]">
                  <Plus size={8} className="text-black stroke-[4px]" />
                </div>
              </div>
            </button>
          </div>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto [&::-webkit-scrollbar]:hidden [-ms-overflow-style:'none'] [scrollbar-width:'none']">
          {renderContent()}
        </div>

        <div className="shrink-0 pb-safe">
          <div className="px-6 py-4 bg-[#1a1b1e]/90 backdrop-blur-xl border-t border-white/5">
          <div className="flex h-14 items-center justify-around gap-2">
            {Object.entries(TABS).map(([key, tabData]) => {
              const Icon = tabData.icon;
              const isActive = activeTab === key;
              return (
                <button
                  key={key}
                  className="relative flex-1 flex flex-col items-center justify-center py-2 gap-1"
                  onClick={() => { setActiveTab(key); setActiveGame(null); triggerHaptic(); }}
                >
                  <div className={`w-12 h-8 rounded-2xl flex items-center justify-center transition-all ${isActive ? 'bg-white/10 text-white' : 'text-white/20 hover:text-white/40'}`}>
                    <Icon size={20} strokeWidth={isActive ? 2.5 : 2} />
                  </div>
                  <span className={`text-[8px] font-black uppercase tracking-widest transition-all ${isActive ? 'text-white' : 'text-white/20'}`}>
                    {tabData.label}
                  </span>
                </button>
              );
            })}
          </div>
        </div>
        </div>
      </div>

      <AnimatePresence>
        {showTopUp && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-md p-4"
            onClick={() => setShowTopUp(false)}
          >
            <motion.div
              initial={{ scale: 0.9, y: 40, opacity: 0 }}
              animate={{ scale: 1, y: 0, opacity: 1 }}
              exit={{ scale: 0.9, y: 40, opacity: 0 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-sm mx-auto rounded-[2.5rem] border border-white/10 bg-[#1a1b1f] overflow-hidden shadow-2xl"
            >
              <div className="relative p-8 text-center border-b border-white/5">
                <button onClick={() => { setShowTopUp(false); setTonInvoiceData(null); }} className="absolute top-6 right-6 text-white/20 hover:text-white transition-colors">✕</button>
                <h2 className="text-2xl font-black uppercase tracking-tighter text-white mb-1">Пополнение</h2>
                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/30">Выберите способ оплаты</p>
              </div>

              <div className="p-6 space-y-4 max-h-[70vh] overflow-y-auto custom-scrollbar">
                {tonPaymentData ? (
                  <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} className="space-y-4">
                     <div className="p-6 rounded-[2rem] bg-blue-500/10 border border-blue-500/30">
                        <h3 className="text-blue-400 font-black text-xs uppercase tracking-widest mb-4 text-center">Данные для оплаты TON</h3>
                        
                        <div className="space-y-3">
                          <div>
                            <p className="text-[8px] text-white/30 uppercase font-black mb-1 ml-1">Кошелек</p>
                            <button onClick={() => copyToClipboard(tonPaymentData.wallet, 'Кошелек')} className="w-full p-3 bg-black/40 border border-white/5 rounded-xl text-[10px] text-white font-mono break-all text-left hover:bg-black/60 transition-all">
                              {tonPaymentData.wallet}
                            </button>
                          </div>

                          <div>
                            <p className="text-[8px] text-white/30 uppercase font-black mb-1 ml-1">Комментарий (ОБЯЗАТЕЛЬНО)</p>
                            <button onClick={() => copyToClipboard(tonPaymentData.comment, 'Комментарий')} className="w-full p-3 bg-blue-500/20 border border-blue-500/40 rounded-xl text-xs text-blue-300 font-black break-all text-left hover:bg-blue-500/30 transition-all flex justify-between items-center">
                              <span>{tonPaymentData.comment}</span>
                              <Zap size={14} />
                            </button>
                          </div>

                          <div className="pt-2">
                            <p className="text-[10px] text-white/60 text-center font-bold">
                              Отправьте <span className="text-blue-400">{tonAmount} TON</span> одним платежом.
                            </p>
                            <p className="text-[9px] text-white/30 text-center mt-2 uppercase tracking-tighter">
                              Баланс обновится автоматически сразу после подтверждения сетью.
                            </p>
                          </div>
                        </div>
                     </div>
                     <button onClick={() => setTonInvoiceData(null)} className="w-full py-3 text-[10px] font-black uppercase text-white/20 hover:text-white/40 transition-colors">
                       ← Назад к выбору
                     </button>
                  </motion.div>
                ) : (
                  <>
                    <div className="p-6 rounded-[2rem] bg-white/5 border border-white/5 hover:border-yellow-500/30 transition-all group">
                      <div className="flex items-center gap-4 mb-6">
                        <div className="w-12 h-12 rounded-2xl bg-yellow-500/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                          <img src="/asset/Icons/TelegramStar.png" className="h-8 w-8" alt="stars" loading="lazy" decoding="async" />
                        </div>
                        <div>
                          <h3 className="font-black text-sm uppercase text-white tracking-tight">Telegram Stars</h3>
                          <p className="text-[9px] text-white/30 font-black uppercase">1 ⭐ = 1 звезда</p>
                        </div>
                      </div>
                      <div className="relative mb-4">
                        <input
                          type="number"
                          value={starsAmount}
                          onChange={(e) => setStarsAmount(e.target.value)}
                          className="w-full bg-black/40 border border-white/5 rounded-2xl p-4 pr-12 text-right font-black text-yellow-500 focus:outline-none focus:border-yellow-500/50"
                        />
                        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-white/20 font-black">⭐</span>
                      </div>
                      <button
                        onClick={() => handleStarsPayment()}
                        className="w-full py-4 rounded-2xl bg-yellow-500 text-black font-black uppercase tracking-widest text-xs hover:bg-yellow-600 transition-all active:scale-95 shadow-lg"
                      >
                        ОПЛАТИТЬ {starsAmount} ⭐
                      </button>
                    </div>

                    <div className="p-6 rounded-[2rem] bg-white/5 border border-white/5 hover:border-blue-500/30 transition-all group">
                      <div className="flex items-center gap-4 mb-6">
                        <div className="w-12 h-12 rounded-2xl bg-blue-500/10 flex items-center justify-center group-hover:scale-110 transition-transform">
                          <img src="/asset/Icons/TonCoin.png" className="h-8 w-8" alt="ton" loading="lazy" decoding="async" />
                        </div>
                        <div>
                          <h3 className="font-black text-sm uppercase text-white tracking-tight">TON Coin</h3>
                          <p className="text-[9px] text-white/30 font-black uppercase">1 TON = 100 ⭐</p>
                        </div>
                      </div>
                      <div className="relative mb-2">
                        <input
                          type="number"
                          value={tonAmount}
                          onChange={(e) => setTonAmount(e.target.value)}
                          className="w-full bg-black/40 border border-white/5 rounded-2xl p-4 pr-12 text-right font-black text-blue-400 focus:outline-none focus:border-blue-400/50"
                          step="0.1"
                        />
                        <span className="absolute right-4 top-1/2 -translate-y-1/2 text-white/20 font-black">TON</span>
                      </div>
                      <div className="text-center mb-4">
                         <p className="text-[10px] font-black text-white/40 uppercase tracking-widest">
                           Вы получите: <span className="text-white">{(parseFloat(tonAmount) || 0) * 100}</span> ⭐
                         </p>
                      </div>
                      <button
                        onClick={handleTonPayment}
                        className="w-full py-4 rounded-2xl bg-blue-500 text-white font-black uppercase tracking-widest text-xs hover:bg-blue-600 transition-all active:scale-95 shadow-lg shadow-blue-500/10"
                      >
                        ОПЛАТИТЬ {tonAmount} TON
                      </button>
                    </div>
                  </>
                )}
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
    </MotionConfig>
  );
}
