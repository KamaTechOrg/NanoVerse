// import { defineConfig } from "vite";
// import react from "@vitejs/plugin-react";

// export default defineConfig({
//   plugins: [react()],
//   server: {
//     port: 5173,
//     proxy: {
//       "/auth": {
//         target: "http://localhost:8080",
//         changeOrigin: true,
//       },
//       "/game": {
//         target: "http://localhost:8080",
//         ws: true,
//         changeOrigin: true,
//       },
//     },
//   },
// });

import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    allowedHosts: ["orensch2.myvnc.com"],

    proxy: {
      // ✅ Auth routes → Edge
      "/auth": {
        target: "http://localhost:8080",
        changeOrigin: true,
      },

      // ✅ Game WebSocket (ws://)
      "^/game/ws": {
        target: "http://localhost:8080",
        ws: true,
        changeOrigin: true,
        secure: false,
      },

      // ✅ Score API → Game service (7002)
      "/score": {
        target: "http://127.0.0.1:7002",
        changeOrigin: true,
      },
    },
  },
});
