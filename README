# Game2 – FastAPI + WebSocket Microservices

The project is built as a set of small, modular microservices that work together to handle all the game logic.  
It supports **real-time multiplayer gameplay** via WebSocket, allowing players to move, change colors, send messages, and interact with an infinite board.

---

## 🧩 Project Structure

- **api/** – contains `main.py`, which runs the FastAPI server and defines the WebSocket entry point.  
- **hub/** – the core game logic: movement, chat, scrolling (infinite board), and player management.  
- **data/** – handles local persistence for players, world chunks, history logs, and scroll triggers.  
- **core/** – includes constants, configuration, and shared settings like board size, bit flags, and data paths.



## ⚙️ How It Works

- The **FastAPI** server exposes a `/ws` WebSocket endpoint.  
- The **Hub** module manages connected sessions, applies movement, updates the board, and broadcasts changes to all relevant players.  
- Player actions are logged in JSONL files for training bots and replaying game sessions.  
- Communication between client and server uses a simple JSON protocol:
  ```json
  { "type": "move", "key": "up" }
  { "type": "color", "value": 7 }
  { "type": "dm", "to": "u456", "text": "hi" }
  ```

The server responds with structured updates:
  ```json
  { "type": "chunk", "chunkId": "0:0", "matrix": [[...]] }
  { "type": "announce", "text": "A player hid a treasure" }
  ```

---

##  How to Run

1. **Install dependencies**  
   Make sure you have Python 3.10+  
   ```bash
   pip install -r requirements.txt
   # or minimal:
   pip install fastapi uvicorn torch "python-jose[cryptography]"
   ```

2. **Start the server**  
   From the root directory:
   ```bash
    1. uvicorn services.auth.main:app --env-file services/auth/.env --host 127.0.0.1 --port 7001 --reload
    2.uvicorn services.game2.api.main:app --host 0.0.0.0 --port 7002 --reload
   From the edge directory:
      npm run dev
   ```

3. **Connect a client**  
   The WebSocket endpoint is:  
   ```
   ws://localhost:8001/ws
   ```---




