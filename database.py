import json
import re
import aiosqlite
from typing import Optional, Dict, Any, List
from config import DB_PATH, AppConfig

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS processed_txs (
                tx_hash TEXT PRIMARY KEY,
                event_type TEXT NOT NULL,
                block_number INTEGER,
                processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS posts_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_type TEXT NOT NULL,
                tx_hash TEXT,
                title TEXT NOT NULL,
                content TEXT NOT NULL,
                image_path TEXT,
                amount REAL,
                usd_value REAL,
                telegram_status TEXT DEFAULT 'pending',
                telegram_msg_id TEXT,
                telegram_error TEXT,
                twitter_status TEXT DEFAULT 'pending',
                twitter_tweet_id TEXT,
                twitter_error TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_stats (
                stat_date DATE PRIMARY KEY,
                total_events INTEGER DEFAULT 0,
                telegram_sent INTEGER DEFAULT 0,
                twitter_sent INTEGER DEFAULT 0,
                volume_usd REAL DEFAULT 0,
                whale_count INTEGER DEFAULT 0
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS daily_schedule_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_date TEXT NOT NULL,
                slot TEXT NOT NULL,
                title TEXT,
                post_id INTEGER,
                status TEXT DEFAULT 'success',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(run_date, slot)
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS topic_bindings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                topic_name TEXT NOT NULL,
                lang_code TEXT,
                thread_id INTEGER NOT NULL,
                enabled INTEGER DEFAULT 1,
                notes TEXT,
                UNIQUE(category, topic_name)
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS scheduled_tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                category TEXT NOT NULL,
                cron_expr TEXT NOT NULL,
                target_channel TEXT NOT NULL,
                target_thread_id INTEGER NOT NULL,
                target_type TEXT DEFAULT 'telegram',
                enabled INTEGER DEFAULT 1,
                last_run TEXT,
                next_run TEXT,
                description TEXT
            );
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS task_run_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                task_name TEXT NOT NULL,
                target_thread_id INTEGER,
                status TEXT NOT NULL,
                detail TEXT,
                run_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()
    await seed_default_topics_and_tasks()

async def get_app_config() -> AppConfig:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT value FROM settings WHERE key = 'app_config'")
        row = await cursor.fetchone()
        if row:
            try:
                data = json.loads(row[0])
                return AppConfig.model_validate(data)
            except Exception as e:
                print(f"[DB] Error loading config: {e}")
        # Default config
        cfg = AppConfig()
        await save_app_config(cfg)
        return cfg

async def save_app_config(config: AppConfig):
    async with aiosqlite.connect(DB_PATH) as db:
        val = json.dumps(config.model_dump(), indent=2)
        await db.execute(
            "INSERT INTO settings (key, value) VALUES ('app_config', ?) ON CONFLICT(key) DO UPDATE SET value = ?",
            (val, val)
        )
        await db.commit()

async def is_tx_processed(tx_hash: str, event_type: str) -> bool:
    key = f"{tx_hash}_{event_type}"
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT 1 FROM processed_txs WHERE tx_hash = ?", (key,))
        row = await cursor.fetchone()
        return row is not None

async def mark_tx_processed(tx_hash: str, event_type: str, block_number: int = 0):
    key = f"{tx_hash}_{event_type}"
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO processed_txs (tx_hash, event_type, block_number) VALUES (?, ?, ?)",
            (key, event_type, block_number)
        )
        await db.commit()

async def record_post_history(
    event_type: str,
    tx_hash: Optional[str],
    title: str,
    content: str,
    image_path: Optional[str] = None,
    amount: float = 0.0,
    usd_value: float = 0.0,
    telegram_status: str = "skipped",
    telegram_msg_id: Optional[str] = None,
    telegram_error: Optional[str] = None,
    twitter_status: str = "skipped",
    twitter_tweet_id: Optional[str] = None,
    twitter_error: Optional[str] = None
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO posts_history (
                event_type, tx_hash, title, content, image_path, amount, usd_value,
                telegram_status, telegram_msg_id, telegram_error,
                twitter_status, twitter_tweet_id, twitter_error
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            event_type, tx_hash, title, content, image_path, amount, usd_value,
            telegram_status, telegram_msg_id, telegram_error,
            twitter_status, twitter_tweet_id, twitter_error
        ))
        await db.commit()
        return cursor.lastrowid

async def get_recent_posts(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("""
            SELECT * FROM posts_history ORDER BY id DESC LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_platform_metrics() -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        # Total counts
        c1 = await db.execute("SELECT COUNT(*) FROM posts_history")
        total_posts = (await c1.fetchone())[0]

        c2 = await db.execute("SELECT COUNT(*) FROM posts_history WHERE telegram_status = 'success'")
        tg_success = (await c2.fetchone())[0]

        c3 = await db.execute("SELECT COUNT(*) FROM posts_history WHERE twitter_status = 'success'")
        tw_success = (await c3.fetchone())[0]

        c4 = await db.execute("SELECT COUNT(*) FROM posts_history WHERE event_type = 'whale'")
        whale_count = (await c4.fetchone())[0]

        c5 = await db.execute("SELECT COALESCE(SUM(usd_value), 0) FROM posts_history")
        total_volume = (await c5.fetchone())[0]

        return {
            "total_posts": total_posts,
            "telegram_success": tg_success,
            "twitter_success": tw_success,
            "whale_count": whale_count,
            "total_volume_usd": total_volume
        }

async def record_daily_slot_run(run_date: str, slot: str, title: str, post_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO daily_schedule_runs (run_date, slot, title, post_id)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(run_date, slot) DO UPDATE SET title = ?, post_id = ?, created_at = CURRENT_TIMESTAMP
        """, (run_date, slot, title, post_id, title, post_id))
        await db.commit()

async def get_today_slot_runs(run_date: str) -> Dict[str, Any]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM daily_schedule_runs WHERE run_date = ?", (run_date,))
        rows = await cursor.fetchall()
        result = {}
        for r in rows:
            result[r["slot"]] = dict(r)
        return result

# --- Topic Bindings & Task Scheduler Helpers ---

DEFAULT_TOPIC_BINDINGS = [
    # 11国语言国家频道
    ("11国语言国家频道", "🇬🇧 English", "en", 33, "英国/欧美英语官方讨论板块"),
    ("11国语言国家频道", "🇨🇳 简体中文", "zh", 34, "华语及大中华区官方讨论板块"),
    ("11国语言国家频道", "🇰🇷 한국어", "ko", 35, "韩国官方讨论板块"),
    ("11国语言国家频道", "🇯🇵 日本語", "ja", 36, "日本官方讨论板块"),
    ("11国语言国家频道", "🇻🇳 Tiếng Việt", "vi", 37, "越南官方讨论板块"),
    ("11国语言国家频道", "🇹🇭 ภาษาไทย", "th", 38, "泰国官方讨论板块"),
    ("11国语言国家频道", "🇮🇩 Bahasa Indonesia", "id", 39, "印度尼西亚官方讨论板块"),
    ("11国语言国家频道", "🇲🇾 Bahasa Melayu", "ms", 40, "马来西亚官方讨论板块"),
    ("11国语言国家频道", "🇪🇸 Español", "es", 41, "西班牙语官方讨论板块"),
    ("11国语言国家频道", "🇧🇷 Português", "pt", 42, "葡萄牙语/巴西官方讨论板块"),
    ("11国语言国家频道", "🇸🇦 العربية", "ar", 43, "阿拉伯语/中东官方讨论板块"),
    # 核心投研与生态
    ("核心投研与生态", "🤖 ENI AI", "all", 5, "ENI AI 投研中心与深度分析"),
    ("核心投研与生态", "🪙 GOLD MARKET", "all", 7, "黄金与宏观市场观察"),
    ("核心投研与生态", "📈 GLOBAL MARKETS", "all", 8, "全球股指与金融市场行情"),
    ("核心投研与生态", "🛠️ DEV & TECH", "all", 9, "开发技术与协议升级"),
    ("核心投研与生态", "🧠 AI AGENT & RWA", "all", 10, "智能体架构与真实世界资产"),
    ("核心投研与生态", "🐳 WHALE ALERTS", "all", 11, "链上大额异动监控"),
    # 社区综合板块
    ("社区综合板块", "💬 GENERAL CHAT", "all", 1, "全社区综合交流大厅"),
    ("社区综合板块", "📢 ANNOUNCEMENTS", "all", 2, "官方重大公告"),
    ("社区综合板块", "❓ FAQ & HELP", "all", 3, "新手指南与答疑"),
    ("社区综合板块", "🤝 ECOSYSTEM PARTNERS", "all", 12, "生态合作与战略盟友"),
    ("社区综合板块", "🏛️ GOVERNANCE & DAO", "all", 13, "社区治理与提案投票"),
    ("社区综合板块", "💹 PRICE DISCUSSION", "all", 14, "价格分析与交易心得"),
    ("社区综合板块", "🎁 AIRDROP & REWARDS", "all", 15, "激励计划与空投任务"),
    ("社区综合板块", "🎨 MEME & CREATIVE", "all", 16, "社区梗图与二创设计"),
    ("社区综合板块", "⚡ VALIDATORS & STAKING", "all", 17, "节点运营与质押收益"),
    ("社区综合板块", "🛡️ SECURITY & AUDIT", "all", 18, "代码安全与合约审计"),
    ("社区综合板块", "🎙️ EVENTS & AMA", "all", 19, "线上直播与社区AMA"),
    ("社区综合板块", "💡 SUGGESTIONS & FEEDBACK", "all", 20, "意见征集与功能反馈")
]

DEFAULT_SCHEDULED_TASKS = [
    {
        "id": "hourly_research",
        "name": "每小时投研分析",
        "category": "AI投研",
        "cron_expr": "0 * * * *",
        "target_channel": "🤖 ENI AI",
        "target_thread_id": 5,
        "target_type": "telegram",
        "enabled": 1,
        "description": "定时向 ENI AI 话题推送每小时精选技术与生态分析研报"
    },
    {
        "id": "gold_market",
        "name": "黄金与宏观市场观察",
        "category": "宏观数据",
        "cron_expr": "0 * * * *",
        "target_channel": "🪙 GOLD MARKET",
        "target_thread_id": 7,
        "target_type": "telegram",
        "enabled": 1,
        "description": "监控国际现货黄金、美元指数与宏观流动性对Web3的影响"
    },
    {
        "id": "global_markets",
        "name": "全球主要股指与流动性跟踪",
        "category": "宏观数据",
        "cron_expr": "0 * * * *",
        "target_channel": "📈 GLOBAL MARKETS",
        "target_thread_id": 8,
        "target_type": "telegram",
        "enabled": 1,
        "description": "纳斯达克、标普500、日经指数与加密资产相关性综述"
    },
    {
        "id": "morning_pulse",
        "name": "ENI 每日生态晨报",
        "category": "每日晨报",
        "cron_expr": "0 9 * * *",
        "target_channel": "🤖 ENI AI",
        "target_thread_id": 5,
        "target_type": "both",
        "enabled": 1,
        "description": "每日上午 09:00 全自动生成 ENI 链上数据与生态速递"
    },
    {
        "id": "arch_intel",
        "name": "核心架构技术情报解读",
        "category": "技术专栏",
        "cron_expr": "30 16 * * *",
        "target_channel": "🤖 ENI AI",
        "target_thread_id": 5,
        "target_type": "telegram",
        "enabled": 1,
        "description": "并行EVM引擎、模块化共识与高吞吐网络深度解构"
    },
    {
        "id": "general_broadcast",
        "name": "社区全员生态通用广播",
        "category": "社区广播",
        "cron_expr": "0 11 * * *",
        "target_channel": "💬 GENERAL CHAT",
        "target_thread_id": 1,
        "target_type": "telegram",
        "enabled": 1,
        "description": "全社区主话题群发生态发展要闻与社区活跃指南"
    },
    {
        "id": "whale_evening",
        "name": "晚间大额巨鲸异动汇总",
        "category": "异动预警",
        "cron_expr": "0 20 * * *",
        "target_channel": "🤖 ENI AI",
        "target_thread_id": 5,
        "target_type": "both",
        "enabled": 1,
        "description": "晚间 20:00 汇总过去 24 小时链上大单转账与异动地址"
    }
]

async def seed_default_topics_and_tasks():
    async with aiosqlite.connect(DB_PATH) as db:
        # Check topic bindings
        cursor = await db.execute("SELECT COUNT(*) FROM topic_bindings")
        count = (await cursor.fetchone())[0]
        if count == 0:
            for cat, name, lang, tid, notes in DEFAULT_TOPIC_BINDINGS:
                await db.execute("""
                    INSERT OR IGNORE INTO topic_bindings (category, topic_name, lang_code, thread_id, notes)
                    VALUES (?, ?, ?, ?, ?)
                """, (cat, name, lang, tid, notes))
            await db.commit()

        # Check scheduled tasks
        cursor = await db.execute("SELECT COUNT(*) FROM scheduled_tasks")
        count_tasks = (await cursor.fetchone())[0]
        if count_tasks == 0:
            for t in DEFAULT_SCHEDULED_TASKS:
                await db.execute("""
                    INSERT OR IGNORE INTO scheduled_tasks (id, name, category, cron_expr, target_channel, target_thread_id, target_type, enabled, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (t["id"], t["name"], t["category"], t["cron_expr"], t["target_channel"], t["target_thread_id"], t["target_type"], t["enabled"], t["description"]))
            await db.commit()

async def get_all_topic_bindings() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM topic_bindings ORDER BY id ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def update_topic_binding(topic_id: int, thread_id: int, enabled: int = 1, topic_name: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if topic_name:
            await db.execute("UPDATE topic_bindings SET thread_id = ?, enabled = ?, topic_name = ? WHERE id = ?", (thread_id, enabled, topic_name, topic_id))
        else:
            await db.execute("UPDATE topic_bindings SET thread_id = ?, enabled = ? WHERE id = ?", (thread_id, enabled, topic_id))
        await db.commit()

async def add_custom_topic(category: str, topic_name: str, thread_id: int, notes: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO topic_bindings (category, topic_name, lang_code, thread_id, enabled, notes)
            VALUES (?, ?, 'custom', ?, 1, ?)
        """, (category, topic_name, thread_id, notes))
        await db.commit()

async def import_or_sync_detected_topics(detected_topics: List[Dict[str, Any]]) -> Dict[str, int]:
    """
    自动将 Telegram getUpdates 侦测到的话题同步到数据库:
    1. 若已有同名或包含关键词的话题，更新其 thread_id 与 enabled=1
    2. 若已有该 thread_id 的话题，更新其话题名称
    3. 若完全不存在，新建对应群组话题
    """
    updated_count = 0
    created_count = 0

    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM topic_bindings")
        existing = [dict(r) for r in await cursor.fetchall()]

        for item in detected_topics:
            try:
                tid = int(item.get("thread_id", 0))
            except (ValueError, TypeError):
                continue
            if tid <= 0:
                continue

            name = (item.get("topic_name") or f"话题 #{tid}").strip()
            chat_title = item.get("chat_title") or "Telegram群"

            # 匹配 1: thread_id 相同
            matched_by_tid = next((t for t in existing if t["thread_id"] == tid), None)
            if matched_by_tid:
                new_name = name if not name.startswith("话题 #") else matched_by_tid["topic_name"]
                await db.execute(
                    "UPDATE topic_bindings SET topic_name = ?, enabled = 1 WHERE id = ?",
                    (new_name, matched_by_tid["id"])
                )
                updated_count += 1
                continue

            # 匹配 2: 名称相同或部分匹配
            clean_name = re.sub(r'[^\w\s]', '', name).strip().lower()
            matched_by_name = None
            if clean_name and len(clean_name) >= 3:
                for t in existing:
                    t_clean = re.sub(r'[^\w\s]', '', t["topic_name"]).strip().lower()
                    if clean_name in t_clean or t_clean in clean_name:
                        matched_by_name = t
                        break

            if matched_by_name:
                await db.execute(
                    "UPDATE topic_bindings SET thread_id = ?, enabled = 1 WHERE id = ?",
                    (tid, matched_by_name["id"])
                )
                updated_count += 1
                continue

            # 匹配 3: 新增话题
            await db.execute("""
                INSERT INTO topic_bindings (category, topic_name, lang_code, thread_id, enabled, notes)
                VALUES (?, ?, 'custom', ?, 1, ?)
            """, (f"{chat_title}", name, tid, f"从 Telegram 自动识别导入 (ID: {tid})"))
            created_count += 1

        await db.commit()

    return {"updated": updated_count, "created": created_count}

async def get_all_scheduled_tasks() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM scheduled_tasks ORDER BY id ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def update_scheduled_task(task_id: str, enabled: int, cron_expr: Optional[str] = None):
    async with aiosqlite.connect(DB_PATH) as db:
        if cron_expr:
            await db.execute("UPDATE scheduled_tasks SET enabled = ?, cron_expr = ? WHERE id = ?", (enabled, cron_expr, task_id))
        else:
            await db.execute("UPDATE scheduled_tasks SET enabled = ? WHERE id = ?", (enabled, task_id))
        await db.commit()

async def log_task_run(task_id: str, task_name: str, target_thread_id: int, status: str, detail: str = ""):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            INSERT INTO task_run_logs (task_id, task_name, target_thread_id, status, detail)
            VALUES (?, ?, ?, ?, ?)
        """, (task_id, task_name, target_thread_id, status, detail))
        await db.execute("""
            UPDATE scheduled_tasks SET last_run = CURRENT_TIMESTAMP WHERE id = ?
        """, (task_id,))
        await db.commit()

async def get_recent_task_logs(limit: int = 20) -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM task_run_logs ORDER BY id DESC LIMIT ?", (limit,))
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

