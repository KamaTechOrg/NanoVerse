
// src/context/WebSocketProvider.tsx
import React, { createContext, useContext } from "react";
import { useWebSocket } from "../hooks/useWebSocket"; // ✅ correct relative path

const WebSocketContext = createContext<ReturnType<typeof useWebSocket> | null>(null);

export const WebSocketProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const ws = useWebSocket(); // ✅ one connection only
  return <WebSocketContext.Provider value={ws}>{children}</WebSocketContext.Provider>;
};

export const useSharedWebSocket = () => {
  const ctx = useContext(WebSocketContext);
  if (!ctx) throw new Error("useSharedWebSocket must be used inside <WebSocketProvider>");
  return ctx;
};
