import asyncio
import httpx
from typing import Optional, Dict, Any, List
from config import AppConfig
from database import get_app_config, save_app_config, is_tx_processed
from services.alert_engine import alert_engine
from services.simulator import ENISimulator
from services.eni_live_tracker import eni_live_tracker
from services.global_news_tracker import global_news_tracker

TOPIC_TRANSFER = "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef"
TOPIC_SWAP = "0xd78ad97fa46c994b6551d0da85fc275fe613ce37657fb8d5e3d130840159d822"

class ENIWatcher:
    def __init__(self):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.rpc_status = "idle"
        self.last_scanned_block = 0
        self.last_error = ""
        self.last_stats = {}
        self.last_news_poll_time = 0

    async def get_block_number(self, rpc_url: str) -> Optional[int]:
        """Calls eth_blockNumber on ENI Chain RPC"""
        async with httpx.AsyncClient(timeout=8.0) as client:
            payload = {"jsonrpc": "2.0", "method": "eth_blockNumber", "params": [], "id": 1}
            try:
                resp = await client.post(rpc_url, json=payload)
                if resp.status_code == 200:
                    result = resp.json().get("result")
                    if result:
                        return int(result, 16)
            except Exception as e:
                self.last_error = str(e)
        return None

    async def poll_explorer_transactions(self, config: AppConfig):
        """Fetches live transactions directly from scan.eniac.network and monitors for large movements"""
        txs = await eni_live_tracker.get_live_transactions(limit=15)
        for tx in txs:
            val_egas = tx.get("value_egas", 0.0)
            tx_hash = tx.get("tx_hash", "")
            if not tx_hash or await is_tx_processed(tx_hash, "whale"):
                continue

            # Check if whale transfer of native gas / token
            usd_val = val_egas * config.chain.token_price_usd
            if val_egas >= config.thresholds.whale_min_amount or usd_val >= config.thresholds.whale_min_usd:
                event = {
                    "event_type": "whale",
                    "tx_hash": tx_hash,
                    "amount": val_egas,
                    "usd_value": usd_val,
                    "symbol": "EGAS",
                    "price": config.chain.token_price_usd,
                    "from_addr": tx.get("from_addr", ""),
                    "to_addr": tx.get("to_addr", ""),
                    "from_short": tx.get("from_short", ""),
                    "to_short": tx.get("to_short", ""),
                    "tx_hash_short": tx.get("tx_hash_short", ""),
                    "block_number": tx.get("block_number", 0)
                }
                await alert_engine.process_event(event, config)

    async def check_global_news(self, config: AppConfig):
        """Polls global crypto news feeds and posts top breaking news"""
        now = asyncio.get_event_loop().time()
        poll_interval_sec = config.thresholds.news_poll_interval * 60
        if now - self.last_news_poll_time < poll_interval_sec:
            return

        self.last_news_poll_time = now
        news_items = await global_news_tracker.get_latest_news(limit=5)
        for n in news_items:
            nid = n.get("news_id", "")
            if not await is_tx_processed(nid, "news"):
                event = {
                    "event_type": "news",
                    "news_id": nid,
                    "news_title": n.get("news_title", ""),
                    "news_url": n.get("news_url", ""),
                    "news_summary": n.get("news_summary", ""),
                    "news_time": n.get("news_time", ""),
                    "news_source": n.get("news_source", "")
                }
                await alert_engine.process_event(event, config)
                break  # publish one fresh breaking news at a time

    async def _run_loop(self):
        print("[ENI Watcher] Started live monitoring on scan.eniac.network & RPC...")
        loop_tick = 0

        while self.is_running:
            try:
                config = await get_app_config()
                current_block = await self.get_block_number(config.chain.rpc_url)

                if current_block is not None:
                    self.rpc_status = "connected"
                    self.last_error = ""
                    self.last_scanned_block = current_block
                else:
                    self.rpc_status = "unreachable"

                # Update live stats from scan.eniac.network
                if loop_tick % 3 == 0:
                    stats = await eni_live_tracker.get_live_stats()
                    if stats:
                        self.last_stats = stats
                        if not self.last_scanned_block and stats.get("total_blocks"):
                            self.last_scanned_block = stats["total_blocks"]

                # Scan explorer live transactions
                if loop_tick % 2 == 0:
                    await self.poll_explorer_transactions(config)

                # Check international breaking news
                if config.thresholds.enable_global_news and loop_tick % 10 == 0:
                    await self.check_global_news(config)

                # If simulation mode is explicitly enabled
                if config.simulation_mode and loop_tick % 6 == 0:
                    import random
                    sim_type = random.choice(["buy", "sell", "whale", "staking"])
                    sim_event = ENISimulator.simulate_event(sim_type)
                    await alert_engine.process_event(sim_event, config)

                loop_tick += 1

            except Exception as e:
                self.last_error = f"Loop exception: {e}"
                print(f"[ENI Watcher] Loop exception: {e}")

            await asyncio.sleep(max(2, config.chain.polling_interval if 'config' in locals() else 4))

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._run_loop())

    def stop(self):
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_running": self.is_running,
            "rpc_status": self.rpc_status,
            "last_scanned_block": self.last_scanned_block,
            "last_error": self.last_error,
            "live_stats": self.last_stats
        }

eni_watcher = ENIWatcher()
