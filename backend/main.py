from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import asyncio
import json
from miner import SubstrateCoordinator
from rpc_client import FractalRPCClient
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("api")

app = FastAPI(title="Fractal Bitcoin Control API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configuration models
class NodeStartRequest(BaseModel):
    datadir: str = None

class MinerStartRequest(BaseModel):
    address: str
    threads: int = 1
    rpc_user: str = "user"
    rpc_pass: str = "pass"

# Singletons
coordinator = SubstrateCoordinator()
rpc = FractalRPCClient(user="user", password="pass")

class TelemetryBroadcaster:
    def __init__(self):
        self.state = {
            "node_running": False,
            "miner_running": False,
            "block_height": 0,
            "sync_progress": 0,
            "headers_synced": 0,
            "peers": 0,
            "hashrate": 0,
            "difficulty": 0,
            "logs": []
        }
        self.task = None

    async def start(self):
        coordinator.start_health_monitor()
        if not self.task:
            self.task = asyncio.create_task(self.poll_loop())

    async def poll_loop(self):
        while True:
            try:
                node_info = await rpc.get_blockchain_info()
                mining_info = await rpc.get_mining_info()
                
                if node_info and node_info.get("result") and mining_info and mining_info.get("result"):
                    res = node_info["result"]
                    m_res = mining_info["result"]
                    self.state.update({
                        "node_running": coordinator.node.running,
                        "miner_running": coordinator.miner.running,
                        "block_height": res.get("blocks", 0),
                        "headers_synced": res.get("headers", 0),
                        "sync_progress": res.get("verificationprogress", 0),
                        "peers": res.get("connections", 0),
                        "hashrate": coordinator.miner.hashrate,
                        "difficulty": m_res.get("difficulty", 0),
                        "logs": coordinator.get_logs()
                    })
                else:
                    self.state.update({
                        "node_running": coordinator.node.running,
                        "miner_running": coordinator.miner.running,
                        "logs": coordinator.get_logs()
                    })
            except Exception as e:
                logger.error(f"Broadcaster poll error: {e}")
            await asyncio.sleep(1)

broadcaster = TelemetryBroadcaster()

@app.on_event("startup")
async def startup_event():
    await broadcaster.start()
    asyncio.create_task(coordinator.ensure_binaries())

@app.get("/status")
async def get_status():
    return broadcaster.state

@app.post("/node/start")
async def start_node(req: NodeStartRequest):
    if coordinator.node.running:
        return {"success": False, "message": "Node already running"}
    asyncio.create_task(coordinator.node.run(datadir=req.datadir))
    return {"success": True, "message": "Node initialization started"}

@app.post("/node/stop")
async def stop_node():
    coordinator.node.stop()
    return {"success": True, "message": "Node shutdown sequence initiated"}

@app.post("/miner/start")
async def start_miner(req: MinerStartRequest):
    if coordinator.miner.running:
        return {"success": False, "message": "Miner already running"}
    # Update RPC credentials if needed
    rpc.user = req.rpc_user
    rpc.password = req.rpc_pass
    asyncio.create_task(coordinator.miner.run(
        req.address, req.rpc_user, req.rpc_pass, req.threads
    ))
    return {"success": True, "message": "Miner initialization started"}

@app.post("/miner/stop")
async def stop_miner():
    coordinator.miner.stop()
    return {"success": True, "message": "Miner shutdown sequence initiated"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(json.dumps(broadcaster.state))
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
