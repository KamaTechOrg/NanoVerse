# 📡 Chat Project

---

## 🧩 Project Structure

```
CHAT/
│
├── Data/
│   ├── tokens.json          # File containing user tokens
│
├── project/                 # Client folder (React + Vite)
├── server/                  # Server folder (FastAPI)
├── .venv/                   # Python virtual environment
└── test_server.py
```

---

## 🚀 Running the Project

To run the project, open **3 separate terminals** in the following order:

### 1️⃣ Client (Frontend)
> From the root directory

```bash
cd project
npm i
npm run dev
```

---

### 2️⃣ Server (Backend)
> Activate Python environment

```bash
cd .venv
pip install fastapi[all]
pip install uvicorn
pip install httpx
npm install socket.io-client
```

If `pip` is not available:
```bash
python -m pip install --upgrade pip
```

Then run the server:
```bash
python -m uvicorn server.main:app --reload
```

---

### 3️⃣ Model Request (KamaTech Server)
> Used to send a test command to the model that simulates the bot behavior

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/demo/bot-ping" `
  -Method POST `
  -Headers @{ "Content-Type" = "application/json" } `
  -Body '{ "as": "player4", "to": "player1", "mode": "generate" }'
```

🟢 **Note:** Make sure the **KamaTech server is running**, including the server created by Ruth!

---

## 🌐 Accessing the Chat Interface

After all services are active, open a browser **in incognito mode** and navigate to:

```
http://localhost:5173/?token=token_12345
```

> The number at the end is the user token – you can find it in `Data/tokens.json`.

---

✅ Everything is ready! Enjoy running the project 🎯
