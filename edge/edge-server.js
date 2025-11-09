import 'dotenv/config';
import express from 'express';
import http from 'http';
import cors from 'cors';
import jwt from 'jsonwebtoken';
import { createProxyMiddleware } from 'http-proxy-middleware';
import { URL } from 'url';

const PORT = Number(process.env.PORT || 8080);
const JWT_SECRET = process.env.AUTH_JWT_SECRET || 'CHANGE_ME_123456789';

const AUTH_SERVICE_URL = process.env.AUTH_SERVICE_URL || 'http://127.0.0.1:7001';
const GAME_SERVICE_URL = process.env.GAME_SERVICE_URL || 'http://127.0.0.1:7002';
const FRONTEND_ORIGIN = (process.env.CORS_ORIGIN || 'http://localhost:5173').split(',');

const app = express();

// ---------------------- CORS ----------------------
app.use(
  cors({
    origin: FRONTEND_ORIGIN,
    credentials: true,
    methods: ['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'],
    allowedHeaders: ['Content-Type', 'Authorization'],
  })
);
app.options('*', cors());

// ---------------------- LOGGING ----------------------
app.use((req, res, next) => {
  console.log('[EDGE][INCOMING]', req.method, req.url, 'origin=', req.headers.origin, 'host=', req.headers.host);
  next();
});

// ---------------------- TOKEN HELPERS ----------------------
function getTokenFromReq(req) {
  try {
    const hdr = (req.headers && (req.headers.authorization || req.headers.Authorization)) || '';
    if (typeof hdr === 'string' && hdr.startsWith('Bearer ')) {
      return hdr.slice(7);
    }
    if (req.query && typeof req.query.token === 'string') return req.query.token;
    if (req.url) {
      const full = req.url.startsWith('http') ? req.url : `http://localhost${req.url}`;
      const u = new URL(full);
      return u.searchParams.get('token') || null;
    }
  } catch {
    console.log('error extracting token');
  }
  return null;
}

function requireJWT(req, res, next) {
  try {
    if (req.method === 'OPTIONS') return res.sendStatus(200);

    const upgrade = (req.headers && req.headers.upgrade) || '';
    if (typeof upgrade === 'string' && upgrade.toLowerCase() === 'websocket') return next();

    const token = getTokenFromReq(req);
    if (!token) return res.status(401).json({ ok: false, error: 'missing_token' });
    req.user = jwt.verify(token, JWT_SECRET);
    next();
  } catch (err) {
    return res.status(401).json({ ok: false, error: 'invalid_token', msg: err.message });
  }
}

// ---------------------- /auth proxy ----------------------
const authProxy = createProxyMiddleware({
  target: AUTH_SERVICE_URL,
  pathRewrite: { '^/auth': '' },
  changeOrigin: true,
  ws: false,
  logLevel: 'debug',
  onProxyReq: (proxyReq, req) => {
    if (req.body && Object.keys(req.body).length) {
      const bodyData = JSON.stringify(req.body);
      proxyReq.setHeader('Content-Type', 'application/json');
      proxyReq.setHeader('Content-Length', Buffer.byteLength(bodyData));
      proxyReq.write(bodyData);
      proxyReq.end();
    }
  },
  onError: (err, req, res) => {
    console.error('[EDGE][auth proxy error]', err?.message);
    if (res && !res.headersSent) {
      res.writeHead && res.writeHead(502);
      res.end('Bad gateway');
    }
  },
});

app.use('/auth', authProxy);

// ---------------------- GAME proxy ----------------------
const gameProxy = createProxyMiddleware({
  target: GAME_SERVICE_URL,
  pathRewrite: { '^/': '/' }, // everything (/) → game service
  changeOrigin: true,
  ws: true,
  logLevel: 'debug',
  onProxyReqWs: (proxyReq, req, socket) => {
    try {
      const full = req.url.startsWith('http')
        ? req.url
        : `http://${req.headers.host || 'localhost'}${req.url}`;
      const u = new URL(full);
      const token = u.searchParams.get('token') || getTokenFromReq(req);

      console.log('[EDGE][WS] upgrade url=', req.url, 'token?', !!token);

      if (!token) {
        socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
        socket.destroy();
        return;
      }

      // verify token
      const payload = jwt.verify(token, JWT_SECRET, { algorithms: ['HS256'] });
      console.log('[EDGE][WS] token OK:', payload?.sub || payload?.username);

      proxyReq.setHeader('Authorization', `Bearer ${token}`);

      // fix host header for upstream
      const targetHost = new URL(GAME_SERVICE_URL).host;
      proxyReq.setHeader('host', targetHost);
    } catch (err) {
      console.log('[EDGE][WS] token verify failed:', err?.message || String(err));
      try {
        socket.write('HTTP/1.1 401 Unauthorized\r\n\r\n');
      } catch {}
      try {
        socket.destroy();
      } catch {}
    }
  },
});


// === SCORE proxy → game ===
app.use("/score", createProxyMiddleware({
  target: GAME_SERVICE_URL,
  changeOrigin: true,
  pathRewrite: { "^/score": "/score" },
  logLevel: "debug",
  onError(err, req, res) {
    console.error("[EDGE][/score proxy error]", err.message);
    if (!res.headersSent) res.status(502).end("Bad gateway");
  }
}));




// All HTTP requests to game → require JWT
app.use('/', (req, res, next) => {
  const upgrade = (req.headers && req.headers.upgrade) || '';
  if (typeof upgrade === 'string' && upgrade.toLowerCase() === 'websocket') return next();
  requireJWT(req, res, next);
}, gameProxy);

// ---------------------- HEALTH CHECK ----------------------
app.get('/health', (_req, res) => res.json({ ok: true, service: 'edge' }));

// ---------------------- FALLBACK ----------------------
app.use((_req, res) => {
  res.status(404).json({ ok: false, error: 'not_found' });
});

// ---------------------- HTTP SERVER + WS UPGRADE ----------------------
const server = http.createServer(app);

server.on('upgrade', (req, socket, head) => {
  try {
  console.log('[EDGE][UPGRADE] got upgrade request:', req.url, 'headers:', req.headers);
    // proxy WS connections at /ws → game service
    if (req.url && req.url.startsWith('/ws')) {
        console.log('[EDGE][FORWARD] forwarding WS upgrade to game service...');

      const token = getTokenFromReq(req);
      if (typeof gameProxy.upgrade === 'function') {
        return gameProxy.upgrade(req, socket, head);
      }
      socket.destroy();
      return;
    }
    socket.destroy();
  } catch {
    try {
      socket.destroy();
    } catch {}
  }
});

server.listen(PORT, () => {
  console.log(`[edge] listening on http://localhost:${PORT}`);
  console.log(`[edge] auth → ${AUTH_SERVICE_URL}`);
  console.log(`[edge] game → ${GAME_SERVICE_URL}`);
});
