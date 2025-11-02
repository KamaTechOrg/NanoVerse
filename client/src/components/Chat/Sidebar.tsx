import React, { useState, useEffect } from 'react';
import { Users, Crown, X } from 'lucide-react';
import { Player } from '../../types';

interface SidebarProps {
  activePlayers: Player[];
  selectedPlayer: Player | null;
  onSelectPlayer: (player: Player) => void;
  currentPlayerId: string;
  unreadCounts?: Record<string, number>;
  onMarkRead?: (playerId: string) => void;
  nearestPlayerId?: string;
  onToggle?: () => void;
}

const Sidebar: React.FC<SidebarProps> = ({
  activePlayers,
  selectedPlayer,
  onSelectPlayer,
  currentPlayerId,
  unreadCounts,
  onMarkRead,
  nearestPlayerId,
  onToggle
}) => {
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (toast) {
      const t = setTimeout(() => setToast(null), 2000);
      return () => clearTimeout(t);
    }
  }, [toast]);

  // === שינוי: לא מסננים את עצמי — מציגים גם אותי ברשימה, עם תגית YOU.
  // בנוסף: ממיינים כך שאני ראשון, אחריו nearest, ואז השאר לפי username.
  const list = [...activePlayers].sort((a, b) => {
    const aIsMe = a.id === currentPlayerId ? 1 : 0;
    const bIsMe = b.id === currentPlayerId ? 1 : 0;
    if (aIsMe !== bIsMe) return bIsMe - aIsMe; // me קודם

    const aIsNearest = a.id === nearestPlayerId ? 1 : 0;
    const bIsNearest = b.id === nearestPlayerId ? 1 : 0;
    if (aIsNearest !== bIsNearest) return bIsNearest - aIsNearest; // nearest אחריי

    const aName = (a as any).username ?? a.id;
    const bName = (b as any).username ?? b.id;
    return String(aName).localeCompare(String(bName));
  });

  return (
    <div className="w-full h-full border-r border-slate-700/50 bg-gradient-to-b from-slate-900 to-slate-800 flex flex-col relative shadow-2xl">
      <div className="p-3 sm:p-4 border-b border-slate-700/50 backdrop-blur-sm bg-slate-800/50 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="p-2 rounded-lg bg-gradient-to-br from-cyan-500/20 to-blue-500/20 border border-cyan-500/30">
            <Users size={18} className="text-cyan-400" />
          </div>
          <div className="font-semibold text-white">Players</div>
        </div>
        {onToggle && (
          <button
            onClick={onToggle}
            className="lg:hidden p-1.5 rounded-lg hover:bg-slate-700/50 transition-colors"
          >
            <X size={18} />
          </button>
        )}
      </div>

      <div className="flex-1 overflow-auto p-2 sm:p-3 space-y-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
        {list.length === 0 ? (
          <div className="text-sm text-slate-400 text-center py-8">No players in this chunk.</div>
        ) : (
          list.map((p) => {
            const isSelected = selectedPlayer?.id === p.id;
            const isMe = currentPlayerId === p.id;
            const isNearest = nearestPlayerId === p.id;
            const unread = unreadCounts?.[p.id] ?? 0;

            return (
              <div
                key={p.id}
                onClick={() => {
                  if (isMe) {
                    setToast("You can't chat with yourself");
                    return;
                  }
                  if (!isNearest) {
                    setToast('You can only chat with the nearest player');
                    return;
                  }
                  onSelectPlayer(p);
                  if (unread > 0 && onMarkRead) onMarkRead(p.id);
                }}
                className={[
                  'flex items-center gap-3 p-2.5 sm:p-3 rounded-xl cursor-pointer border transition-all duration-200',
                  isSelected
                    ? 'bg-gradient-to-r from-cyan-600/20 to-blue-600/20 border-cyan-500/50 shadow-lg shadow-cyan-500/20'
                    : 'hover:bg-slate-700/40 border-transparent hover:border-slate-600/50',
                  isNearest ? 'ring-2 ring-emerald-500/40 shadow-emerald-500/20' : '',
                  !isNearest && !isMe ? 'opacity-60' : '',
                ].join(' ')}
              >
                <div className="relative shrink-0">
                  <div className="w-10 h-10 rounded-full bg-gradient-to-br from-slate-700 to-slate-600 flex items-center justify-center border-2 border-slate-600/50 shadow-lg">
                    <Crown size={18} className="text-amber-400" />
                  </div>
                  <span
                    className={`absolute -bottom-0.5 -right-0.5 w-3.5 h-3.5 rounded-full border-2 border-slate-900 shadow-lg
                    {(p as any).status === 'online' ? 'bg-emerald-500' : (p as any).status === 'in-game' ? 'bg-sky-500' : 'bg-slate-500'}`}
                    title={(p as any).status || 'unknown'}
                  />
                </div>

                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate text-white flex items-center gap-1.5">
                    <span className="truncate">{(p as any).username ?? p.id}</span>

                    {isMe && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-400/40 text-emerald-300 whitespace-nowrap shrink-0">
                        you
                      </span>
                    )}

                    {isNearest && (
                      <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-sky-500/20 border border-sky-500/40 text-sky-300 whitespace-nowrap shrink-0">
                        nearest
                      </span>
                    )}
                  </div>

                  {/* מיקום השחקן */}
                  <div className="text-xs text-slate-400 truncate">
                    ({(p as any).row ?? 0}, {(p as any).col ?? 0})
                  </div>
                </div>

                {unread > 0 && (
                  <div className="text-[10px] font-bold bg-gradient-to-r from-rose-600 to-rose-500 text-white px-2 py-1 rounded-full shadow-lg shadow-rose-500/30 shrink-0">
                    {unread}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>

      <div className="p-3 sm:p-4 border-t border-slate-700/50 bg-slate-800/50 backdrop-blur-sm">
        <div className="text-xs text-slate-400 text-center">
          <span className="inline-block">Game Chat</span>
          <span className="mx-1.5">•</span>
          <span className="inline-block">Talk. Play. Enjoy.</span>
        </div>
      </div>

      {toast && (
        <div className="absolute bottom-20 left-1/2 -translate-x-1/2 bg-gradient-to-r from-rose-600 to-rose-500 text-white text-xs sm:text-sm px-4 py-2.5 rounded-xl border border-rose-400/50 shadow-2xl shadow-rose-500/30 backdrop-blur-md animate-fade-in z-50 max-w-[calc(100%-2rem)]">
          {toast}
        </div>
      )}
    </div>
  );
};

export default Sidebar;
