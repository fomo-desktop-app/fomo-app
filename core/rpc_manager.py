import time
import asyncio
import requests
import logging
from typing import Dict, Any

logger = logging.getLogger("FOMO.RPCManager")

class RPCManager:
    """
    Multi-chain RPC Node Failover Engine for Solana, Base, BNB, and Robinhood Chain.
    Routes transactions through nodes with sub-150ms latency.
    """

    def __init__(self, network_config: Dict[str, Any]):
        self.networks = network_config
        self.active_endpoints = {}
        self._initialize_endpoints()

    def _initialize_endpoints(self):
        """Set primary endpoints as active by default."""
        for chain, nodes in self.networks.items():
            self.active_endpoints[chain] = nodes["primary_rpc"]

    async def ping_node(self, url: str) -> float:
        """Measure round-trip time (latency) for a given RPC node endpoint in milliseconds."""
        loop = asyncio.get_event_loop()
        start_time = time.perf_counter()
        try:
            # Perform a lightweight ping/block request
            await loop.run_in_executor(
                None, 
                lambda: requests.post(url, json={"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}, timeout=1.5)
            )
            latency = (time.perf_counter() - start_time) * 1000
            return latency
        except Exception:
            return float('inf')  # Node is unreachable or timed out

    async def check_and_failover(self, chain: str) -> str:
        """
        Check active node health. Automatically route to fallback 
        if latency exceeds threshold or node becomes unresponsive.
        """
        if chain not in self.networks:
            raise ValueError(f"Unsupported chain: {chain}")

        primary_url = self.networks[chain]["primary_rpc"]
        fallback_url = self.networks[chain]["fallback_rpc"]

        primary_latency = await self.ping_node(primary_url)
        
        if primary_latency < 200:  # Healthy primary threshold
            self.active_endpoints[chain] = primary_url
            return primary_url
        
        logger.warning(f"[{chain.upper()}] Primary RPC latency high ({primary_latency:.1f}ms). Testing fallback...")
        fallback_latency = await self.ping_node(fallback_url)

        if fallback_latency < primary_latency:
            logger.info(f"[{chain.upper()}] Failover triggered -> Routing to fallback node ({fallback_latency:.1f}ms).")
            self.active_endpoints[chain] = fallback_url
            return fallback_url
        
        self.active_endpoints[chain] = primary_url
        return primary_url

    def get_rpc(self, chain: str) -> str:
        """Return currently active RPC URL for specified blockchain network."""
        return self.active_endpoints.get(chain, "")
