<p align="center">
  <img src="0logov3.png" width="400" alt="Fractal Bitcoin Logo" />
</p>

# Fractal Bitcoin (FB) Dashboard V4

A sophisticated, high-performance command center for the Fractal Bitcoin network. This dashboard manages both a local **Fractal Node (`fractald`)** and an integrated **External Miner**, providing real-time telemetry across the entire substrate lifecycle.

## 🚀 Key Features

- **Dual Substrate Management**: Orchestrate both the full node and the hashing miner from a single interface.
- **Auto-Deployment Engine**: One-click acquisition of Fractal substrates. On startup, the system automatically fetches the latest official releases and prepares them for your environment.
- **WSL Translation Layer**: Native Windows support for official Linux node binaries via automated WSL drive mapping and path translation.
- **Real-time Telemetry Broadcaster**: High-performance telemetry broadcasting that minimizes RPC load and prevents rate-limiting.
- **Process Watchdog**: Advanced lifecycle management that neutralizes zombie processes and ensures a clean environment on shutdown.
- **Node-Miner Safety Coupling**: Intelligent monitoring that halts the miner if the node loses network sync or healthy status.


## 🛠️ Project Structure

```text
├── backend/          # Substrate Coordinator & RPC Gateway
│   ├── bin/          # Place fractald.exe and fractal-miner.exe here
│   ├── main.py       # Dual-stream API & WebSocket
│   ├── miner.py      # Substrate Coordinator (Process Manager)
│   └── rpc_client.py # Async Bitcoin JSON-RPC Client
└── frontend/         # Preact + Vite Control Panel
    ├── src/          # Dual-Zone UI (Node/Miner)
    └── index.html    # Entry point
```

## 🏁 Quick Start

### Prerequisites
- **Python 3.10+** (FastAPI, uvicorn, websockets)
- **fractald.exe** & **fractal-miner.exe** (Placed in `backend/bin/`)
- **Bun** (for frontend development)

### 1. Initialize Substrate binaries
Ensure you place the official binaries in `backend/bin/`.

### 2. Launch Control API
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate
pip install fastapi uvicorn websockets
python main.py
```

### 3. Launch UI
```bash
cd frontend
bun install
bun dev
```

### 4. Operation
1. Open `http://localhost:3699`.
2. Click **Initialize Node** to start the Fractal network substrate.
3. Once synced, enter your address and click **Start Mining**.

---
<p align="center">
  <i>Developed for the BOLTEVM Ecosystem.</i>
</p>
