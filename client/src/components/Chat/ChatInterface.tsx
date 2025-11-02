import React, {
  useState,
  useRef,
  useEffect,
  useMemo,
  useCallback,
} from "react";
import { Send, Smile, Settings, X, Quote, Users } from "lucide-react";
import MessageItem from "./MessageItem";
import EmojiPicker from "./EmojiPicker";
import { Message, Player } from "../../types";

type Reaction = "up" | "down" | null;

interface ChatInterfaceProps {
  messages: Message[];
  selectedPlayer: Player | null;
  currentPlayerId: string;
  onSendMessage: (message: string, quotedMessage?: Message) => void;
  onReactMessage: (messageId: string, reaction: Reaction) => void;
  onDeleteMessage: (messageId: string) => void;

  // live players in the chunk
  playersInChunk?: {
    id: string;
    username?: string;
    row: number;
    col: number;
    chunk_id?: string;
  }[];
  nearestPlayerId?: string;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  messages,
  selectedPlayer,
  currentPlayerId,
  onSendMessage,
  onReactMessage,
  onDeleteMessage,
  playersInChunk = [],
  nearestPlayerId,
}) => {
  const [input, setInput] = useState("");
  const [quotedMessage, setQuotedMessage] = useState<Message | undefined>(undefined);
  const [showEmojiPicker, setShowEmojiPicker] = useState(false);
  const [showPlayers, setShowPlayers] = useState(false);
  const endRef = useRef<HTMLDivElement | null>(null);

  const msgText = (m?: Message) =>
    !m ? "" : (m as any).deleted ? "Message deleted" : m.message ?? "";

  const canSend = useMemo(() => {
    if (!selectedPlayer) return false;
    if (selectedPlayer.id === currentPlayerId) return false;
    if (!nearestPlayerId) return true;
    return selectedPlayer.id === nearestPlayerId;
  }, [selectedPlayer, nearestPlayerId, currentPlayerId]);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSend = useCallback(() => {
    const text = input.trim();
    if (!text) return;

    if (!selectedPlayer) return;
    if (selectedPlayer.id === currentPlayerId) {
      alert("You can't chat with yourself.");
      return;
    }
    if (nearestPlayerId && selectedPlayer.id !== nearestPlayerId) {
      alert("You can only chat with the nearest player in your chunk.");
      return;
    }

    onSendMessage(text, quotedMessage);
    setInput("");
    setQuotedMessage(undefined);
  }, [
    input,
    quotedMessage,
    onSendMessage,
    selectedPlayer,
    currentPlayerId,
    nearestPlayerId,
  ]);

  const handleEmojiSelect = (emoji: string) => setInput((v) => v + emoji);
  const handleGifSelect = (gifUrl: string) => setInput((v) => v + ` ${gifUrl} `);

  return (
    <div className="relative flex flex-col h-full min-h-0 bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900">
      {/* Toolbar */}
      <div className="px-3 sm:px-4 py-3 border-b border-slate-700 bg-slate-800 flex items-center justify-between">
        <div className="text-xs sm:text-sm flex items-center gap-2 min-w-0">
          {selectedPlayer ? (
            <>
              <span className="text-slate-400 hidden sm:inline">Chat with</span>
              <span className="font-semibold text-white truncate">
                {selectedPlayer.username}
              </span>
              {selectedPlayer.id === currentPlayerId && (
                <span className="text-[10px] sm:text-xs px-1.5 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300 whitespace-nowrap">
                  you
                </span>
              )}
              {nearestPlayerId &&
                selectedPlayer.id === nearestPlayerId &&
                selectedPlayer.id !== currentPlayerId && (
                  <span className="text-[10px] sm:text-xs px-1.5 py-0.5 rounded-full bg-sky-500/20 border border-sky-500/40 text-sky-300 whitespace-nowrap">
                    nearest
                  </span>
                )}
            </>
          ) : (
            <span className="text-slate-400">Select a player</span>
          )}
        </div>

        {/* כפתורים מימין: People + Settings */}
        <div className="flex items-center gap-1.5 sm:gap-2">
          <button
            onClick={() => setShowPlayers(true)}
            title="Players in chunk"
            className="p-1.5 sm:p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
          >
            <Users size={18} className="sm:w-[18px] sm:h-[18px]" />
          </button>

          <button
            className="p-1.5 sm:p-2 rounded-lg hover:bg-slate-700/50 transition-colors"
            title="Settings"
          >
            <Settings size={18} className="sm:w-[18px] sm:h-[18px]" />
          </button>
        </div>
      </div>

      {/* Messages – תופס 100% רוחב/גובה */}
      <div className="flex-1 w-full min-w-0 overflow-auto p-3 sm:p-4 space-y-2 scrollbar-thin scrollbar-thumb-slate-700 scrollbar-track-transparent">
        {messages.map((m, idx) => {
          const prevMessage = idx > 0 ? messages[idx - 1] : null;
          const nextMessage = idx < messages.length - 1 ? messages[idx + 1] : null;
          const isOwn = m.from === currentPlayerId;

        return (
            <MessageItem
              key={m.id}
              message={m}
              prevMessage={prevMessage}
              nextMessage={nextMessage}
              isOwn={isOwn}
              currentPlayerId={currentPlayerId}
              onReact={(messageId, reaction) => onReactMessage(messageId, reaction)}
              onDelete={(id) => onDeleteMessage(id)}
              onQuote={() => setQuotedMessage(m)}
            />
          );
        })}
        <div ref={endRef} />
      </div>

      {/* Quoted preview */}
      {quotedMessage && (
        <div className="px-3 sm:px-4 py-2 border-t border-slate-700 bg-slate-800 text-xs flex items-center gap-2">
          <Quote size={14} className="text-slate-400 shrink-0" />
          <div className="flex-1 truncate text-slate-300">
            Replying to{" "}
            <span className="font-semibold text-white">{quotedMessage.from}</span>:{" "}
            {msgText(quotedMessage)}
          </div>
          <button
            className="p-1 rounded hover:bg-slate-700 shrink-0"
            onClick={() => setQuotedMessage(undefined)}
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Input bar */}
      <div className="p-2 sm:p-3 border-t border-slate-700 bg-slate-800 flex items-center gap-1.5 sm:gap-2">
        <button
          className="p-1.5 sm:p-2 rounded-lg hover:bg-slate-700/50 transition-colors shrink-0"
          title="Emoji / GIF"
          onClick={() => setShowEmojiPicker((v) => !v)}
        >
          <Smile size={16} className="sm:w-[18px] sm:h-[18px]" />
        </button>

        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              if (canSend) handleSend();
            }
          }}
          className="flex-1 bg-slate-800 border border-slate-700 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-sky-500/50 focus:border-sky-500/50 transition-all placeholder:text-slate-500"
          placeholder={
            selectedPlayer
              ? canSend
                ? `Message ${selectedPlayer.username}...`
                : `Only nearest player`
              : "Select a player..."
          }
        />

        <button
          onClick={handleSend}
          disabled={!input.trim() || !canSend}
          className={`px-3 py-2 rounded-lg flex items-center gap-1.5 sm:gap-2 transition-all shrink-0 ${
            !input.trim() || !canSend
              ? "bg-slate-700/50 text-slate-500 cursor-not-allowed"
              : "bg-gradient-to-r from-cyan-600 to-blue-600 hover:from-cyan-500 hover:to-blue-500 text-white shadow-lg shadow-cyan-500/20"
          }`}
        >
          <Send size={14} className="sm:w-4 sm:h-4" />
          <span className="hidden sm:inline text-sm font-medium">Send</span>
        </button>
      </div>

      {/* Emoji/GIF */}
      {showEmojiPicker && (
        <EmojiPicker
          onEmojiSelect={handleEmojiSelect}
          onGifSelect={handleGifSelect}
          onClose={() => setShowEmojiPicker(false)}
        />
      )}

      {/* Players panel – מעל חלון הצ'אט בלבד */}
      {showPlayers && (
        <div
          className="
            absolute
            left-2 right-2
            top-14
            bottom-16
            z-50
            pointer-events-auto
          "
        >
          <div className="
            h-full w-full
            bg-slate-900 border border-slate-700 rounded-2xl shadow-xl
            flex flex-col overflow-hidden min-h-0
          ">
            {/* כותרת */}
            <div className="flex items-center justify-between px-3 py-2 border-b border-slate-700 shrink-0">
              <div className="font-semibold text-white">Players in this chunk</div>
              <button
                className="p-1.5 rounded hover:bg-slate-700/60"
                onClick={() => setShowPlayers(false)}
              >
                <X size={18} />
              </button>
            </div>

            {/* רשימה – גלילה בתוך הפאנל */}
            <ul className="flex-1 overflow-y-auto space-y-2 p-3 pr-2 scrollbar-thin scrollbar-thumb-slate-700">
              {playersInChunk.map((p) => {
                const isMe = p.id === currentPlayerId;
                const isNearest = p.id === (nearestPlayerId || "");
                return (
                  <li
                    key={p.id}
                    className={`flex items-center justify-between p-3 rounded-xl border transition-all
                      ${isNearest
                        ? "border-emerald-500/60 bg-emerald-500/10 shadow-lg shadow-emerald-500/20"
                        : "border-slate-600/50 bg-slate-800/50"}
                      ${!isMe && !isNearest ? "opacity-60" : ""}`}
                  >
                    <span className="text-sm font-medium">
                      {p.username ?? p.id}{" "}
                      {isMe && (
                        <span className="ml-1 text-xs px-1.5 py-0.5 rounded-full bg-emerald-500/20 border border-emerald-500/40 text-emerald-300">
                          you
                        </span>
                      )}
                    </span>
                    <span className="text-xs text-slate-400">
                      ({p.row},{p.col})
                    </span>
                  </li>
                );
              })}
            </ul>
          </div>
        </div>
      )}
    </div>
  );
};

export default ChatInterface;
