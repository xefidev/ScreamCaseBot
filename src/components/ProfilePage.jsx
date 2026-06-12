import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { DEFAULT_GIFT_IMAGE, getDynamicGiftImage } from '../giftUtils';
import { requestWithdrawal, payWithdrawalFee, showAlert } from '../api';

const PAGE_BG = '#1a1b1e';
const WITHDRAW_THRESHOLD = 500;

const formatValue = (value) => {
  if (value === undefined || value === null) return '0';
  if (value >= 1000) return `${(value / 1000).toFixed(1).replace('.0', '')}k`;
  return value.toString();
};

export default function ProfilePage({
  isPage,
  inventory = [],
  setInventory,
  balance,
  setBalance
}) {
  const [user, setUser] = React.useState(null);
  const [sellingIds, setSellingIds] = useState(new Set());
  const [isSellingAll, setIsSellingAll] = useState(false);
  const [withdrawItem, setWithdrawItem] = useState(null);
  const [withdrawStep, setWithdrawStep] = useState('confirm'); // confirm | paying | error
  const [withdrawLoading, setWithdrawLoading] = useState(false);

  React.useEffect(() => {
    const userData = window.Telegram?.WebApp?.initDataUnsafe?.user;
    if (userData) setUser(userData);
  }, []);

  const triggerHaptic = (type = 'heavy') => {
    const haptic = window.Telegram?.WebApp?.HapticFeedback;
    if (!haptic) return;
    if (type === 'success') haptic.notificationOccurred('success');
    else haptic.impactOccurred(type);
  };

  const handleSell = (item) => {
    if (sellingIds.has(item.id)) return;
    triggerHaptic();
    if (!setInventory || !setBalance || !item?.id) return;

    setSellingIds(prev => new Set(prev).add(item.id));

    setInventory((prev) => {
      const itemExists = prev.some(i => i.id === item.id);
      if (!itemExists) return prev;
      return prev.filter((currentItem) => currentItem.id !== item.id);
    });

    const sellPrice = Number(item.price || item.cost) || 0;
    if (sellPrice > 0) {
      setBalance((prev) => prev + sellPrice);
      triggerHaptic('success');
    }
  };

  const handleSellAll = () => {
    if (inventory.length === 0 || isSellingAll) return;
    triggerHaptic('heavy');
    setIsSellingAll(true);

    const totalValue = inventory.reduce((sum, item) => sum + (Number(item.price || item.cost) || 0), 0);

    setInventory([]);
    setBalance(prev => prev + totalValue);
    triggerHaptic('success');

    setTimeout(() => setIsSellingAll(false), 1000);
  };

  const openWithdraw = (item) => {
    triggerHaptic('heavy');
    setWithdrawItem(item);
    setWithdrawStep('confirm');
  };

  const closeWithdraw = () => {
    setWithdrawItem(null);
    setWithdrawStep('confirm');
    setWithdrawLoading(false);
  };

  const handlePayFee = async (method) => {
    if (!user?.id || !withdrawItem?.id || withdrawLoading) return;
    setWithdrawLoading(true);
    triggerHaptic('heavy');

    try {
      const result = await payWithdrawalFee(user.id, withdrawItem.id, method);
      if (!result.ok) {
        showAlert('❌ Не удалось создать счёт. Попробуйте позже.');
        setWithdrawLoading(false);
        return;
      }

      if (method === 'stars' && result.invoice_link) {
        window.Telegram?.WebApp?.openInvoice?.(result.invoice_link, (status) => {
          setWithdrawLoading(false);
          if (status === 'paid') {
            // Per spec: after payment, show "error, stars credited to bot balance"
            setWithdrawStep('error');
            triggerHaptic('success');
          } else if (status === 'cancelled' || status === 'failed') {
            closeWithdraw();
          }
        });
      } else if (method === 'ton') {
        // TON flow - open external wallet or show instructions
        if (result.wallet) {
          const tonLink = `ton://transfer/${result.wallet}?amount=5000000000&text=${encodeURIComponent(result.comment || '')}`;
          window.Telegram?.WebApp?.openLink?.(tonLink) || window.open(tonLink, '_blank');
          // After short delay, simulate the "credited to bot" outcome
          setTimeout(() => {
            setWithdrawStep('error');
            setWithdrawLoading(false);
            triggerHaptic('success');
          }, 2000);
        } else {
          showAlert('❌ TON-кошелёк временно недоступен. Попробуйте оплату звёздами.');
          setWithdrawLoading(false);
        }
      }
    } catch (e) {
      console.error('Withdraw pay error:', e);
      showAlert('❌ Сетевая ошибка. Попробуйте позже.');
      setWithdrawLoading(false);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-4 pb-24" style={{ backgroundColor: PAGE_BG, WebkitOverflowScrolling: 'touch' }}>
      <div className="mb-6 flex justify-between items-center">
        <h2 className="text-2xl font-black uppercase tracking-widest text-white">Профиль</h2>
        {inventory.length > 0 && (
          <button
            onClick={handleSellAll}
            disabled={isSellingAll}
            className="px-4 py-2 rounded-xl bg-red-500/10 border border-red-500/30 text-red-400 text-[10px] font-black uppercase tracking-widest disabled:opacity-50"
          >
            {isSellingAll ? 'ПРОДАЖА...' : 'ПРОДАТЬ ВСЕ'}
          </button>
        )}
      </div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25 }} className="glass-panel relative mb-6 overflow-hidden p-6 bg-white/[0.02] border-white/10" style={{ willChange: 'transform' }}>
        <div className="relative z-10 flex items-center gap-4">
          <div className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-full border border-white/10 bg-white/5 shadow-2xl" style={{ marginTop: '12px' }}>
            {user?.photo_url ? (
              <img src={user.photo_url} alt="Avatar" className="h-full w-full object-cover" onError={(e) => { e.currentTarget.style.display='none'; }} loading="lazy" decoding="async" />
            ) : (
              <span className="text-3xl font-black text-white/20">{user?.first_name?.charAt(0) || '?'}</span>
            )}
          </div>
          <div className="min-w-0 flex-1">
            <h3 className="truncate text-xl font-black uppercase leading-tight tracking-tight text-white">{user?.first_name || 'Игрок'}</h3>
            <div className="mt-2 flex items-center gap-1.5 px-3 py-1 rounded-lg bg-yellow-500/10 border border-yellow-500/20 w-fit">
               <span className="text-sm font-black text-yellow-500">{formatValue(balance)}</span>
               <img src="/asset/Icons/TelegramStar.png" className="h-4 w-4" alt="Stars" onError={(e) => { e.currentTarget.src = '/asset/Gifts/Case.webp'; }} loading="lazy" decoding="async" />
            </div>
            <p className="mt-2 text-[8px] text-white/20 font-black uppercase tracking-widest">ID: {user?.id || '0'}</p>
          </div>
        </div>
      </motion.div>

      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.25, delay: 0.05 }} className="glass-panel p-6 bg-white/[0.02] border-white/10" style={{ willChange: 'transform' }}>
        <h4 className="mb-4 text-xs font-black uppercase tracking-widest text-white/40">Инвентарь ({inventory?.length || 0})</h4>
        {!inventory || inventory.length === 0 ? (
          <div className="py-12 text-center border border-dashed border-white/5 rounded-3xl"><p className="text-[10px] font-black uppercase tracking-[0.2em] text-white/10">Пусто</p></div>
        ) : (
          <div className="grid grid-cols-2 gap-3">
            {inventory.map((item) => {
              const itemPrice = Number(item.price || item.cost) || 0;
              const canWithdraw = itemPrice >= WITHDRAW_THRESHOLD;
              return (
                <div key={item.id} className="flex flex-col items-center justify-between rounded-3xl border border-white/5 bg-white/[0.02] p-4 shadow-xl group" style={{ willChange: 'auto' }}>
                  <img src={getDynamicGiftImage(item)} alt="Gift" className="mb-3 h-20 w-20 object-contain" onError={(e) => { e.currentTarget.src = DEFAULT_GIFT_IMAGE; }} loading="lazy" decoding="async" />
                  <p className="mb-3 w-full truncate text-center text-[9px] font-black uppercase tracking-tight text-white/60">{item.name || 'Gift'}</p>
                  {canWithdraw && (
                    <button
                      onClick={() => openWithdraw(item)}
                      className="mb-2 w-full rounded-xl border border-emerald-400/40 bg-emerald-500/15 py-2 text-[8px] font-black uppercase tracking-widest text-emerald-300 active:opacity-70"
                    >
                      ⬆ Вывести
                    </button>
                  )}
                  <button
                    onClick={() => handleSell(item)}
                    disabled={sellingIds.has(item.id)}
                    className="w-full rounded-xl border border-red-500/30 bg-red-500/10 py-2 text-[8px] font-black uppercase tracking-widest text-red-400 disabled:opacity-50 active:opacity-70"
                  >
                    {sellingIds.has(item.id) ? 'ПРОДАНО' : `Продать: ${itemPrice}`}
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </motion.div>

      <AnimatePresence>
        {withdrawItem && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/80 backdrop-blur-sm"
            onClick={closeWithdraw}
          >
            <motion.div
              initial={{ scale: 0.9, y: 20 }}
              animate={{ scale: 1, y: 0 }}
              exit={{ scale: 0.9, y: 20 }}
              transition={{ duration: 0.2 }}
              onClick={(e) => e.stopPropagation()}
              className="w-full max-w-sm rounded-3xl border border-white/10 bg-[#1a1b1e] p-6 shadow-2xl"
              style={{ willChange: 'transform' }}
            >
              {withdrawStep === 'confirm' && (
                <>
                  <div className="mb-4 text-center">
                    <img src={getDynamicGiftImage(withdrawItem)} alt={withdrawItem.name} className="mx-auto mb-3 h-24 w-24 object-contain" />
                    <h3 className="text-base font-black uppercase tracking-wider text-white">{withdrawItem.name || 'Gift'}</h3>
                    <p className="mt-1 text-xs text-white/40">Стоимость: {Number(withdrawItem.price || withdrawItem.cost) || 0}⭐</p>
                  </div>
                  <div className="mb-4 rounded-2xl border border-yellow-500/30 bg-yellow-500/10 p-4">
                    <p className="text-[11px] font-black uppercase tracking-wider text-yellow-300 mb-2">⚠️ За комиссию</p>
                    <p className="text-xs text-white/70 leading-relaxed">
                      Для вывода подарка необходимо оплатить комиссию:
                    </p>
                    <ul className="mt-2 space-y-1 text-xs text-white/80">
                      <li>• <b className="text-yellow-300">50⭐</b> настоящих звёзд Telegram</li>
                      <li>• или <b className="text-cyan-300">5 TON</b></li>
                    </ul>
                  </div>
                  <div className="space-y-2">
                    <button
                      onClick={() => handlePayFee('stars')}
                      disabled={withdrawLoading}
                      className="w-full rounded-2xl border border-yellow-500/40 bg-yellow-500/15 py-3 text-xs font-black uppercase tracking-widest text-yellow-300 active:opacity-70 disabled:opacity-50"
                    >
                      {withdrawLoading ? 'Подождите...' : 'Оплатить 50⭐ Telegram Stars'}
                    </button>
                    <button
                      onClick={() => handlePayFee('ton')}
                      disabled={withdrawLoading}
                      className="w-full rounded-2xl border border-cyan-400/40 bg-cyan-500/15 py-3 text-xs font-black uppercase tracking-widest text-cyan-300 active:opacity-70 disabled:opacity-50"
                    >
                      {withdrawLoading ? 'Подождите...' : 'Оплатить 5 TON'}
                    </button>
                    <button
                      onClick={closeWithdraw}
                      className="w-full rounded-2xl border border-white/10 bg-white/[0.02] py-2 text-[10px] font-black uppercase tracking-widest text-white/40 active:opacity-70"
                    >
                      Отмена
                    </button>
                  </div>
                </>
              )}

              {withdrawStep === 'error' && (
                <>
                  <div className="mb-4 text-center">
                    <div className="mx-auto mb-3 flex h-16 w-16 items-center justify-center rounded-full bg-red-500/20 border border-red-500/40">
                      <span className="text-3xl">⚠️</span>
                    </div>
                    <h3 className="text-base font-black uppercase tracking-wider text-white mb-2">Произошла ошибка</h3>
                    <p className="text-xs text-white/70 leading-relaxed">
                      Звёзды зачислены на баланс бота. Попробуйте позже.
                    </p>
                  </div>
                  <button
                    onClick={closeWithdraw}
                    className="w-full rounded-2xl border border-white/10 bg-white/5 py-3 text-xs font-black uppercase tracking-widest text-white/70 active:opacity-70"
                  >
                    Понятно
                  </button>
                </>
              )}
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
