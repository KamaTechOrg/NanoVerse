import React, { useEffect, useState, useMemo } from "react";
import { X, Users } from "lucide-react";
import { useSharedWebSocket } from "../../context/WebSocketProvider";
import Sidebar from "./Sidebar";
import ChatInterface from "./ChatInterface";
import CustomizationPanel from "./CustomizationPanel";
import type { ChatTheme } from "../../types";

export type LocalPlayer = {
  id: string;
  username?: string;
  email?: string;
  row: number;
  col: number;
  chunk_id?: string;
};

interface ChatRootProps {
  onClose?: () => void;
  playerId: string;
  currentChunkId?: string | null;
  playersInChunk: LocalPlayer[];
}

const ChatRoot: React.FC<ChatRootProps> = ({
  onClose,
  playerId,
  currentChunkId,
  playersInChunk,
}) => {
  const {
    messages,
    selectedPlayer,
    sendMessage,
    selectPlayer,
    reactToMessage,
    deleteMessage,
    unreadCounts,
    markRead,
  } = useSharedWebSocket();

  const meId = playerId;
  const chunkId = currentChunkId ?? playersInChunk[0]?.chunk_id ?? "chunk_0_0";

  const me = useMemo(
    () => playersInChunk.find((p) => p.id === meId) || null,
    [playersInChunk, meId]
  );

  const nearestLocal = useMemo(() => {
    if (!me) return null;
    let best: LocalPlayer | null = null;
    let bestD = Infinity;
    for (const p of playersInChunk) {
      if (p.id === me.id) continue;
      const d = Math.hypot(
        (p.row ?? 0) - (me.row ?? 0),
        (p.col ?? 0) - (me.col ?? 0)
      );
      if (d < bestD) {
        bestD = d;
        best = p;
      }
    }
    return best;
  }, [me, playersInChunk]);

  const nearestPlayerId = nearestLocal?.id;

  const sidebarPlayers = useMemo(() => {
    return playersInChunk.map((p) => ({
      id: p.id,
      username: p.username ?? p.id,
      email: p.email ?? "",
      status: "online",
      row: p.row,
      col: p.col,
    }));
  }, [playersInChunk]);

  useEffect(() => {
    if (!nearestLocal) return;
    if (!selectedPlayer || selectedPlayer.id !== nearestLocal.id) {
      selectPlayer({
        id: nearestLocal.id,
        username: nearestLocal.username ?? nearestLocal.id,
      } as any);
    }
  }, [nearestLocal, selectedPlayer, selectPlayer]);

  // keep local copy so we can clear on "clearChat"
  const [localMessages, setLocalMessages] = useState(messages);
  useEffect(() => setLocalMessages(messages), [messages]);

  useEffect(() => {
    const handleClear = () => {
      console.log(
        "[ChatRoot] clearing messages because player is alone in chunk"
      );
      setLocalMessages([]);
      selectPlayer(null as any);
    };
    window.addEventListener("clearChat", handleClear);
    return () => window.removeEventListener("clearChat", handleClear);
  }, [selectPlayer]);

  const [showCustomization, setShowCustomization] = useState(false);
  const [currentTheme, setCurrentTheme] = useState<ChatTheme>({
    name: "Cyber Blue",
    primaryColor: "#0ea5e9",
    secondaryColor: "#06b6d4",
    accentColor: "#3b82f6",
    backgroundColor: "#0f172a",
    cardColor: "#1e293b",
    textColor: "#f8fafc",
  });

  // sidebar/modal with players list (closed by default to feel like “real chat”)
  const [sidebarOpen, setSidebarOpen] = useState(false);

  return (
    <div
      className="relative flex h-full w-full overflow-hidden bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900"
      style={{ color: currentTheme.textColor }}
    >
      {/* Sidebar: render only when open (mobile modal + desktop panel) */}
      {sidebarOpen && (
        <>
          <div className="fixed lg:relative inset-y-0 left-0 z-30 w-64 sm:w-72 lg:w-80">
            <Sidebar
              activePlayers={sidebarPlayers as any}
              nearestPlayerId={nearestPlayerId}
              selectedPlayer={selectedPlayer}
              onSelectPlayer={selectPlayer}
              currentPlayerId={meId}
              unreadCounts={unreadCounts}
              onMarkRead={markRead}
              onToggle={() => setSidebarOpen(false)}
            />
          </div>
          {/* backdrop for mobile */}
          <div
            className="fixed inset-0 bg-black/50 backdrop-blur-sm z-20 lg:hidden"
            onClick={() => setSidebarOpen(false)}
          />
        </>
      )}

      {/* Messages area */}
      <div className="flex-1 h-full flex flex-col min-w-0">
        <div className="px-3 sm:px-4 py-3 border-b border-slate-700 backdrop-blur-sm bg-slate-800 flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 min-w-0">
            {/* People button toggles list above chat only */}
            <button
              onClick={() => setSidebarOpen((v) => !v)}
              className="p-2 rounded-lg hover:bg-slate-700/50 transition-colors shrink-0"
              title={sidebarOpen ? "Hide players" : "Show players"}
            >
              <Users className="w-5 h-5" />
            </button>
            <div className="font-semibold text-lg bg-gradient-to-r from-cyan-400 to-blue-400 bg-clip-text text-transparent truncate">
              Game Chat
            </div>
          </div>
          <div className="flex items-center gap-1.5 sm:gap-2 shrink-0">
            <button
              onClick={() => setShowCustomization((v) => !v)}
              className="bg-slate-700/50 hover:bg-slate-600/50 px-2.5 sm:px-3 py-1.5 rounded-lg transition-all text-xs sm:text-sm font-medium"
            >
              Theme
            </button>
            {onClose && (
              <button
                onClick={onClose}
                className="bg-slate-700/50 hover:bg-slate-600/50 p-2 rounded-lg transition-all"
                title="Close chat"
              >
                <X size={18} />
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 min-h-0">
          <ChatInterface
            messages={localMessages}
            selectedPlayer={selectedPlayer}
            currentPlayerId={meId}
            onSendMessage={(text, quoted) => {
              if (!selectedPlayer) return;
              if (selectedPlayer.id === meId) {
                alert("You can't chat with yourself.");
                return;
              }
              if (nearestPlayerId && selectedPlayer.id !== nearestPlayerId) {
                alert("You can only chat with the nearest player in your chunk.");
                return;
              }
              sendMessage(text, quoted, { chunkId });
            }}
            onReactMessage={(messageId, reaction) =>
              reactToMessage(messageId, reaction)
            }
            onDeleteMessage={deleteMessage}
            playersInChunk={playersInChunk as any}
            nearestPlayerId={nearestPlayerId}
          />
        </div>
      </div>

      {showCustomization && (
        <CustomizationPanel
          currentTheme={currentTheme}
          themes={[currentTheme]}
          onThemeChange={setCurrentTheme}
          onClose={() => setShowCustomization(false)}
        />
      )}
    </div>
  );
};

export default ChatRoot;
