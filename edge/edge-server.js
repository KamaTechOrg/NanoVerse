import { URL as NodeURL, fileURLToPath } from "url";
import path from "path";
import "dotenv/config";
import express from "express";
import http from "http";
import cors from "cors";
import jwt from "jsonwebtoken";
import { createProxyMiddleware } from "http-proxy-middleware";

/* ---------------------- ENV & CONSTANTS ---------------------- */
const HOST = process.env.HOST || "0.0.0.0";
const PORT = Number(process.env.PORT || 8080);
const JWT_SECRET = process.env.AUTH_JWT_SECRET || "CHANGE_ME_123456789";

const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || "http://127.0.0.1:7001";
const GAME_SERVICE_URL = process.env.GAME_SERVICE_URL || "http://127.0.0.1:7002";

// CORS_ORIGIN may be comma-separated
const DEFAULT_ORIGINS = ["http://localhost:5173", "http://localhost:5174"];
const FRONTEND_ORIGIN = (process.env.CORS_ORIGIN
  ? process.env.CORS_ORIGIN.split(",").map(s => s.trim()).filter(Boolean)
  : DEFAULT_ORIGINS);

/* ---------------------- PATHS ---------------------- */
const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const distDir = path.join(__dirname, "../client/dist"); // adjust if needed

/* ---------------------- APP ---------------------- */
const app = express();

/* ---------------------- LOGGING ---------------------- */
app.use((req, _res, next) => {
  console.log(
    "[EDGE][INCOMING]",
    req.method,
    req.url,
    "origin=",
    req.headers.origin,
    "host=",
    req.headers.host
  );
  next();
});

/* ---------------------- AUTH PROXY (no body parsers before this!) ---------------------- */
app.use(
  "/auth",
  createProxyMiddleware({
    target: AUTH_SERVICE_URL,
    changeOrigin: true,
    pathRewrite: { "^/auth": "" }, // /auth/* → upstream /*
    ws: false,
    logLevel: "debug",
    onError: (err, req, res) => {
      console.error("[EDGE][auth proxy error]", err?.message);
      if (res && !res.headersSent) res.status(502).end("Bad gateway");
    },
  })
);

/* ---------------------- BODY PARSERS (safe after /auth) ---------------------- */
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

/* ---------------------- CORS ---------------------- */
app.use(
  cors({
    origin: FRONTEND_ORIGIN,
    credentials: true,
    methods: ["GET", "POST", "OPTIONS", "PUT", "DELETE", "PATCH"],
    allowedHeaders: ["Content-Type", "Authorization"],
  })
);
app.options("*", cors());

/* ---------------------- STATIC (client build) ---------------------- */
app.use(express.static(distDir));

/* ---------------------- HEALTH (public) ---------------------- */
app.get("/health", (_req, res) => res.json({ ok: true, service: "edge" }));

/* ---------------------- TOKEN HELPERS ---------------------- */
function getTokenFromReq(req) {
  try {
    const hdr = (req.headers && (req.headers.authorization || req.headers.Authorization)) || "";
    if (typeof hdr === "string" && hdr.startsWith("Bearer ")) return hdr.slice(7);
    if (req.query && typeof req.query.token === "string") return req.query.token;

    if (req.url) {
      const full = req.url.startsWith("http") ? req.url : `http://localhost${req.url}`;
      const u = new NodeURL(full);
      return u.searchParams.get("token") || null;
    }
  } catch {
    console.log("[EDGE] error extracting token");
  }
  return null;
}

function requireJWT(req, res, next) {
  try {
    if (req.method === "OPTIONS") return res.sendStatus(200);

    const upgrade = (req.headers && req.headers.upgrade) || "";
    if (typeof upgrade === "string" && upgrade.toLowerCase() === "websocket") return next();

    const token = getTokenFromReq(req);
    if (!token) return res.status(401).json({ ok: false, error: "missing_token" });

    req.user = jwt.verify(token, JWT_SECRET);
    next();
  } catch (err) {
    return res.status(401).json({ ok: false, error: "invalid_token", msg: err?.message });
  }
}

/* ---------------------- SCORE PROXY (public; re-add /score prefix) ---------------------- */
app.use(
  "/score",
  createProxyMiddleware({
    target: GAME_SERVICE_URL,
    changeOrigin: true,
    logLevel: "debug",
    pathRewrite: (path /* e.g. "/top" */) => `/score${path}`, // -> "/score/top"
    onError(err, req, res) {
      console.error("[EDGE][/score proxy error]", err?.message);
      if (!res.headersSent) res.status(502).end("Bad gateway");
    },
  })
);

/* ---------------------- GAME PROXY (JWT required) ---------------------- */
const STATIC_PREFIXES = [
  "/assets",
  "/vite.svg",
  "/favicon",
  "/robots.txt",
  "/manifest",
  "/icons",
];

const gameProxy = createProxyMiddleware({
  target: GAME_SERVICE_URL,
  pathRewrite: { "^/": "/" },
  changeOrigin: true,
  ws: true,
  logLevel: "debug",
  onProxyReqWs: (proxyReq, req, socket) => {
    try {
      const full = req.url.startsWith("http")
        ? req.url
        : `http://${req.headers.host || "localhost"}${req.url}`;
      const u = new NodeURL(full);
      const token = u.searchParams.get("token") || getTokenFromReq(req);

      console.log("[EDGE][WS] upgrade url=", req.url, "token?", !!token);

      if (!token) {
        socket.write("HTTP/1.1 401 Unauthorized\r\n\r\n");
        socket.destroy();
        return;
      }

      const payload = jwt.verify(token, JWT_SECRET, { algorithms: ["HS256"] });
      console.log("[EDGE][WS] token OK:", payload?.sub || payload?.username);

      proxyReq.setHeader("Authorization", `Bearer ${token}`);

      const targetHost = new NodeURL(GAME_SERVICE_URL).host;
      proxyReq.setHeader("host", targetHost);
    } catch (err) {
      console.log("[EDGE][WS] token verify failed:", err?.message || String(err));
      try { socket.write("HTTP/1.1 401 Unauthorized\r\n\r\n"); } catch {}
      try { socket.destroy(); } catch {}
    }
  },
});

// All non-static, non-auth, non-score → require JWT → game
app.use(
  "/",
  (req, res, next) => {
    const upgrade = (req.headers && req.headers.upgrade) || "";
    if (typeof upgrade === "string" && upgrade.toLowerCase() === "websocket") return next();

    if (req.method === "GET" && STATIC_PREFIXES.some(p => req.path === p || req.path.startsWith(p))) {
      return next();
    }

    requireJWT(req, res, next);
  },
  gameProxy
);

/* ---------------------- SPA FALLBACK ---------------------- */
app.get("*", (req, res, next) => {
  const wantsHtml = req.method === "GET" && (req.headers.accept || "").includes("text/html");
  if (
    wantsHtml &&
    !req.path.startsWith("/auth") &&
    !req.path.startsWith("/ws") &&
    !req.path.startsWith("/health") &&
    !req.path.startsWith("/score")
  ) {
    return res.sendFile(path.join(distDir, "index.html"));
  }
  next();
});

/* ---------------------- HTTP SERVER + WS UPGRADE ---------------------- */
const server = http.createServer(app);

server.on("upgrade", (req, socket, head) => {
  try {
    console.log("[EDGE][UPGRADE] got upgrade request:", req.url, "headers:", req.headers);
    if (req.url && req.url.startsWith("/ws")) {
      console.log("[EDGE][FORWARD] forwarding WS upgrade to game service...");
      if (typeof gameProxy.upgrade === "function") {
        return gameProxy.upgrade(req, socket, head);
      }
      socket.destroy();
      return;
    }
    socket.destroy();
  } catch {
    try { socket.destroy(); } catch {}
  }
});

server.listen(PORT, HOST, () => {
  console.log(`[edge] listening on ${HOST}:${PORT}`);
  console.log(`[edge] auth → ${AUTH_SERVICE_URL}`);
  console.log(`[edge] game → ${GAME_SERVICE_URL}`);
  console.log(`[edge] cors origins →`, FRONTEND_ORIGIN);
});
