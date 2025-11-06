

import React, { useEffect, useState, useCallback, useMemo } from "react";
import { Wifi, WifiOff, Users, Gamepad2, MessageCircle, X, HelpCircle } from "lucide-react";
import { authStorage } from "../utils/auth";
import { MessageBubble } from "./MessageBubble";
import { MessageInput } from "./MessageInput";
import ChatRoot from "./Chat/ChatRoot";
import { InstructionsModal } from "./InstructionsModal";
import { useSharedWebSocket } from "../context/WebSocketProvider";

interface GameState {
  w: number;
  h: number;
  data: number[];
  chunk_id?: string;
}

type PlayerInChunk = {
  id: string;
  row: number;
  col: number;
  color: number; // ✅ now received from the server
};

const SYSTEM_TREASURE = "A player hid a treasure";

const QuoteToast: React.FC<{ text: string; onClose: () => void }> = ({ text, onClose }) => {
  return (
    <div
      className="fixed bottom-8 left-1/2 -translate-x-1/2 z-30 max-w-[90vw] sm:max-w-[70vw] w-full sm:w-[680px] px-4 sm:px-5 py-4
                 bg-white/95 text-slate-800 rounded-2xl shadow-2xl border border-slate-200
                 backdrop-blur-sm"
      role="status"
      aria-live="polite"
    >
      <div className="flex items-start gap-3">
        <div className="mt-0.5 h-full border-l-4 border-purple-400 rounded-full" aria-hidden />
        <div className="flex-1 min-w-0">
          <div className="text-xs sm:text-sm uppercase tracking-wide text-slate-500">
            Message found here
          </div>
          <blockquote className="mt-1 text-base sm:text-lg leading-snug text-slate-900 break-words">
            "{text}"
          </blockquote>
        </div>
        <button
          onClick={onClose}
          className="shrink-0 inline-flex items-center justify-center rounded-full p-1 hover:bg-slate-100 transition"
          aria-label="Close"
          title="Close"
        >
          <X size={18} />
        </button>
      </div>
    </div>
  );
};

const VoxelGrid: React.FC = () => {
  const { isConnected, sendCommand } = useSharedWebSocket();

  const [gameState, setGameState] = useState<GameState | null>(null);
  const [playerCount, setPlayerCount] = useState(0);
  const [lastAction, setLastAction] = useState("");
  const [notice, setNotice] = useState<string | null>(null);
  const [showChat, setShowChat] = useState(false);
  const [showInstructions, setShowInstructions] = useState(false);
  const [players, setPlayers] = useState<PlayerInChunk[]>([]);
  const [showMessageInput, setShowMessageInput] = useState(false);
  const [currentMessage, setCurrentMessage] = useState<any>(null);
  const [error, setError] = useState<string | null>(null);
  const [quoteText, setQuoteText] = useState<string | null>(null);

  useEffect(() => {
    if (!quoteText) return;
    const t = setTimeout(() => setQuoteText(null), 6000);
    return () => clearTimeout(t);
  }, [quoteText]);

  // Handle server messages
  useEffect(() => {
    const handleGameUpdate = (ev: CustomEvent) => {
      const data = ev.detail;

      if (data.type === "matrix") {
        setGameState({
          w: data.w,
          h: data.h,
          data: data.data,
          chunk_id: data.chunk_id,
        });

        const newPlayers = Array.isArray(data.players) ? data.players : [];
        setPlayers(newPlayers);
        setPlayerCount(data.total_players ?? newPlayers.length);

        const newChunkId = String(data.chunk_id || "");
        if (newChunkId && newChunkId !== sessionStorage.getItem("current_chunk_id")) {
          sessionStorage.setItem("current_chunk_id", newChunkId);
          window.dispatchEvent(new Event("chunkChanged"));
        }

        // ✅ Clear chat if alone in chunk
        if (newPlayers.length <= 1) {
          window.dispatchEvent(new Event("clearChat"));
        }
      }

      if (data.type === "announcement" && data.data?.text) {
        const text = String(data.data.text);
        if (text === SYSTEM_TREASURE) {
          setNotice(text);
          setTimeout(() => setNotice(null), 3000);
        } else {
          setQuoteText(text);
        }
      }

      if (data.type === "error") {
        setError(String(data.message || "An error occurred."));
        setShowMessageInput(false);
        setTimeout(() => setError(null), 3000);
      }
    };

    window.addEventListener("game-update", handleGameUpdate as EventListener);
    return () => window.removeEventListener("game-update", handleGameUpdate as EventListener);
  }, []);

  const decodeColor = (v: number) => {
    // Extract only the color bits (0–63)
    const colorCode = v & 0b111111;
    // Shift bits up so they align with the original 2–7 layout
    const shifted = colorCode << 2;
    const getBit = (x: number, bit: number) => (x >> bit) & 1;
    const get2 = (x: number, b0: number, b1: number) =>
      (getBit(x, b1) << 1) | getBit(x, b0);
    const r2 = get2(shifted, 2, 5);
    const g2 = get2(shifted, 3, 6);
    const b2 = get2(shifted, 4, 7);
    const map = [0, 85, 170, 255];
    return `rgb(${map[r2]}, ${map[g2]}, ${map[b2]})`;
  };


  // Keyboard handling
  const handleKeyPress = useCallback(
    (event: KeyboardEvent) => {
      if (!isConnected) return;

      const ae = document.activeElement as HTMLElement | null;
      const tag = ae?.tagName?.toLowerCase();
      if (tag === "input" || tag === "textarea" || ae?.isContentEditable) return;

      const key = event.key.toLowerCase();
      let action = "";
      switch (key) {
        case "arrowup":
        case "w":
          sendCommand("up"); action = "Moved Up"; break;
        case "arrowdown":
        case "s":
          sendCommand("down"); action = "Moved Down"; break;
        case "arrowleft":
        case "a":
          sendCommand("left"); action = "Moved Left"; break;
        case "arrowright":
        case "d":
          sendCommand("right"); action = "Moved Right"; break;
        case "m":
          setShowMessageInput(true); action = "Writing Message"; break;
        case "c":
          sendCommand("c"); action = "Color Changed"; break;
      }
      if (action) {
        setLastAction(action);
        setTimeout(() => setLastAction(""), 1500);
        event.preventDefault();
      }
    },
    [isConnected, sendCommand]
  );

  useEffect(() => {
    const onKeyDown = (e: KeyboardEvent) => handleKeyPress(e);
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [handleKeyPress]);

  // Render grid background (static environment)
  const renderGrid = () => {
    if (!gameState) return null;
    const cells: JSX.Element[] = [];

    for (let r = 0; r < gameState.h; r++) {
      for (let c = 0; c < gameState.w; c++) {
        const i = r * gameState.w + c;
        const v = gameState.data[i];
        // const getBit = (x: number, bit: number) => (x >> bit) & 1;
        // const get2 = (x: number, b0: number, b1: number) =>
        //   (getBit(x, b1) << 1) | getBit(x, b0);
        // const r2 = get2(v, 2, 5);
        // const g2 = get2(v, 3, 6);
        // const b2 = get2(v, 4, 7);
        // const blank = r2 === 0 && g2 === 0 && b2 === 0;
        // const map = [0, 85, 170, 255];
        // const color = `rgb(${map[r2]}, ${map[g2]}, ${map[b2]})`;
        const color = decodeColor(v);
        const blank = (v & 0b111111) === 0;

        cells.push(
          <div
            key={`${r}-${c}`}
            className="voxel-cell"
            style={{
              backgroundColor: blank ? "transparent" : color,
            }}
          />
        );
      }
    }

    // ✅ Add player overlay with real color
    // const map = [0, 85, 170, 255];
    // const playerDivs = players.map((p) => {
    //   const v = p.color;
    //   const getBit = (x: number, bit: number) => (x >> bit) & 1;
    //   const get2 = (x: number, b0: number, b1: number) =>
    //     (getBit(x, b1) << 1) | getBit(x, b0);
    //   const r2 = get2(v, 2, 5);
    //   const g2 = get2(v, 3, 6);
    //   const b2 = get2(v, 4, 7);
    //   const color = `rgb(${map[r2]}, ${map[g2]}, ${map[b2]})`;
    const playerDivs = players.map((p) => {
      const color = decodeColor(p.color);

      return (
        <div
          key={`player-${p.id}`}
          className="absolute rounded-[2px] shadow-[0_0_6px_rgba(255,255,255,0.6)]"
          style={{
            width: `${100 / gameState.w}%`,
            height: `${100 / gameState.h}%`,
            top: `${(p.row / gameState.h) * 100}%`,
            left: `${(p.col / gameState.w) * 100}%`,
            backgroundColor: color,
          }}
        />
      );
    });

    return (
      <div
        className="relative"
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${gameState.w}, 1fr)`,
          gap: "1px",
          width: "100%",
          aspectRatio: "1",
        }}
      >
        {cells}
        {playerDivs}
      </div>
    );
  };

  const enrichedPlayers = useMemo(() => {
    const chunkId = gameState?.chunk_id ?? sessionStorage.getItem("current_chunk_id") ?? null;
    return players.map((p) => ({
      ...p,
      username: p.id,
      email: "",
      chunk_id: chunkId || "",
    }));
  }, [players, gameState]);

  const myId = authStorage.getUser()?.id ?? "";

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-purple-900 to-slate-900 text-white overflow-x-hidden">
      <div className="container mx-auto px-4 pt-4 sm:pt-8">
        <div className="text-center mb-4 sm:mb-6">
          <h1 className="text-3xl sm:text-4xl font-bold mb-2 bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
            NanoVerse
          </h1>
          <p className="text-slate-300 text-sm sm:text-lg">
            A multiplayer voxel playground where colors come alive
          </p>
        </div>

        {/* Status bar */}
        <div className="flex flex-wrap items-center justify-center gap-2 sm:gap-3 mb-4 sm:mb-6">
          <div
            className={`flex items-center gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-full text-sm ${isConnected ? "bg-green-500/20 text-green-300" : "bg-red-500/20 text-red-300"
              }`}
          >
            {isConnected ? <Wifi size={16} /> : <WifiOff size={16} />}
            <span className="font-medium hidden sm:inline">
              {isConnected ? "Connected" : "Connecting..."}
            </span>
          </div>

          <div className="flex items-center gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-full bg-blue-500/20 text-blue-300 text-sm">
            <Users size={16} />
            <span className="font-medium">{playerCount}</span>
            <span className="hidden sm:inline">Players</span>
          </div>

          <button
            onClick={() => setShowInstructions(true)}
            className="flex items-center gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-full bg-amber-500/20 text-amber-300 hover:bg-amber-500/30 transition-all duration-200 transform hover:scale-105 text-sm"
          >
            <HelpCircle size={16} />
            <span className="font-medium hidden sm:inline">How to Play</span>
          </button>

          {lastAction && (
            <div className="flex items-center gap-2 px-3 sm:px-4 py-1.5 sm:py-2 rounded-full bg-purple-500/20 text-purple-300 animate-pulse text-sm">
              <Gamepad2 size={16} />
              <span className="font-medium">{lastAction}</span>
            </div>
          )}
        </div>
      </div>

      {/* Board */}
      <div className="flex justify-center items-center px-4 py-4 min-h-[60vh]">
        {gameState ? (
          <div
            className="voxel-grid relative bg-slate-800/50 p-3 sm:p-4 rounded-2xl backdrop-blur-sm border border-slate-700/50 shadow-2xl overflow-hidden"
            style={{
              maxWidth: "min(800px, 90vw)",
              aspectRatio: "1",
              width: "100%",
            }}
          >
            {renderGrid()}
          </div>
        ) : (
          <div className="flex items-center justify-center w-full max-w-md aspect-square bg-slate-800/50 rounded-2xl backdrop-blur-sm border border-slate-700/50">
            <div className="text-center">
              <div className="animate-spin w-8 h-8 border-2 border-blue-400 border-t-transparent rounded-full mx-auto mb-4" />
              <p className="text-slate-400 text-sm">Connecting to voxel world...</p>
            </div>
          </div>
        )}
      </div>

      {/* Chat Panel */}
      {showChat && (
        <>
          <div
            className="fixed inset-0 bg-black/20 backdrop-blur-[1px] z-40 sm:hidden"
            onClick={() => setShowChat(false)}
          />
          <div
            className="fixed z-[100] right-3 xs:right-4 sm:right-6 bottom-16 xs:bottom-14 sm:bottom-12 bg-slate-900 border border-slate-700 rounded-2xl shadow-2xl overflow-hidden pointer-events-auto aspect-[4/5] w-[clamp(220px,22vw,380px)] max-h-[600px]"
            style={{ maxHeight: "min(70vh, 600px)" }}
          >
            <ChatRoot
              onClose={() => setShowChat(false)}
              playerId={myId}
              currentChunkId={gameState?.chunk_id ?? sessionStorage.getItem("current_chunk_id") ?? null}
              playersInChunk={enrichedPlayers}
            />
          </div>
        </>
      )}

      {/* Floating chat button */}
      <button
        onClick={() => setShowChat((prev) => !prev)}
        className="fixed bottom-5 right-5 sm:bottom-6 sm:right-6 z-50 rounded-full p-3 sm:p-3.5 bg-black/80 text-white shadow-lg hover:bg-black transition-transform hover:scale-110"
        title={showChat ? "Close Chat" : "Open Chat"}
      >
        {showChat ? <X size={20} /> : <MessageCircle size={20} />}
      </button>

      {/* Connection status */}
      <div className="fixed bottom-4 left-4 text-xs sm:text-sm text-slate-300 flex items-center gap-2 sm:gap-3 bg-slate-800/70 px-2 sm:px-3 py-1.5 sm:py-2 rounded-lg backdrop-blur-sm border border-slate-700/50 shadow-lg">
        {isConnected ? <Wifi className="text-green-400" size={14} /> : <WifiOff className="text-red-400" size={14} />}
        <span className="hidden sm:inline">
          {isConnected ? "Connected" : "Disconnected"} • {playerCount} players
        </span>
        <span className="sm:hidden">{playerCount}</span>
      </div>

      {notice && (
        <div className="fixed top-4 left-1/2 -translate-x-1/2 bg-blue-50/90 text-blue-800 px-4 py-2 rounded-lg shadow-lg border border-blue-200 text-sm">
          {notice}
        </div>
      )}

      {quoteText && <QuoteToast text={quoteText} onClose={() => setQuoteText(null)} />}

      {showMessageInput && (
        <MessageInput
          onSubmit={(content: string) => {
            sendCommand({ command: "m", content });
            setShowMessageInput(false);
          }}
          onClose={() => setShowMessageInput(false)}
        />
      )}

      {showInstructions && <InstructionsModal onClose={() => setShowInstructions(false)} />}

      {currentMessage && <MessageBubble message={currentMessage} />}

      {error && (
        <div className="fixed top-4 right-4 bg-red-50 text-red-600 px-4 py-3 rounded-lg shadow-lg border border-red-200 text-sm max-w-[90vw] sm:max-w-md">
          {error}
        </div>
      )}
    </div>
  );
};

export default VoxelGrid;
