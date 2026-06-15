import asyncio
import aiohttp
import uuid
from datetime import datetime

class CSFAegisBridge:
    """ Routes Linux Firewall Daemon intrusions to the Univac Aegis threat matrix """
    def __init__(self, aegis_url: str):
        self.aegis_url = aegis_url
        self.session = None
        self.node_id = "CSF-Cyber-Node-01"

    async def initialize(self):
        """ Instantiates the asynchronous HTTP session """
        self.session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=3.0))

    async def shutdown(self):
        """ Gracefully closes the outbound sockets """
        if not self.session:
            return
        await self.session.close()

    async def dispatch_intrusion(self, target_ip: str, block_reason: str):
        """ Executes the Guard Clause and routes the block event """
        if not self.session:
            return

        aegis_payload = {
            "EventId": str(uuid.uuid4()),
            "Timestamp": datetime.utcnow().isoformat() + "Z",
            "SourceNode": self.node_id,
            "EventType": "CYBER_INTRUSION_BLOCKED",
            "SeverityLevel": 8,
            "RawProtocolData": target_ip + " | " + block_reason
        }

        headers = {"X-Aegis-Client": self.node_id, "Content-Type": "application/json"}
        
        try:
            await self.session.post(self.aegis_url, json=aegis_payload, headers=headers)
        except Exception:
            pass
