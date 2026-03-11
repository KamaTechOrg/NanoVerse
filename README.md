                          
						  
# 🌌 NanoVerse

![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-backend-green)
![WebSockets](https://img.shields.io/badge/WebSocket-realtime-orange)
![PyTorch](https://img.shields.io/badge/PyTorch-AI-red)
![LoRA](https://img.shields.io/badge/LLM-LoRA-purple)

NanoVerse is an **AI-driven multiplayer world** that combines real-time gameplay, distributed backend services, and personalized AI agents.

The system explores how **machine learning models and LLMs can extend player presence** inside a persistent online environment.

Players interact in a shared world while AI systems learn their behavior and communication style using:

- **GRU sequence models**
- **LoRA-based LLM personalization**
- **real-time microservices architecture**

---

# 🚀 Key Features

- Real-time multiplayer architecture
- WebSocket based game communication
- Distributed backend services
- AI powered gameplay agents
- GRU behavioral models
- Gemma LLM fine-tuning with LoRA adapters
- Player behavior modeling
- Modular scalable system design

---

# 🧠 AI Systems

NanoVerse integrates multiple AI components designed to simulate player behavior and communication.

## GRU Behavioral Model

The first model predicts **player gameplay actions** based on the current world state and recent interaction history.

Inputs may include:

- nearby entities
- previous actions
- world state
- contextual gameplay signals

Why GRU:

- efficient sequential modeling
- suitable for time-series gameplay data
- lightweight enough for real-time inference

---

## GRU Temporal Model

The second GRU model focuses on **behavior timing and pacing**.

Instead of only predicting actions, it models:

- action intervals
- sleep durations
- behavioral continuity

This improves realism and creates more natural gameplay behavior.

Together the models handle:

- **decision prediction**
- **temporal behavior modeling**

---

## LLM Personalization (Gemma + LoRA)

NanoVerse includes a language-based interaction system for personalized chat and dialogue.

The project uses:

- **Gemma**
- **LoRA (Low Rank Adaptation)**

Instead of training a full model per player, LoRA allows training **small adapter weights**.

Advantages:

- extremely memory efficient
- scalable to many players
- fast adapter switching
- minimal GPU overhead

Structure:


Base LLM
│
├── Player Adapter A
├── Player Adapter B
├── Player Adapter C


Each adapter captures player communication style.

---

## 🏗 System Architecture

```text
Client
│
▼
Edge Gateway
│
▼
Auth Service
│
▼
Game Service (WebSocket API)
│
├── Core Gameplay Logic
├── Bot / AI Systems
├── Chat System
├── Data Layer
└── Training Pipeline
```

The architecture separates runtime gameplay from training and AI systems.

---

## 📁 Repository Structure

```text
NanoVerse
├── .github/              # CI workflows and GitHub configuration
├── client/               # Game client
├── edge/                 # Edge gateway service
├── finetune_gemma/       # Gemma fine-tuning and LoRA adapters
├── services/
│   ├── auth/             # Authentication service
│   └── game2/            # Core game backend
│       ├── api/          # REST + WebSocket API
│       ├── bot/          # AI agents and gameplay bots
│       ├── chat/         # Chat and messaging system
│       ├── core/         # Core game logic
│       ├── data/         # Storage and datasets
│       ├── hub/          # Internal coordination layer
│       └── train/        # ML training pipelines
├── README.md
├── .env
├── .gitignore
└── requirements.txt
```

---

# ⚙️ Core Services

## Auth Service

Handles:

- user authentication
- session validation
- player identity

Separating authentication improves security boundaries.

---

## Game Service

The main runtime engine of NanoVerse.

Responsibilities:

- handling player connections
- processing gameplay events
- maintaining world state
- coordinating internal subsystems

---

## Bot System

Executes AI-driven gameplay behavior.

Uses GRU models to:

- predict actions
- generate behavior
- simulate player decisions

---

## Chat System

Handles in-game communication.

Features:

- message routing
- chat history
- integration with LLM personalization

---

## Training Pipeline

Responsible for improving AI models.

Typical steps:

1. collect gameplay logs
2. preprocess training data
3. train GRU models
4. fine-tune Gemma adapters
5. deploy updated models

---

## 🔁 AI Training Loop

```text
Gameplay Data
│
▼
Dataset Processing
│
▼
GRU Model Training
│
▼
Gemma LoRA Fine-Tuning
│
▼
Model Deployment
│
▼
Runtime Inference
```
---

## ▶️ Running the Project

Clone the repository:

```bash
git clone https://github.com/KamaTechOrg/NanoVerse.git
cd NanoVerse
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Configure environment:

```bash
# create and edit your .env file
```

Start services according to your local configuration.

---

## 🎮 Demo Scenario

Example flow:

1. Player connects through the client
2. Edge gateway routes requests
3. Auth service validates the user
4. Game service opens a session
5. Player actions update world state
6. Bot system predicts behavior
7. Chat system generates personalized responses

---

## 🧩 Engineering Focus

NanoVerse demonstrates capabilities across several domains:

- backend architecture
- AI systems engineering
- sequence modeling
- LLM personalization
- real-time distributed systems

The project explores how AI agents can operate inside interactive worlds while remaining scalable and efficient.
