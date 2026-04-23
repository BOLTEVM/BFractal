import os
import sys
import urllib.request
import tarfile
import zipfile
import shutil
import subprocess
import logging
import json
import time
import asyncio

logger = logging.getLogger("deployer")

# Use official Linux release for Linux/WSL, but a trusted community build for native Windows
FRACTAL_RELEASE_URL = "https://api.github.com/repos/fractal-bitcoin/fractald-release/releases/latest"
FRACTAL_WINDOWS_URL = "https://api.github.com/repos/m-rezaei/fractal-bitcoin-windows/releases/latest"
MINER_RELEASE_URL = "https://api.github.com/repos/fractal-bitcoin/fractal-miner/releases/latest"

class SubstrateDeployer:
    def __init__(self, bin_dir: str):
        self.bin_dir = bin_dir
        self.cache_path = os.path.join(self.bin_dir, "release_cache.json")
        os.makedirs(self.bin_dir, exist_ok=True)

    def is_wsl_available(self):
        try:
            # Check for wsl command
            res = subprocess.run(["wsl", "--list", "--quiet"], capture_output=True, text=True)
            if res.returncode == 0 and res.stdout.strip():
                return True, "READY"
            return False, "NO_DISTRO"
        except:
            return False, "COMMAND_NOT_FOUND"

    def check_binaries(self):
        node_exists = os.path.exists(os.path.join(self.bin_dir, "fractald.exe")) or \
                      os.path.exists(os.path.join(self.bin_dir, "bitcoind"))
        miner_exists = os.path.exists(os.path.join(self.bin_dir, "fractal-miner.exe"))
        return node_exists and miner_exists

    def get_cached_release(self, key):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r') as f:
                    cache = json.load(f)
                    entry = cache.get(key)
                    if entry and (time.time() - entry.get("timestamp", 0)) < 86400: # 24h
                        return entry.get("url"), entry.get("filename")
            except: pass
        return None, None

    def set_cached_release(self, key, url, filename):
        cache = {}
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, 'r') as f: cache = json.load(f)
            except: pass
        
        cache[key] = {"url": url, "filename": filename, "timestamp": time.time()}
        with open(self.cache_path, 'w') as f:
            json.dump(cache, f)

    def download_github_release(self, api_url, asset_pattern):
        # Try cache first
        cached_url, cached_file = self.get_cached_release(api_url)
        if cached_url:
            logger.info(f"Using cached release metadata for {api_url}")
            return cached_url, cached_file

        try:
            req = urllib.request.Request(api_url, headers={"User-Agent": "Fractal-Deployer"})
            with urllib.request.urlopen(req) as response:
                data = json.loads(response.read().decode())
                for asset in data.get("assets", []):
                    if asset_pattern in asset["name"]:
                        url, filename = asset["browser_download_url"], asset["name"]
                        self.set_cached_release(api_url, url, filename)
                        return url, filename
        except Exception as e:
            logger.error(f"Failed to fetch release from {api_url}: {e}")
        return None, None

    def is_safe_path(self, path):
        full_path = os.path.realpath(os.path.join(self.bin_dir, path))
        return full_path.startswith(os.path.realpath(self.bin_dir))

    async def deploy_node(self):
        logger.info("Initializing Node deployment...")
        if os.name == 'nt':
            url, filename = self.download_github_release(FRACTAL_WINDOWS_URL, "win64.zip")
            if not url: url, filename = self.download_github_release(FRACTAL_WINDOWS_URL, "windows.zip")
            
            if not url:
                logger.warning("Native Windows build not found, falling back to Linux/WSL substrate.")
                return await self._deploy_node_linux()
            
            target_path = os.path.join(self.bin_dir, filename)
            logger.info(f"Downloading Native Node from {url}...")
            def download(): urllib.request.urlretrieve(url, target_path)
            await asyncio.get_event_loop().run_in_executor(None, download)
            
            logger.info("Extracting Native Node substrate...")
            with zipfile.ZipFile(target_path, 'r') as zip_ref:
                for member in zip_ref.namelist():
                    if member.endswith("bitcoind.exe") or member.endswith("fractald.exe"):
                        with zip_ref.open(member) as source, open(os.path.join(self.bin_dir, "fractald.exe"), 'wb') as target:
                            shutil.copyfileobj(source, target)
                        break
            os.remove(target_path)
            logger.info("Native Node substrate deployed successfully.")
            return True
        else:
            return await self._deploy_node_linux()

    async def _deploy_node_linux(self):
        url, filename = self.download_github_release(FRACTAL_RELEASE_URL, "linux-gnu.tar.gz")
        if not url: return False
        target_path = os.path.join(self.bin_dir, filename)
        logger.info(f"Downloading Linux Node from {url}...")
        def download(): urllib.request.urlretrieve(url, target_path)
        await asyncio.get_event_loop().run_in_executor(None, download)
        logger.info("Extracting Linux Node substrate...")
        if filename.endswith(".tar.gz"):
            with tarfile.open(target_path, "r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith("bitcoind"):
                        member.name = os.path.basename(member.name)
                        tar.extract(member, self.bin_dir)
                        break
        os.remove(target_path)
        logger.info("Node substrate deployed successfully.")
        return True

    async def deploy_miner(self):
        logger.info("Initializing Miner deployment...")
        url, filename = self.download_github_release(MINER_RELEASE_URL, "win64.zip")
        if not url: url, filename = self.download_github_release(MINER_RELEASE_URL, "windows.zip")
        if not url: return False
        target_path = os.path.join(self.bin_dir, filename)
        logger.info(f"Downloading Miner from {url}...")
        def download(): urllib.request.urlretrieve(url, target_path)
        await asyncio.get_event_loop().run_in_executor(None, download)
        logger.info("Extracting Miner substrate...")
        with zipfile.ZipFile(target_path, 'r') as zip_ref:
            for member in zip_ref.namelist():
                if member.endswith(".exe"):
                    with zip_ref.open(member) as source, open(os.path.join(self.bin_dir, "fractal-miner.exe"), 'wb') as target:
                        shutil.copyfileobj(source, target)
                    break
        os.remove(target_path)
        logger.info("Miner substrate deployed successfully.")
        return True
