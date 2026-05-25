import React, { useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { Gift, Star } from 'lucide-react';
import { fetchQuests, claimQuest } from '../api';

export default function QuestsTab({ userId, onBalanceUpdate }) {
  const [quests, setQuests] = useState(null);

  const loadQuests = async () => {
    if (!userId) return;
    const data = await fetchQuests(userId);
    setQuests(data);
  };

  useEffect(() => {
    loadQuests();
  }, [userId]);

  const handleClaim = async (questId) => {
    try {
      // Optimiztic UI update or just wait for response
      const res = await claimQuest(userId, questId);
      if (res && res.success) {
        // Trigger haptic if available
        try { window?.Telegram?.WebApp?.HapticFeedback?.notificationOccurred('success'); } catch(e){}
        
        // Refresh balance in header
        if (onBalanceUpdate) {
            onBalanceUpdate();
        }
        
        // Update local state to avoid refetch
        setQuests(prev => prev.map(q => q.id === questId ? { ...q, is_claimed: true } : q));
      }
    } catch (e) {
      console.error('Failed to claim quest:', e);
    }
  };

  return (
    <div className="h-full overflow-y-auto p-6 pb-24" style={{ backgroundColor: '#1a1b1e' }}>
      <h2 className="mb-6 font-rounded text-3xl font-black uppercase tracking-tight text-white flex items-center gap-3">
        <TrophyIcon className="text-yellow-500" />
        Награды и Квесты
      </h2>
      
      <div className="space-y-5">
        {quests ? (
          quests.length > 0 ? (
            quests.map((a, i) => {
            const goal = a?.goal || 1;
            const progress = Math.min(a?.progress || 0, goal);
            const percent = (progress / goal) * 100;
            const isComplete = progress >= goal;

            return (
              <motion.div 
                key={a?.id || i}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.1 }}
                className={`relative overflow-hidden rounded-[2rem] p-5 shadow-2xl transition-all ${
                  isComplete && !a?.is_claimed 
                    ? 'bg-gradient-to-br from-yellow-500/20 to-black/60 border border-yellow-500/50' 
                    : 'bg-white/5 border border-white/10'
                }`}
              >
                {/* Glow Background for completed items */}
                {isComplete && !a?.is_claimed && (
                  <div className="absolute inset-0 bg-yellow-500/10 pointer-events-none animate-pulse" />
                )}

                <div className="relative z-10 flex gap-4 items-center mb-4">
                  {/* Reward Icon / Accent */}
                  <div className={`flex shrink-0 items-center justify-center w-16 h-16 rounded-2xl ${
                    isComplete && !a?.is_claimed
                      ? 'bg-gradient-to-br from-yellow-400 to-yellow-600 shadow-[0_0_20px_rgba(234,179,8,0.5)] text-black'
                      : 'bg-black/40 border border-white/10 text-white/50'
                  }`}>
                    {a.reward > 10 ? <Gift size={32} /> : <Star size={32} />}
                  </div>

                  {/* Title and Info */}
                  <div className="flex-1">
                    <h3 className="font-black text-lg uppercase tracking-tighter text-white mb-1">
                      {a?.title || 'Достижение'}
                    </h3>
                    <div className="flex items-center gap-2">
                      <span className="flex items-center gap-1 bg-yellow-500/20 text-yellow-500 text-[10px] px-2 py-1 rounded-md font-black uppercase">
                        <Star size={12} /> +{a?.reward || 0} Звёзд
                      </span>
                    </div>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="mb-4">
                  <div className="flex justify-between mb-1.5 px-1">
                    <span className="text-[10px] font-black text-white/40 uppercase tracking-widest">Прогресс</span>
                    <span className="text-[10px] font-black text-white uppercase tracking-widest">
                      {progress} / {goal}
                    </span>
                  </div>
                  <div className="h-2 w-full bg-black/50 rounded-full overflow-hidden border border-white/5">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${percent}%` }}
                      transition={{ duration: 1, ease: 'easeOut' }}
                      className={`h-full ${
                        isComplete 
                          ? 'bg-yellow-500 shadow-[0_0_10px_rgba(234,179,8,0.8)]' 
                          : 'bg-white/30'
                      }`}
                    />
                  </div>
                </div>

                {/* Action Button */}
                {a?.is_claimed ? (
                  <div className="w-full py-3 rounded-xl bg-black/40 border border-white/5 text-center flex items-center justify-center gap-2">
                    <Star size={14} className="text-white/20" />
                    <span className="text-[10px] font-black uppercase text-white/20 tracking-widest">Награда получена</span>
                  </div>
                ) : (
                  <button
                    onClick={() => handleClaim(a?.id)}
                    disabled={!isComplete}
                    className={`relative overflow-hidden w-full py-3.5 rounded-xl font-black text-xs uppercase tracking-widest transition-all ${
                      isComplete
                        ? 'bg-yellow-500 text-black shadow-lg shadow-yellow-500/20 cursor-pointer hover:bg-yellow-400 hover:scale-[1.02] active:scale-95 animate-[pulse_2s_ease-in-out_infinite]'
                        : 'bg-white/5 text-white/20 cursor-not-allowed'
                    }`}
                  >
                    Забрать награду
                  </button>
                )}
              </motion.div>
            );
          })
        ) : (
           <p className="text-white/50 text-center py-10 font-bold uppercase text-sm">Нет доступных квестов.</p>
        )) : (
           <p className="text-white/50 text-center py-10 font-bold uppercase text-sm animate-pulse">Загрузка квестов...</p>
        )}
      </div>
    </div>
  );
}

// Small helper icon component
const TrophyIcon = ({ className }) => (
  <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className={`w-8 h-8 ${className}`}>
    <path d="M6 9H4.5a2.5 2.5 0 0 1 0-5H6" />
    <path d="M18 9h1.5a2.5 2.5 0 0 0 0-5H18" />
    <path d="M4 22h16" />
    <path d="M10 14.66V17c0 .55-.47.98-.97 1.21C7.85 18.75 7 20.24 7 22" />
    <path d="M14 14.66V17c0 .55.47.98.97 1.21C16.15 18.75 17 20.24 17 22" />
    <path d="M18 2H6v7a6 6 0 0 0 12 0V2Z" />
  </svg>
);
