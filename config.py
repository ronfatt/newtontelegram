import os
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

class ChainSettings(BaseModel):
    rpc_url: str = Field(default="https://rpc.eniac.network", description="ENI Chain Mainnet JSON-RPC URL")
    chain_id: int = Field(default=173, description="Chain ID of ENI Mainnet (173)")
    chain_name: str = Field(default="ENI Mainnet", description="Display name")
    explorer_url: str = Field(default="https://scan.eniac.network", description="Explorer base URL")
    api_url: str = Field(default="https://scan.eniac.network/api/v2", description="Blockscout v2 API endpoint")
    token_address: str = Field(default="0x6D1e851446F4D004AE2A72F9AfEd85e8829A205E", description="ENI / Newton Verified Contract Address")
    token_symbol: str = Field(default="ENI", description="Token Symbol")
    token_decimals: int = Field(default=18, description="Token Decimals")
    token_price_usd: float = Field(default=0.15, description="Estimated/Oracle token price in USD")
    dex_pair_address: Optional[str] = Field(default="0x50616972454e4955534454303030303030303031", description="DEX Liquidity Pair Address")
    staking_contract: Optional[str] = Field(default="0x5374616b696e67506f6f6c303030303030303031", description="Staking Pool Contract Address")
    polling_interval: int = Field(default=4, description="Polling interval in seconds")
    last_scanned_block: int = Field(default=0, description="Last scanned block number")

class AlertThresholds(BaseModel):
    whale_min_amount: float = Field(default=50000.0, description="Minimum ENI amount to trigger Whale Alert")
    whale_min_usd: float = Field(default=7500.0, description="Minimum USD value for Whale Alert")
    whale_usd_threshold: Optional[float] = Field(default=None, description="Alias for whale_min_usd")
    swap_min_amount: float = Field(default=10000.0, description="Minimum ENI amount to trigger DEX Swap Alert")
    swap_min_usd: float = Field(default=1500.0, description="Minimum USD value for DEX Swap Alert")
    staking_min_amount: float = Field(default=20000.0, description="Minimum ENI amount to trigger Staking Alert")
    enable_whale_alert: bool = Field(default=True)
    enable_dex_alert: bool = Field(default=True)
    enable_staking_alert: bool = Field(default=True)
    enable_daily_summary: bool = Field(default=True)
    enable_global_news: bool = Field(default=True, description="Enable global international blockchain news alerts")
    news_poll_interval: int = Field(default=15, description="Interval in minutes to poll international news")

class TelegramSettings(BaseModel):
    enabled: bool = Field(default=False)
    bot_token: str = Field(default="", description="Telegram Bot API Token (from @BotFather)")
    chat_id: str = Field(default="", description="Target Chat ID or Channel (@channel_name or -100xxx)")
    thread_id: Optional[str] = Field(default="", description="Optional Message Thread ID for forum groups")
    send_images: bool = Field(default=True, description="Generate and attach visual alert card")
    include_buttons: bool = Field(default=True, description="Include explorer / swap inline buttons")

class TwitterSettings(BaseModel):
    enabled: bool = Field(default=False)
    api_key: str = Field(default="", description="Twitter Consumer API Key")
    api_secret: str = Field(default="", description="Twitter Consumer API Secret")
    access_token: str = Field(default="", description="Twitter Access Token")
    access_token_secret: str = Field(default="", description="Twitter Access Token Secret")
    send_images: bool = Field(default=True, description="Attach visual card to tweets")
    custom_hashtags: str = Field(default="#ENIChain #Newton #Crypto #WhaleAlert #Web3", description="Hashtags appended to tweets")

class TemplatesSettings(BaseModel):
    buy_template: str = Field(
        default="🟢 <b>【ENI DEX 大额买单提醒】</b> 🟢\n\n"
                "💰 买入金额: <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
                "🏷 成交均价: <b>${price:.4f}</b>\n"
                "👤 买方地址: <code>{buyer_short}</code>\n"
                "🔗 交易哈希: <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
                "🚀 ENI Chain 链上交易活跃，牛顿协议生态持续增长！\n"
                "#ENI #DEX #BuyAlert #ENIChain"
    )
    sell_template: str = Field(
        default="🔴 <b>【ENI DEX 卖出成交提醒】</b> 🔴\n\n"
                "📉 卖出金额: <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
                "🏷 成交均价: <b>${price:.4f}</b>\n"
                "👤 卖方地址: <code>{seller_short}</code>\n"
                "🔗 交易哈希: <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
                "#ENI #DEX #SellAlert"
    )
    whale_template: str = Field(
        default="🐋 <b>【ENI 巨鲸链上异动提醒】</b> 🐋\n\n"
                "🚨 监测到大额链上转账！\n"
                "💎 转移数量: <b>{amount:,.0f} {symbol}</b>\n"
                "💵 预估价值: <b>${usd_value:,.2f}</b>\n"
                "📤 发送地址: <code>{from_short}</code>\n"
                "📥 接收地址: <code>{to_short}</code>\n"
                "🔗 交易哈希: <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
                "#ENI #WhaleAlert #ENIChain"
    )
    staking_template: str = Field(
        default="💎 <b>【ENI 生态质押/流动性提醒】</b> 💎\n\n"
                "⚡ 类型: <b>{action_type}</b>\n"
                "💰 数量: <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
                "🏛 矿池/合约: <b>{pool_name}</b>\n"
                "👤 用户地址: <code>{user_short}</code>\n"
                "🔗 交易哈希: <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
                "🌟 参与牛顿原生协议，共享生态收益！\n"
                "#ENI #Staking #Newton"
    )
    summary_template: str = Field(
        default="📊 <b>【ENI Chain 链上实时数据报告】</b> 📊\n\n"
                "🌐 网络: <b>ENI Mainnet (ChainID: {chain_id})</b>\n"
                "🧱 最新区块高度: <b>#{total_blocks:,}</b>\n"
                "📈 链上交易总数: <b>{total_txs:,}</b> 笔\n"
                "👥 独立持币地址: <b>{active_addresses:,}</b> 个\n"
                "⚡ 24H 链上交易数: <b>{transactions_today:,}</b> 笔\n"
                "⛽ 平均 Gas 价格: <b>{gas_price} Gwei</b>\n"
                "⏱ 平均出块时间: <b>{block_time} 秒</b>\n\n"
                "🌐 区块浏览器查看：<a href='{explorer_url}'>scan.eniac.network</a>\n"
                "#ENI #ENIChain #BlockchainReport #Mainnet"
    )
    news_template: str = Field(
        default="🌍 <b>【区块链国际要闻快讯】</b> 🌍\n\n"
                "📰 <b>{news_title}</b>\n\n"
                "📌 核心摘要: {news_summary}\n"
                "🏛 来源机构: <b>{news_source}</b>\n"
                "⏰ 发布时间: {news_time}\n"
                "🔗 原文链接: <a href='{news_url}'>点击阅读全文</a>\n\n"
                "⚡ ENI Chain × Newton 国际前沿资讯同步\n"
                "#CryptoNews #Blockchain #Web3 #Crypto #Bitcoin"
    )

class DailyScheduleSettings(BaseModel):
    enabled: bool = Field(default=True, description="Enable automatic 3 posts per day")
    morning_time: str = Field(default="09:00", description="Morning post time (HH:MM)")
    afternoon_time: str = Field(default="14:00", description="Afternoon post time (HH:MM)")
    evening_time: str = Field(default="20:00", description="Evening post time (HH:MM)")
    auto_publish_twitter: bool = Field(default=True)
    auto_publish_telegram: bool = Field(default=True)

class AppConfig(BaseModel):
    chain: ChainSettings = Field(default_factory=ChainSettings)
    thresholds: AlertThresholds = Field(default_factory=AlertThresholds)
    telegram: TelegramSettings = Field(default_factory=TelegramSettings)
    twitter: TwitterSettings = Field(default_factory=TwitterSettings)
    templates: TemplatesSettings = Field(default_factory=TemplatesSettings)
    daily_schedule: DailyScheduleSettings = Field(default_factory=DailyScheduleSettings)
    simulation_mode: bool = Field(default=False, description="Simulate random transactions if true")
    auto_publish: bool = Field(default=True, description="Automatically publish to enabled channels")
    server_port: int = Field(default=8080)
    server_host: str = Field(default="0.0.0.0")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "platform.db")
IMAGES_DIR = os.path.join(BASE_DIR, "generated_images")
STATIC_DIR = os.path.join(BASE_DIR, "static")
