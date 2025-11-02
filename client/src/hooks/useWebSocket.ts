import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type {
  Message as ChatMessage,
  Player,
  WebSocketMessage,
  Reaction,
} from "../types";
import { authStorage } from "../utils/auth";

function backendHost(): string {
  const h = window.location.hostname;
  return h === "localhost" || h === "127.0.0.1" ? "127.0.0.1" : h;
}

function wsUrl(): string {
  const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
  return `${proto}//${backendHost()}:8080/game/ws`;
/**
 * Decide backend host:
 * - in dev: ws://127.0.0.1:8080/ws
 * - in prod: ws(s)://<actual-host>/ws
 */
// function backendHost(): string {
//   const h = window.location.hostname;
//   return h === "localhost" || h === "127.0.0.1" ? "127.0.0.1" : h;
// }

//??to put it ??------------------------------------
// function wsUrl(): string {
//   const proto = window.location.protocol === "https:" ? "wss:" : "ws:";
//   const host = window.location.host; // This includes the port if specified
  // return `${proto}//${host}/game/ws`;
}

let singletonSocket: WebSocket | null = null;

type UseWS = {
  isConnected: boolean;
  messages: ChatMessage[];
  selectedPlayer: Player | null;
  selectPlayer: (p: Player) => void;
  sendMessage: (
    text: string,
    quotedMessage?: ChatMessage,
    extras?: { chunkId?: string | null }
  ) => void;
  reactToMessage: (id: string, reaction: Reaction) => void;
  deleteMessage: (messageId: string) => void;
  activePlayers: Player[];
  currentPlayerId?: string;
  unreadCounts: Record<string, number>;
  markRead: (playerId: string) => void;
  sendCommand: (command: string) => void;
};

export function useWebSocket(): UseWS {
  const socketRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [activePlayers] = useState<Player[]>([]);
  const [selectedPlayer, _setSelectedPlayer] = useState<Player | null>(null);
  const [currentPlayerId, _setCurrentPlayerId] = useState<string>();
  const [unreadCounts, setUnreadCounts] = useState<Record<string, number>>({});

  const selectedPlayerRef = useRef<Player | null>(null);
  const currentPlayerIdRef = useRef<string | undefined>(undefined);
  const seenIdsRef = useRef<Set<string>>(new Set());
  const messageIndexRef = useRef<Map<string, ChatMessage>>(new Map());

  const setSelectedPlayer = useCallback((p: Player | null) => {
    selectedPlayerRef.current = p;
    _setSelectedPlayer(p);
  }, []);

  const setCurrentPlayerId = useCallback((id?: string) => {
    currentPlayerIdRef.current = id;
    _setCurrentPlayerId(id);
  }, []);

  const attachQuoteIfAny = useCallback((raw: any): ChatMessage => {
    const quotedId = raw?.quotedId || raw?.quoted_id;
    if (quotedId) {
      const q = messageIndexRef.current.get(quotedId);
      if (q) return { ...(raw as ChatMessage), quoted_message: q } as any;
    }
    return raw as ChatMessage;
  }, []);

  const upsertMessages = useCallback(
    (list: ChatMessage[]) => {
      const withQuotes = list.map(attachQuoteIfAny);
      setMessages((prev) => {
        const next = [...prev];
        for (const m of withQuotes) {
          if (!seenIdsRef.current.has(m.id)) {
            next.push(m);
            seenIdsRef.current.add(m.id);
          } else {
            const i = next.findIndex((x) => x.id === m.id);
            if (i >= 0) next[i] = { ...next[i], ...m };
          }
        }
        return next;
      });
      for (const m of withQuotes) messageIndexRef.current.set(m.id, m);
    },
    [attachQuoteIfAny]
  );

  useEffect(() => {
    if (singletonSocket && singletonSocket.readyState !== WebSocket.CLOSED) {
      socketRef.current = singletonSocket;
      setIsConnected(singletonSocket.readyState === WebSocket.OPEN);
      return;
    }

    const url = wsUrl();
    const token = authStorage.getToken();
    const ws = new WebSocket(`${url}?token=${encodeURIComponent(token ?? "")}`);
    singletonSocket = ws;
    socketRef.current = ws;
    console.log("[WS] connecting to", url);

    ws.onopen = () => {
      setIsConnected(true);
      console.log("[WS] open");
      const user = authStorage.getUser();
      if (user?.id) {
        ws.send(JSON.stringify({ player_id: user.id }));
        setCurrentPlayerId(user.id);
      }
    };

    ws.onmessage = (ev) => {
      const data: WebSocketMessage | any = JSON.parse(ev.data);

      if (["matrix", "announcement", "error"].includes(data.type)) {
        window.dispatchEvent(new CustomEvent("game-update", { detail: data }));
        return;
      }

      if (data.type === "history") {
        const msgs: ChatMessage[] = (data.messages ?? []).map((m: any) => ({
          id: m.id,
          from: m.sender_id || m.from,
          to: m.receiver_id || m.to,
          message: m.content || m.message,
          timestamp: m.timestamp,
          type: "user",
          my_reaction:
            m.reaction === "like" ? "up" : m.reaction === "dislike" ? "down" : null,
        }));
        seenIdsRef.current = new Set(msgs.map((m) => m.id));
        setMessages(msgs);
        for (const m of msgs) messageIndexRef.current.set(m.id, m);
        return;
      }

      if (data.type === "message") {
        const msg: ChatMessage = {
          id: data.id,
          from: data.sender ?? "unknown",
          to: data.to ?? "",
          message: data.message ?? "",
          timestamp: data.timestamp ?? new Date().toISOString(),
          type: "user",
        };
        if (seenIdsRef.current.has(msg.id)) return;
        seenIdsRef.current.add(msg.id);
        messageIndexRef.current.set(msg.id, msg);
        setMessages((prev) => [...prev, msg]);
        return;
      }

      if (data.type === "react") {
        const { messageId, my_reaction } = data;
        const normalized =
          my_reaction === "like" ? "up" : my_reaction === "dislike" ? "down" : null;

        setMessages((prev) =>
          prev.map((m) => (m.id === messageId ? { ...m, my_reaction: normalized } : m))
        );

        const cur = messageIndexRef.current.get(messageId);
        if (cur)
          messageIndexRef.current.set(messageId, {
            ...cur,
            my_reaction: normalized,
          });
        return;
      }

      if (data.type === "unread") {
        const me = currentPlayerIdRef.current;
        if (me && (data as any).to === me) {
          setUnreadCounts((prev) => ({
            ...prev,
            [(data as any).from]: (data as any).count,
          }));
        }
      }
    };

    ws.onclose = () => {
      console.warn("[WS] closed");
      setIsConnected(false);
      if (socketRef.current === ws) socketRef.current = null;
      singletonSocket = null;
    };

    return () => {
      if (socketRef.current === ws) {
        try {
          ws.close();
        } catch {}
        socketRef.current = null;
        singletonSocket = null;
      }
    };
  }, [attachQuoteIfAny, upsertMessages, setCurrentPlayerId]);

  const sendCommand = useCallback((command: string | object) => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify(typeof command === "string" ? { command } : command));
  }, []);

  const selectPlayer = useCallback(
    (p: Player) => {
      setSelectedPlayer(p);
      const ws = socketRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      ws.send(JSON.stringify({ type: "select", selectedPlayer: p.id }));
      ws.send(JSON.stringify({ type: "read", with: p.id }));
      setUnreadCounts((prev) => ({ ...prev, [p.id]: 0 }));
    },
    [setSelectedPlayer]
  );

  const markRead = useCallback((playerId: string) => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "read", with: playerId }));
    setUnreadCounts((prev) => ({ ...prev, [playerId]: 0 }));
  }, []);

  const sendMessage = useCallback(
    (text: string, quotedMessage?: ChatMessage, extras?: { chunkId?: string | null }) => {
      const ws = socketRef.current;
      const sel = selectedPlayerRef.current;
      const me = currentPlayerIdRef.current;
      if (!ws || ws.readyState !== WebSocket.OPEN) return;
      if (!sel || !me || !text.trim()) return;

      const ts = new Date().toISOString();
      const id = `${ts}|${me}|${text}`;
      const payload: any = {
        type: "message",
        message: text,
        selectedPlayer: sel.id,
        timestamp: ts,
      };
      if (quotedMessage) payload.quotedId = quotedMessage.id;
      if (extras?.chunkId) payload.chunkId = extras.chunkId;

      ws.send(JSON.stringify(payload));
      const optimistic: ChatMessage = {
        id,
        from: me,
        to: sel.id,
        message: text,
        timestamp: ts,
        type: "user",
      } as any;
      seenIdsRef.current.add(id);
      messageIndexRef.current.set(id, optimistic);
      setMessages((prev) => [...prev, optimistic]);
    },
    []
  );

  const reactToMessage = useCallback((messageId: string, reaction: Reaction) => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;

    const mapped =
      reaction === "up" ? "like" : reaction === "down" ? "dislike" : "none";
    ws.send(JSON.stringify({ type: "react", messageId, reaction: mapped }));
  }, []);

  const deleteMessage = useCallback((messageId: string) => {
    const ws = socketRef.current;
    if (!ws || ws.readyState !== WebSocket.OPEN) return;
    ws.send(JSON.stringify({ type: "delete", messageId }));
    setMessages((prev) =>
      prev.map((m) => (m.id === messageId ? { ...m, deleted: true, message: "" } : m))
    );
  }, []);

  return useMemo(
    () => ({
      isConnected,
      messages,
      selectedPlayer,
      selectPlayer,
      sendMessage,
      reactToMessage,
      deleteMessage,
      activePlayers,
      currentPlayerId,
      unreadCounts,
      markRead,
      sendCommand,
    }),
    [
      isConnected,
      messages,
      selectedPlayer,
      selectPlayer,
      sendMessage,
      reactToMessage,
      deleteMessage,
      activePlayers,
      currentPlayerId,
      unreadCounts,
      markRead,
      sendCommand,
    ]
  );
}
