import random
import time
import hashlib
from typing import Dict, Any

def generate_random_address() -> str:
    return "0x" + "".join(random.choices("0123456789abcdef", k=40))

def generate_random_tx_hash() -> str:
    raw = f"{time.time()}_{random.random()}"
    return "0x" + hashlib.sha256(raw.encode()).hexdigest()

class ENISimulator:
    @staticmethod
    def simulate_event(event_type: str = "buy", custom_amount: float = None) -> Dict[str, Any]:
        """Generates a realistic simulated ENI chain event"""
        tx_hash = generate_random_tx_hash()
        eni_price = round(random.uniform(0.14, 0.18), 4)

        if event_type == "buy":
            amount = custom_amount or round(random.uniform(30000, 180000), 0)
            usd_val = round(amount * eni_price, 2)
            buyer = generate_random_address()
            return {
                "event_type": "buy",
                "tx_hash": tx_hash,
                "amount": amount,
                "usd_value": usd_val,
                "price": eni_price,
                "symbol": "ENI",
                "buyer": buyer,
                "buyer_short": f"{buyer[:6]}...{buyer[-4:]}",
                "tx_hash_short": f"{tx_hash[:8]}...{tx_hash[-6:]}",
                "timestamp": int(time.time())
            }

        elif event_type == "sell":
            amount = custom_amount or round(random.uniform(25000, 120000), 0)
            usd_val = round(amount * eni_price, 2)
            seller = generate_random_address()
            return {
                "event_type": "sell",
                "tx_hash": tx_hash,
                "amount": amount,
                "usd_value": usd_val,
                "price": eni_price,
                "symbol": "ENI",
                "seller": seller,
                "seller_short": f"{seller[:6]}...{seller[-4:]}",
                "tx_hash_short": f"{tx_hash[:8]}...{tx_hash[-6:]}",
                "timestamp": int(time.time())
            }

        elif event_type == "whale":
            amount = custom_amount or round(random.uniform(150000, 850000), 0)
            usd_val = round(amount * eni_price, 2)
            from_addr = generate_random_address()
            to_addr = generate_random_address()
            return {
                "event_type": "whale",
                "tx_hash": tx_hash,
                "amount": amount,
                "usd_value": usd_val,
                "price": eni_price,
                "symbol": "ENI",
                "from_addr": from_addr,
                "to_addr": to_addr,
                "from_short": f"{from_addr[:6]}...{from_addr[-4:]}",
                "to_short": f"{to_addr[:6]}...{to_addr[-4:]}",
                "tx_hash_short": f"{tx_hash[:8]}...{tx_hash[-6:]}",
                "timestamp": int(time.time())
            }

        elif event_type == "staking":
            actions = ["质押存入 (Stake Deposit)", "流动性添加 (Add Liquidity)", "节点委托 (Validator Delegate)"]
            action = random.choice(actions)
            pools = ["Newton Protocol Genesis Pool", "ENI/USDT LP Yield Pool", "Newton AI Compute Node Staking"]
            pool = random.choice(pools)
            amount = custom_amount or round(random.uniform(50000, 300000), 0)
            usd_val = round(amount * eni_price, 2)
            user = generate_random_address()
            return {
                "event_type": "staking",
                "tx_hash": tx_hash,
                "amount": amount,
                "usd_value": usd_val,
                "price": eni_price,
                "symbol": "ENI",
                "action_type": action,
                "pool_name": pool,
                "user": user,
                "user_short": f"{user[:6]}...{user[-4:]}",
                "tx_hash_short": f"{tx_hash[:8]}...{tx_hash[-6:]}",
                "timestamp": int(time.time())
            }

        else: # summary
            total_txs = random.randint(12500, 34200)
            vol_usd = round(random.uniform(850000, 2400000), 2)
            active_addr = random.randint(3100, 8900)
            whales = random.randint(12, 38)
            tvl_eni = round(random.uniform(15000000, 28000000), 0)
            return {
                "event_type": "summary",
                "tx_hash": "",
                "amount": 0,
                "usd_value": vol_usd,
                "total_txs": total_txs,
                "volume_usd": vol_usd,
                "active_addresses": active_addr,
                "whale_count": whales,
                "tvl_eni": tvl_eni,
                "tvl_usd": round(tvl_eni * eni_price, 2),
                "current_price": eni_price,
                "timestamp": int(time.time())
            }
