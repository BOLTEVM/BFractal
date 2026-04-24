import base64
import json
import asyncio
import urllib.request
import logging

logger = logging.getLogger("rpc")

class FractalRPCClient:
    def __init__(self, host="127.0.0.1", port=18332, user=None, password=None):
        self.url = f"http://{host}:{port}"
        self.user = user
        self.password = password
        self._id = 0

    async def call(self, method, params=[]):
        self._id += 1
        payload = {
            "jsonrpc": "2.0",
            "id": self._id,
            "method": method,
            "params": params
        }
        
        headers = {'Content-Type': 'application/json'}
        if self.user and self.password:
            auth = base64.b64encode(f"{self.user}:{self.password}".encode()).decode()
            headers['Authorization'] = f"Basic {auth}"

        try:
            # We use await-in-executor to keep it async friendly for FastAPI
            def do_request():
                req = urllib.request.Request(
                    self.url, 
                    data=json.dumps(payload).encode(),
                    headers=headers,
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=5) as response:
                    return json.loads(response.read().decode())

            return await asyncio.get_event_loop().run_in_executor(None, do_request)
        except Exception as e:
            # Change to debug to avoid spamming the console when node is starting up
            logger.debug(f"RPC connection pending for {method}: {e}")
            return {"error": str(e), "result": None}

    async def get_blockchain_info(self):
        return await self.call("getblockchaininfo")

    async def get_network_info(self):
        return await self.call("getnetworkinfo")

    async def get_mining_info(self):
        return await self.call("getmininginfo")
