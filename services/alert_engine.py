import asyncio
from typing import Dict, Any, Optional, Callable, List
from config import AppConfig
from database import (
    is_tx_processed, mark_tx_processed, record_post_history,
    get_app_config
)
from image_generator import create_alert_card
from publishers.telegram_bot import TelegramPublisher
from publishers.twitter_client import TwitterPublisher

ENGLISH_TEMPLATES = {
    "buy": (
        "🟢 <b>【ENI DEX Large Buy Alert】</b> 🟢\n\n"
        "💰 <b>Buy Amount:</b> <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
        "🏷 <b>Execution Price:</b> <b>${price:.4f}</b>\n"
        "👤 <b>Buyer Address:</b> <code>{buyer_short}</code>\n"
        "🔗 <b>Tx Hash:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
        "🚀 <i>High-frequency trading activity on ENI Chain. Newton Protocol ecosystem is expanding!</i>\n"
        "#ENI #DEX #BuyAlert #ENIChain #Web3"
    ),
    "sell": (
        "🔴 <b>【ENI DEX Sell Alert】</b> 🔴\n\n"
        "📉 <b>Sell Amount:</b> <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
        "🏷 <b>Execution Price:</b> <b>${price:.4f}</b>\n"
        "👤 <b>Seller Address:</b> <code>{seller_short}</code>\n"
        "🔗 <b>Tx Hash:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
        "⚡ <i>Real-time liquidity and automated AMM tracking on ENI Chain</i>\n"
        "#ENI #DEX #SellAlert #ENIChain"
    ),
    "whale": (
        "🐋 <b>【ENI Chain Whale Movement Alert】</b> 🐋\n\n"
        "🚨 <b>Large On-Chain Transfer Detected!</b>\n"
        "💎 <b>Transfer Amount:</b> <b>{amount:,.0f} {symbol}</b>\n"
        "💵 <b>Estimated Value:</b> <b>${usd_value:,.2f}</b>\n"
        "📤 <b>From:</b> <code>{from_short}</code>\n"
        "📥 <b>To:</b> <code>{to_short}</code>\n"
        "🔗 <b>Tx Hash:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
        "🌐 <i>Monitoring on-chain liquidity shifts & major token distribution</i>\n"
        "#ENI #WhaleAlert #Crypto #Blockchain #ENIChain"
    ),
    "staking": (
        "💎 <b>【ENI Staking & Liquidity Alert】</b> 💎\n\n"
        "⚡ <b>Action:</b> {action_type}\n"
        "💰 <b>Amount:</b> <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
        "🏛 <b>Pool / Contract:</b> <b>{pool_name}</b>\n"
        "👤 <b>User Address:</b> <code>{user_short}</code>\n"
        "🔗 <b>Tx Hash:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
        "🌟 <i>Strengthening decentralized consensus & earning staking yield with Newton Protocol!</i>\n"
        "#ENI #Staking #Newton #DeFi"
    ),
    "summary": (
        "📊 <b>【ENI Chain Real-Time Network Report】</b> 📊\n\n"
        "🌐 <b>Network:</b> <b>ENI Mainnet (ChainID: {chain_id})</b>\n"
        "🧱 <b>Block Height:</b> <b>#{total_blocks:,}</b>\n"
        "📈 <b>Total Transactions:</b> <b>{total_txs:,}</b>\n"
        "👥 <b>Unique Addresses:</b> <b>{active_addresses:,}</b>\n"
        "⚡ <b>24H Transactions:</b> <b>{transactions_today:,}</b>\n"
        "⛽ <b>Average Gas:</b> <b>{gas_price} Gwei</b>\n"
        "⏱ <b>Block Time:</b> <b>{block_time}s</b>\n\n"
        "🌐 <b>Blockscout Explorer:</b> <a href='{explorer_url}'>scan.eniac.network</a>\n"
        "#ENI #ENIChain #BlockchainReport #Mainnet"
    ),
    "news": (
        "🌍 <b>【Global Crypto Breaking News】</b> 🌍\n\n"
        "📰 <b>{news_title}</b>\n\n"
        "📌 <b>Summary:</b> {news_summary}\n"
        "🏛 <b>Source:</b> <b>{news_source}</b>\n"
        "⏰ <b>Published:</b> {news_time}\n"
        "🔗 <b>Original Article:</b> <a href='{news_url}'>Read Full Story</a>\n\n"
        "⚡ <i>ENI Chain × Newton Protocol Intelligence Feed</i>\n"
        "#CryptoNews #Blockchain #Web3 #Crypto #Bitcoin #ENIChain"
    )
}

CHINESE_TEMPLATES = {
    "buy": (
        "🟢 <b>【ENI DEX 大额买单提醒】</b> 🟢\n\n"
        "💰 <b>买入金额:</b> <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
        "🏷 <b>成交均价:</b> <b>${price:.4f}</b>\n"
        "👤 <b>买方地址:</b> <code>{buyer_short}</code>\n"
        "🔗 <b>交易哈希:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
        "🚀 <i>ENI Chain 链上交易活跃，牛顿协议生态持续增长！</i>\n"
        "#ENI #DEX #BuyAlert #ENIChain"
    ),
    "sell": (
        "🔴 <b>【ENI DEX 卖出成交提醒】</b> 🔴\n\n"
        "📉 <b>卖出金额:</b> <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
        "🏷 <b>成交均价:</b> <b>${price:.4f}</b>\n"
        "👤 <b>卖方地址:</b> <code>{seller_short}</code>\n"
        "🔗 <b>交易哈希:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
        "⚡ <i>实时流动性与自动化做市监控</i>\n"
        "#ENI #DEX #SellAlert"
    ),
    "whale": (
        "🐋 <b>【ENI 巨鲸链上异动提醒】</b> 🐋\n\n"
        "🚨 <b>监测到大额链上转账！</b>\n"
        "💎 <b>转移数量:</b> <b>{amount:,.0f} {symbol}</b>\n"
        "💵 <b>预估价值:</b> <b>${usd_value:,.2f}</b>\n"
        "📤 <b>发送地址:</b> <code>{from_short}</code>\n"
        "📥 <b>接收地址:</b> <code>{to_short}</code>\n"
        "🔗 <b>交易哈希:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
        "🌐 <i>监控链上大单流动与筹码再分配</i>\n"
        "#ENI #WhaleAlert #ENIChain"
    ),
    "staking": (
        "💎 <b>【ENI 生态质押/流动性提醒】</b> 💎\n\n"
        "⚡ <b>类型:</b> {action_type}\n"
        "💰 <b>数量:</b> <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
        "🏛 <b>矿池/合约:</b> <b>{pool_name}</b>\n"
        "👤 <b>用户地址:</b> <code>{user_short}</code>\n"
        "🔗 <b>交易哈希:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
        "🌟 <i>参与牛顿原生协议，共享生态收益！</i>\n"
        "#ENI #Staking #Newton"
    ),
    "summary": (
        "📊 <b>【ENI Chain 链上实时数据报告】</b> 📊\n\n"
        "🌐 <b>网络:</b> <b>ENI Mainnet (ChainID: {chain_id})</b>\n"
        "🧱 <b>最新区块高度:</b> <b>#{total_blocks:,}</b>\n"
        "📈 <b>链上交易总数:</b> <b>{total_txs:,}</b> 笔\n"
        "👥 <b>独立持币地址:</b> <b>{active_addresses:,}</b> 个\n"
        "⚡ <b>24H 链上交易数:</b> <b>{transactions_today:,}</b> 笔\n"
        "⛽ <b>平均 Gas 价格:</b> <b>{gas_price} Gwei</b>\n"
        "⏱ <b>平均出块时间:</b> <b>{block_time} 秒</b>\n\n"
        "🌐 <b>区块浏览器查看：</b> <a href='{explorer_url}'>scan.eniac.network</a>\n"
        "#ENI #ENIChain #BlockchainReport #Mainnet"
    ),
    "news": (
        "🌍 <b>【区块链国际要闻快讯】</b> 🌍\n\n"
        "📰 <b>{news_title}</b>\n\n"
        "📌 <b>核心摘要:</b> {news_summary}\n"
        "🏛 <b>来源机构:</b> <b>{news_source}</b>\n"
        "⏰ <b>发布时间:</b> {news_time}\n"
        "🔗 <b>原文链接:</b> <a href='{news_url}'>点击阅读全文</a>\n\n"
        "⚡ <i>ENI Chain × Newton 国际前沿资讯同步</i>\n"
        "#CryptoNews #Blockchain #Web3 #Crypto #Bitcoin"
    )
}

class AlertEngine:
    def __init__(self):
        self._listeners: List[Callable[[Dict[str, Any]], Any]] = []

    def subscribe(self, callback: Callable[[Dict[str, Any]], Any]):
        self._listeners.append(callback)

    def unsubscribe(self, callback: Callable[[Dict[str, Any]], Any]):
        if callback in self._listeners:
            self._listeners.remove(callback)

    async def broadcast_event(self, event_data: Dict[str, Any]):
        for cb in list(self._listeners):
            try:
                if asyncio.iscoroutinefunction(cb):
                    await cb(event_data)
                else:
                    cb(event_data)
            except Exception as e:
                print(f"[AlertEngine] Broadcast error: {e}")

    def format_template(self, template_str: str, data: Dict[str, Any], config: AppConfig) -> str:
        ctx = {
            "explorer_url": config.chain.explorer_url,
            "chain_name": config.chain.chain_name,
            "chain_id": config.chain.chain_id,
            "symbol": data.get("symbol", config.chain.token_symbol),
            "amount": data.get("amount", 0.0),
            "usd_value": data.get("usd_value", 0.0),
            "price": data.get("price", config.chain.token_price_usd),
            "current_price": data.get("current_price", config.chain.token_price_usd),
            "tx_hash": data.get("tx_hash", ""),
            "tx_hash_short": data.get("tx_hash_short", ""),
            "buyer": data.get("buyer", ""),
            "buyer_short": data.get("buyer_short", ""),
            "seller": data.get("seller", ""),
            "seller_short": data.get("seller_short", ""),
            "from_addr": data.get("from_addr", ""),
            "from_short": data.get("from_short", ""),
            "to_addr": data.get("to_addr", ""),
            "to_short": data.get("to_short", ""),
            "action_type": data.get("action_type", ""),
            "pool_name": data.get("pool_name", ""),
            "user": data.get("user", ""),
            "user_short": data.get("user_short", ""),
            "total_blocks": data.get("total_blocks", 0),
            "total_txs": data.get("total_txs", 0),
            "volume_usd": data.get("volume_usd", 0.0),
            "active_addresses": data.get("active_addresses", 0),
            "transactions_today": data.get("transactions_today", 0),
            "gas_price": data.get("gas_price", 87.3),
            "block_time": data.get("block_time", 1.0),
            "whale_count": data.get("whale_count", 0),
            "tvl_eni": data.get("tvl_eni", 0.0),
            "tvl_usd": data.get("tvl_usd", 0.0),
            "news_title": data.get("news_title", ""),
            "news_summary": data.get("news_summary", ""),
            "news_source": data.get("news_source", ""),
            "news_time": data.get("news_time", ""),
            "news_url": data.get("news_url", "")
        }
        try:
            return template_str.format(**ctx)
        except Exception as e:
            print(f"[AlertEngine] Template format error ({e}), using default format")
            if "news_title" in data:
                return f"【GLOBAL CRYPTO NEWS】\n{data.get('news_title')}\nSource: {data.get('news_source')}\nLink: {data.get('news_url')}"
            return f"【{data.get('event_type', '').upper()} ALERT】\nAmount: {ctx['amount']} {ctx['symbol']} (${ctx['usd_value']:,.2f})\nTx: {ctx['tx_hash']}"

    async def process_event(self, raw_data: Dict[str, Any], config: Optional[AppConfig] = None) -> Dict[str, Any]:
        """Processes an on-chain event or news, checks thresholds, creates image, and publishes"""
        if not config:
            config = await get_app_config()

        event_type = raw_data.get("event_type", "whale")
        tx_hash = raw_data.get("tx_hash", "")
        news_id = raw_data.get("news_id", "")
        dedup_key = tx_hash or news_id

        amount = float(raw_data.get("amount", 0.0))
        usd_value = float(raw_data.get("usd_value", 0.0))

        # 1. Deduplication check
        if dedup_key and await is_tx_processed(dedup_key, event_type):
            return {"skipped": True, "reason": "Already processed"}

        # 2. Threshold check
        th = config.thresholds
        if event_type == "whale":
            if not th.enable_whale_alert:
                return {"skipped": True, "reason": "Whale alerts disabled"}
            if amount < th.whale_min_amount and usd_value < th.whale_min_usd:
                return {"skipped": True, "reason": f"Below whale threshold ({amount} < {th.whale_min_amount})"}

        elif event_type in ["buy", "sell"]:
            if not th.enable_dex_alert:
                return {"skipped": True, "reason": "DEX alerts disabled"}
            if amount < th.swap_min_amount and usd_value < th.swap_min_usd:
                return {"skipped": True, "reason": f"Below DEX swap threshold ({amount} < {th.swap_min_amount})"}

        elif event_type == "staking":
            if not th.enable_staking_alert:
                return {"skipped": True, "reason": "Staking alerts disabled"}
            if amount < th.staking_min_amount:
                return {"skipped": True, "reason": f"Below staking threshold ({amount} < {th.staking_min_amount})"}

        elif event_type == "summary":
            if not th.enable_daily_summary:
                return {"skipped": True, "reason": "Daily summary disabled"}

        elif event_type == "news":
            if not th.enable_global_news:
                return {"skipped": True, "reason": "Global news alerts disabled"}

        # Determine target thread
        raw_target = raw_data.get("target_thread_id")
        target_tid = str(raw_target) if raw_target is not None else str(config.telegram.thread_id or "1")
        # Target # General (thread 1, or empty/0) and English Chat (thread 16) MUST receive 100% English content
        is_general_or_en = target_tid in ["1", "16", "", "None", "0"] or not target_tid

        # 3. Select template and render text
        tm = config.templates
        if raw_data.get("content"):
            text = raw_data["content"]
            title = raw_data.get("title", f"ENI {event_type.capitalize()}")
        else:
            if is_general_or_en:
                tpl = ENGLISH_TEMPLATES.get(event_type) or tm.model_dump().get(f"{event_type}_template")
                title = f"ENI {event_type.capitalize()} Alert"
            else:
                tpl = CHINESE_TEMPLATES.get(event_type) or tm.model_dump().get(f"{event_type}_template")
                title = f"ENI {event_type.capitalize()} 提醒"
            text = self.format_template(tpl, raw_data, config)

        # 4. Generate visual card image
        image_path = None
        try:
            image_path = create_alert_card(event_type, raw_data)
        except Exception as e:
            print(f"[AlertEngine] Image generation failed: {e}")

        # 5. Prepare Telegram buttons
        buttons = []
        if config.telegram.include_buttons:
            if is_general_or_en:
                # 100% English buttons for # General and English Chat
                if tx_hash:
                    exp_url = f"{config.chain.explorer_url}/tx/{tx_hash}"
                    buttons = [
                        [
                            {"text": "🔍 View on Explorer", "url": exp_url},
                            {"text": "🔄 Newton DEX Swap", "url": "https://xplan.eniac.network/swap"}
                        ]
                    ]
                elif event_type in ["tech", "summary"]:
                    buttons = [
                        [
                            {"text": "🌐 Official Explorer", "url": "https://scan.eniac.network"},
                            {"text": "🏛 Official Portal", "url": "https://eniac.network"}
                        ]
                    ]
                elif event_type == "news" and raw_data.get("news_url"):
                    buttons = [
                        [
                            {"text": "📰 Read Full Story", "url": raw_data.get("news_url")},
                            {"text": "🌐 Official Portal", "url": "https://eniac.network"}
                        ]
                    ]
                elif event_type == "summary":
                    buttons = [
                        [
                            {"text": "🌐 Explorer Dashboard", "url": config.chain.explorer_url}
                        ]
                    ]
            else:
                # Chinese buttons for Chinese chat
                if tx_hash:
                    exp_url = f"{config.chain.explorer_url}/tx/{tx_hash}"
                    buttons = [
                        [
                            {"text": "🔍 在 scan.eniac.network 查看", "url": exp_url},
                            {"text": "🔄 牛顿 DEX 交易", "url": "https://xplan.eniac.network/swap"}
                        ]
                    ]
                elif event_type in ["tech", "summary"]:
                    buttons = [
                        [
                            {"text": "🌐 官方区块浏览器", "url": "https://scan.eniac.network"},
                            {"text": "🏛 ENI 官方网站", "url": "https://eniac.network"}
                        ]
                    ]
                elif event_type == "news" and raw_data.get("news_url"):
                    buttons = [
                        [
                            {"text": "📰 阅读全文原文", "url": raw_data.get("news_url")},
                            {"text": "🌐 ENI 官网", "url": "https://eniac.network"}
                        ]
                    ]
                elif event_type == "summary":
                    buttons = [
                        [
                            {"text": "🌐 进入 scan.eniac.network 浏览器", "url": config.chain.explorer_url}
                        ]
                    ]

        # 6. Dispatch to Telegram
        tg_status, tg_msg_id, tg_error = "skipped", None, None
        if config.auto_publish and config.telegram.enabled:
            tg_res = await TelegramPublisher.send_alert(
                bot_token=config.telegram.bot_token,
                chat_id=config.telegram.chat_id,
                text=text,
                image_path=image_path if config.telegram.send_images else None,
                buttons=buttons if config.telegram.include_buttons else None,
                thread_id=target_tid
            )
            if tg_res.get("success"):
                tg_status = "success"
                tg_msg_id = tg_res.get("message_id")
            else:
                tg_status = "failed"
                tg_error = tg_res.get("error")

        # 7. Dispatch to Twitter / X
        tw_status, tw_tweet_id, tw_error = "skipped", None, None
        if config.auto_publish and config.twitter.enabled:
            tweet_body = f"{text}\n\n{config.twitter.custom_hashtags}"
            tw_res = TwitterPublisher.post_tweet(
                api_key=config.twitter.api_key,
                api_secret=config.twitter.api_secret,
                access_token=config.twitter.access_token,
                access_token_secret=config.twitter.access_token_secret,
                text=tweet_body,
                image_path=image_path if config.twitter.send_images else None
            )
            if tw_res.get("success"):
                tw_status = "success"
                tw_tweet_id = tw_res.get("tweet_id")
            else:
                tw_status = "failed"
                tw_error = tw_res.get("error")

        # 8. Record to Database
        post_id = await record_post_history(
            event_type=event_type,
            tx_hash=dedup_key,
            title=title,
            content=text,
            image_path=image_path,
            amount=amount,
            usd_value=usd_value,
            telegram_status=tg_status,
            telegram_msg_id=tg_msg_id,
            telegram_error=tg_error,
            twitter_status=tw_status,
            twitter_tweet_id=tw_tweet_id,
            twitter_error=tw_error
        )

        if dedup_key:
            await mark_tx_processed(dedup_key, event_type)

        result_payload = {
            "post_id": post_id,
            "event_type": event_type,
            "tx_hash": tx_hash,
            "news_id": news_id,
            "title": title,
            "content": text,
            "image_path": image_path,
            "amount": amount,
            "usd_value": usd_value,
            "telegram": {"status": tg_status, "msg_id": tg_msg_id, "error": tg_error},
            "twitter": {"status": tw_status, "tweet_id": tw_tweet_id, "error": tw_error}
        }

        # 9. Broadcast to live dashboard
        await self.broadcast_event(result_payload)
        return result_payload

alert_engine = AlertEngine()
