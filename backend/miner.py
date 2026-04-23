import asyncio
import json
import logging
import os
import subprocess
import time
import re
import atexit
from typing import Dict, Any, Optional, List
from deployer import SubstrateDeployer

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("substrate")

class BaseSubstrate:
    def __init__(self, name: str, exe_name: str):
        self.name = name
        self.exe_name = exe_name
        self.running = False
        self._process: Optional[subprocess.Popen] = None
        self.log_queue = []
        self.bin_dir = os.path.join(os.path.dirname(__file__), "bin")
        self.exe_path = os.path.join(self.bin_dir, self.exe_name)

    def add_log(self, category: str, message: str, custom_time: str = None):
        timestamp = custom_time if custom_time else time.strftime("%H:%M:%S")
        log_entry = {"time": timestamp, "cat": category, "msg": message, "source": self.name}
        self.log_queue.append(log_entry)
        if len(self.log_queue) > 50:
            self.log_queue.pop(0)

    def stop(self):
        self.running = False
        if self._process:
            logger.info(f"Terminating {self.name}...")
            # Use taskkill on Windows for a more aggressive cleanup if needed
            if os.name == 'nt':
                try:
                    subprocess.run(['taskkill', '/F', '/T', '/PID', str(self._process.pid)], capture_output=True)
                except:
                    self._process.terminate()
            else:
                self._process.terminate()
            
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None

def to_wsl_path(win_path: str) -> str:
    """Safely converts a Windows path to a WSL path (supports any drive letter)."""
    if not win_path: return win_path
    if ":" not in win_path: return win_path.replace("\\", "/")
    
    drive, path = win_path.split(":", 1)
    # C:\path -> /mnt/c/path
    unix_path = path.replace("\\", "/")
    return f"/mnt/{drive.lower()}{unix_path}"


class FractalNode(BaseSubstrate):
    def __init__(self):
        super().__init__("NODE", "fractald.exe")
        self.sync_progress = 0
        self.block_height = 0
        self.peers = 0
        self.is_wsl = False

    async def run(self, datadir: str = None):
        # Priority: Native Windows EXE (.exe), fallback to bitcoind (WSL)
        exe_path = self.exe_path
        if not os.path.exists(exe_path):
            linux_path = os.path.join(self.bin_dir, "bitcoind")
            if os.path.exists(linux_path):
                # Verify WSL environment
                has_wsl, wsl_state = SubstrateDeployer(self.bin_dir).is_wsl_available()
                if not has_wsl:
                    if wsl_state == "COMMAND_NOT_FOUND":
                        self.add_log("ERROR", "WSL is not installed. Please install WSL and Ubuntu.")
                    elif wsl_state == "DOCKER_DESKTOP_ONLY":
                        self.add_log("ERROR", "WSL is set to 'docker-desktop'. Please install Ubuntu: run 'wsl --install -d Ubuntu'")
                    else:
                        self.add_log("ERROR", "WSL found but no Linux distro is installed. Please run 'wsl --install'.")
                    return
                self.is_wsl = True
                exe_path = linux_path
            else:
                self.add_log("ERROR", "Substrate binary missing. Re-acquiring...")
                return

        self.running = True
        
        if self.is_wsl:
            wsl_path = to_wsl_path(exe_path)
            # Ensure executable permission inside WSL
            subprocess.run(["wsl", "chmod", "+x", wsl_path], capture_output=True)
            cmd = ["wsl", wsl_path, "-server", "-rest"]
            if datadir:
                cmd.append("-datadir=" + to_wsl_path(datadir))
        else:
            cmd = [exe_path, "-server", "-rest"]
            if datadir:
                cmd.extend(["-datadir=" + datadir])

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            asyncio.create_task(self.pipe_logs())
            
            while self.running:
                if self._process.poll() is not None:
                    self.add_log("ERROR", "Node process terminated unexpectedly.")
                    break
                await asyncio.sleep(1)
        except Exception as e:
            self.add_log("ERROR", f"Failed to launch Node: {e}")
        finally:
            self.stop()

    async def pipe_logs(self):
        if not self._process or not self._process.stdout: return
        while self.running and self._process.poll() is None:
            line = await asyncio.get_event_loop().run_in_executor(None, self._process.stdout.readline)
            if not line: break
            msg = line.decode().strip()
            if msg:
                # Basic parsing for sync info
                if "UpdateTip" in msg:
                    # Example: UpdateTip: new best=... height=123
                    match = re.search(r"height=(\d+)", msg)
                    if match: self.block_height = int(match.group(1))
                self.add_log("INFO", msg)

class FractalMiner(BaseSubstrate):
    def __init__(self):
        super().__init__("MINER", "fractal-miner.exe")
        self.hashrate = 0
        self.shares = 0

    async def run(self, address: str, rpc_user: str, rpc_pass: str, threads: int = 1):
        if not os.path.exists(self.exe_path):
            self.add_log("ERROR", f"Substrate {self.exe_name} not found in bin/.")
            return

        self.running = True
        cmd = [
            self.exe_path,
            "--rpc-addr", "127.0.0.1:18332",
            "--rpc-user", rpc_user,
            "--rpc-pass", rpc_pass,
            "--address", address,
            "--threads", str(threads)
        ]

        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            asyncio.create_task(self.pipe_logs())
            
            while self.running:
                if self._process.poll() is not None:
                    self.add_log("ERROR", "Miner process terminated unexpectedly.")
                    break
                await asyncio.sleep(1)
        except Exception as e:
            self.add_log("ERROR", f"Failed to launch Miner: {e}")
        finally:
            self.stop()

    async def pipe_logs(self):
        if not self._process or not self._process.stdout: return
        while self.running and self._process.poll() is None:
            line = await asyncio.get_event_loop().run_in_executor(None, self._process.stdout.readline)
            if not line: break
            msg = line.decode().strip()
            if msg:
                # Basic parsing for hashrate
                # Example: [MINER] Speed: 1.23 MH/s
                match = re.search(r"Speed:\s+([\d\.]+)", msg)
                if match: self.hashrate = float(match.group(1))
                self.add_log("PROC", msg)

class SubstrateCoordinator:
    def __init__(self):
        self.node = FractalNode()
        self.miner = FractalMiner()
        self.log_queue = []
        self._health_task = None
        self.deployer = SubstrateDeployer(os.path.join(os.path.dirname(__file__), "bin"))
        # Add initial system log
        self.node.add_log("SYSTEM", "Fractal Substrate Coordinator V4.1.1 ONLINE")
        atexit.register(self.stop_all)

    async def ensure_binaries(self):
        if not self.deployer.check_binaries():
            self.node.add_log("DEPLOY", "Substrates missing. Starting automated cloud acquisition...")
            if not os.path.exists(os.path.join(self.deployer.bin_dir, "bitcoind")) and \
               not os.path.exists(os.path.join(self.deployer.bin_dir, "fractald.exe")):
                await self.deployer.deploy_node()
            
            if not os.path.exists(os.path.join(self.deployer.bin_dir, "fractal-miner.exe")):
                await self.deployer.deploy_miner()
            
            self.node.add_log("SUCCESS", "All substrates deployed and verified.")
        else:
            self.node.add_log("DEBUG", "Substrate integrity verified locally.")


    def start_health_monitor(self):
        if not self._health_task:
            self._health_task = asyncio.create_task(self.health_check_loop())

    async def health_check_loop(self):
        """Monitors Node-Miner coupling and halts miner if node fails"""
        while True:
            if self.miner.running and not self.node.running:
                self.miner.add_log("ERROR", "Node failure detected. Auto-halting miner for safety.")
                self.miner.stop()
            await asyncio.sleep(5)

    def get_logs(self):
        all_logs = self.node.log_queue + self.miner.log_queue
        all_logs.sort(key=lambda x: x["time"])
        return all_logs[-50:]

    def stop_all(self):
        logger.info("Watchdog: Cleaning up all substrates...")
        self.node.stop()
        self.miner.stop()

    @property
    def running(self):
        return self.node.running or self.miner.running
