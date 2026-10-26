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
    enabled: bool = Field(default=True)
    bot_token: str = Field(default_factory=lambda: os.environ.get("TELEGRAM_BOT_TOKEN", "8839374237:AAEFdFgmF07h-M9PBwr5bXALibAo3-CRGGY"), description="Telegram Bot API Token (from @BotFather)")
    chat_id: str = Field(default_factory=lambda: os.environ.get("TELEGRAM_CHAT_ID", "-1004381922114"), description="Target Chat ID or Channel (@channel_name or -100xxx)")
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
        default="🟢 <b>【ENI DEX Large Buy Alert】</b> 🟢\n\n"
                "💰 <b>Buy Amount:</b> <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
                "🏷 <b>Execution Price:</b> <b>${price:.4f}</b>\n"
                "👤 <b>Buyer Address:</b> <code>{buyer_short}</code>\n"
                "🔗 <b>Tx Hash:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
                "🚀 <i>High-frequency trading activity on ENI Chain. Newton Protocol ecosystem is expanding!</i>\n"
                "#ENI #DEX #BuyAlert #ENIChain #Web3"
    )
    sell_template: str = Field(
        default="🔴 <b>【ENI DEX Sell Alert】</b> 🔴\n\n"
                "📉 <b>Sell Amount:</b> <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
                "🏷 <b>Execution Price:</b> <b>${price:.4f}</b>\n"
                "👤 <b>Seller Address:</b> <code>{seller_short}</code>\n"
                "🔗 <b>Tx Hash:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
                "⚡ <i>Real-time liquidity and automated AMM tracking on ENI Chain</i>\n"
                "#ENI #DEX #SellAlert #ENIChain"
    )
    whale_template: str = Field(
        default="🐋 <b>【ENI Chain Whale Movement Alert】</b> 🐋\n\n"
                "🚨 <b>Large On-Chain Transfer Detected!</b>\n"
                "💎 <b>Transfer Amount:</b> <b>{amount:,.0f} {symbol}</b>\n"
                "💵 <b>Estimated Value:</b> <b>${usd_value:,.2f}</b>\n"
                "📤 <b>From:</b> <code>{from_short}</code>\n"
                "📥 <b>To:</b> <code>{to_short}</code>\n"
                "🔗 <b>Tx Hash:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
                "🌐 <i>Monitoring on-chain liquidity shifts & major token distribution</i>\n"
                "#ENI #WhaleAlert #Crypto #Blockchain #ENIChain"
    )
    staking_template: str = Field(
        default="💎 <b>【ENI Staking & Liquidity Alert】</b> 💎\n\n"
                "⚡ <b>Action:</b> {action_type}\n"
                "💰 <b>Amount:</b> <b>{amount:,.0f} {symbol}</b> (${usd_value:,.2f})\n"
                "🏛 <b>Pool / Contract:</b> <b>{pool_name}</b>\n"
                "👤 <b>User Address:</b> <code>{user_short}</code>\n"
                "🔗 <b>Tx Hash:</b> <a href='{explorer_url}/tx/{tx_hash}'>{tx_hash_short}</a>\n\n"
                "🌟 <i>Strengthening decentralized consensus & earning staking yield with Newton Protocol!</i>\n"
                "#ENI #Staking #Newton #DeFi"
    )
    summary_template: str = Field(
        default="📊 <b>【ENI Chain Real-Time Network Report】</b> 📊\n\n"
                "🌐 <b>Network:</b> <b>ENI Mainnet (ChainID: {chain_id})</b>\n"
                "🧱 <b>Block Height:</b> <b>#{total_blocks:,}</b>\n"
                "📈 <b>Total Transactions:</b> <b>{total_txs:,}</b>\n"
                "👥 <b>Unique Addresses:</b> <b>{active_addresses:,}</b>\n"
                "⚡ <b>24H Transactions:</b> <b>{transactions_today:,}</b>\n"
                "⛽ <b>Average Gas:</b> <b>{gas_price} Gwei</b>\n"
                "⏱ <b>Block Time:</b> <b>{block_time}s</b>\n\n"
                "🌐 <b>Blockscout Explorer:</b> <a href='{explorer_url}'>scan.eniac.network</a>\n"
                "#ENI #ENIChain #BlockchainReport #Mainnet"
    )
    news_template: str = Field(
        default="🌍 <b>【Global Crypto Breaking News】</b> 🌍\n\n"
                "📰 <b>{news_title}</b>\n\n"
                "📌 <b>Summary:</b> {news_summary}\n"
                "🏛 <b>Source:</b> <b>{news_source}</b>\n"
                "⏰ <b>Published:</b> {news_time}\n"
                "🔗 <b>Original Article:</b> <a href='{news_url}'>Read Full Story</a>\n\n"
                "⚡ <i>ENI Chain × Newton Protocol Intelligence Feed</i>\n"
                "#CryptoNews #Blockchain #Web3 #Crypto #Bitcoin #ENIChain"
    )

class DailyScheduleSettings(BaseModel):
    enabled: bool = Field(default=True, description="Enable automatic 2 posts per day to #General")
    posts_per_day: int = Field(default=2, description="Daily posts count (default: 2)")
    morning_time: str = Field(default="10:00", description="Morning post time (HH:MM)")
    afternoon_time: str = Field(default="", description="Afternoon post time (optional)")
    evening_time: str = Field(default="20:00", description="Evening post time (HH:MM)")
    auto_publish_twitter: bool = Field(default=False)
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

def _is_serverless_env() -> bool:
    for k in ("VERCEL", "VERCEL_ENV", "VERCEL_REGION", "AWS_LAMBDA_FUNCTION_NAME", "LAMBDA_TASK_ROOT"):
        if os.environ.get(k):
            return True
    try:
        test_file = os.path.join(BASE_DIR, f".write_test_{os.getpid()}")
        with open(test_file, "w") as f:
            f.write("1")
        os.remove(test_file)
        return False
    except Exception:
        return True

IS_VERCEL = _is_serverless_env()

if IS_VERCEL:
    DB_PATH = "/tmp/platform.db"
    IMAGES_DIR = "/tmp/generated_images"
    STATIC_DIR = os.path.join(BASE_DIR, "static")
    PUBLIC_DIR = os.path.join(BASE_DIR, "public")
else:
    DB_PATH = os.path.join(BASE_DIR, "platform.db")
    IMAGES_DIR = os.path.join(BASE_DIR, "generated_images")
    STATIC_DIR = os.path.join(BASE_DIR, "static")
    PUBLIC_DIR = os.path.join(BASE_DIR, "public")
