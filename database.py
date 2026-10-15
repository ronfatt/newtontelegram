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
        await db.execute("""
            CREATE TABLE IF NOT EXISTS multi_day_campaigns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                day_number INTEGER DEFAULT 1,
                campaign_title TEXT NOT NULL,
                scheduled_time TEXT NOT NULL,
                poster_image TEXT,
                text_zh TEXT,
                text_en TEXT,
                text_ko TEXT,
                text_vi TEXT,
                status TEXT DEFAULT 'pending',
                sent_at TIMESTAMP,
                send_results TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        await db.commit()
    await seed_default_topics_and_tasks()
    await seed_default_campaigns()

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

# ==========================================
# Multi-Day Campaigns (4 National Chats Matrix)
# ==========================================

DEFAULT_CAMPAIGNS = [
    {
        "day_number": 1,
        "campaign_title": "Day 1：牛顿协议倡议与宏大愿景",
        "scheduled_time": "10:00",
        "poster_image": "/static/uploads/posters/1.png",
        "text_zh": "⚛️ <b>【牛顿协议系列推介 · 第 1 期：牛顿倡议与宏大愿景】</b>\n\n牛顿协议（Newton Protocol）致力于构建连接现实世界价值与下一代智能数字经济的基础设施。\n\n🌟 <b>核心使命与愿景：</b>\n• 打破传统区块链技术孤岛，实现千万级高频商业交互\n• 基于 ENI Chain 并行 EVM 底层架构，实现毫秒级亚秒敲定\n• 构建公平、透明、去中心化的全球协作生态网络\n\n🌐 官方区块浏览器：https://scan.eniac.network\n#NewtonProtocol #ENIChain #Web3 #Decentralized",
        "text_en": "⚛️ <b>【Newton Protocol Showcase · Day 1: The Newton Initiative & Grand Vision】</b>\n\nNewton Protocol is architected to bridge real-world value with next-generation autonomous digital economies.\n\n🌟 <b>Core Mission & Key Pillars:</b>\n• Breaking blockchain silos for enterprise-scale high-frequency utility\n• Powered by ENI Chain Parallel EVM with sub-second finality\n• Creating a transparent, trustless and decentralized global ecosystem\n\n🌐 Live Explorer: https://scan.eniac.network\n#NewtonProtocol #ENIChain #Web3 #Decentralized",
        "text_ko": "⚛️ <b>【뉴턴 프로토콜 쇼케이스 · 1일차: 뉴턴 이니셔티브와 비전】</b>\n\n뉴턴 프로토콜(Newton Protocol)은 실물 자산 가치와 차세대 디지털 경제를 잇는 글로벌 인프라입니다.\n\n🌟 <b>핵심 미션과 비전:</b>\n• 기업급 고주파수 유틸리티 지원\n• ENI Chain 병렬 EVM 기반 1초 미만 트랜잭션 확정성\n• 투명하고 탈중앙화된 글로벌 협력 생태계 구축\n\n🌐 공식 익스플로러: https://scan.eniac.network\n#NewtonProtocol #ENIChain #Web3 #Crypto",
        "text_vi": "⚛️ <b>【Newton Protocol Showcase · Ngày 1: Sứ mệnh & Tầm nhìn Newton】</b>\n\nNewton Protocol được thiết kế để kết nối giá trị thực tế với nền kinh tế kỹ thuật số thế hệ mới.\n\n🌟 <b>Sứ mệnh & Trụ cột cốt lõi:</b>\n• Phá bỏ rào cản công nghệ, hỗ trợ hàng triệu giao dịch quy mô doanh nghiệp\n• Vận hành trên ENI Chain với Parallel EVM, tốc độ xác nhận dưới 1 giây\n• Xây dựng hệ sinh thái phi tập trung minh bạch và toàn cầu\n\n🌐 Khám phá Explorer: https://scan.eniac.network\n#NewtonProtocol #ENIChain #Web3 #Blockchain"
    },
    {
        "day_number": 2,
        "campaign_title": "Day 2：并行 EVM 与企业级模块化公链",
        "scheduled_time": "14:30",
        "poster_image": "/static/uploads/posters/2.png",
        "text_zh": "⚡ <b>【牛顿协议系列推介 · 第 2 期：并行 EVM 与模块化公链】</b>\n\n告别网络拥堵与高额 Gas！ENI Chain 并行执行引擎带来极致性能革命。\n\n🚀 <b>技术创新点：</b>\n• 并行执行：互不干扰的交易并发撮合处理\n• 模块化结构：Mainnet 主网底层 + Hub 跨链枢纽 + AppChains 定制链\n• 企业级高吞吐：稳定支持千万级日交易量\n\n🔗 官网探索：https://eniac.network\n#ENIChain #ParallelEVM #ModularL1 #Newton",
        "text_en": "⚡ <b>【Newton Protocol Showcase · Day 2: Parallel EVM & Modular Architecture】</b>\n\nSay goodbye to network congestion and volatile gas spikes! The ENI Chain parallel engine brings a performance breakthrough.\n\n🚀 <b>Technical Innovations:</b>\n• Parallel Execution: Independent state transactions processed concurrently\n• Modular Topography: Mainnet settlement + Interoperable Hub + Custom AppChains\n• Enterprise Throughput: Engineered for millions of daily active operations\n\n🔗 Explore Official Portal: https://eniac.network\n#ENIChain #ParallelEVM #ModularL1 #Newton",
        "text_ko": "⚡ <b>【뉴턴 프로토콜 쇼케이스 · 2일차: 병렬 EVM과 모듈러 아키텍처】</b>\n\n네트워크 혼잡과 가스비 폭등에서 벗어나십시오! ENI Chain의 병렬 엔진이 성능의 혁신을 이끕니다.\n\n🚀 <b>기술적 혁신 요소:</b>\n• 병렬 실행(Parallel Execution): 상호 충돌 없는 트랜잭션 동시 처리\n• 모듈러 토폴로지: Mainnet + Hub + 맞춤형 AppChains\n• 기업급 고처리량: 매일 수백만 건의 대규모 거래 완벽 지원\n\n🔗 공식 포털: https://eniac.network\n#ENIChain #ParallelEVM #ModularL1 #Newton",
        "text_vi": "⚡ <b>【Newton Protocol Showcase · Ngày 2: Parallel EVM & Kiến trúc Modular】</b>\n\nKhông còn tắc nghẽn mạng hay phí gas biến động! Động cơ thực thi song song của ENI Chain mang lại bước đột phá công nghệ.\n\n🚀 <b>Điểm sáng công nghệ:</b>\n• Thực thi song song: Xử lý đồng thời các giao dịch độc lập\n• Cấu trúc Modular: Mainnet + Hub liên chuỗi + AppChains riêng biệt\n• Thông lượng chuẩn doanh nghiệp: Đáp ứng hàng triệu giao dịch mỗi ngày\n\n🔗 Khám phá ngay: https://eniac.network\n#ENIChain #ParallelEVM #ModularL1 #Newton"
    },
    {
        "day_number": 3,
        "campaign_title": "Day 3：原生质押、节点治理与生态激励",
        "scheduled_time": "18:00",
        "poster_image": "/static/uploads/posters/3.png",
        "text_zh": "💎 <b>【牛顿协议系列推介 · 第 3 期：原生质押与节点治理】</b>\n\n深度参与牛顿生态建设，共享去中心化网络繁荣与通缩收益红利！\n\n🌟 <b>治理与激励权益：</b>\n• 原生通胀通缩对冲机制与节点验证质押分红\n• 社区 DAO 提案治理，每一个持币者皆为主体\n• DEX 流动性激励池助力资产高灵活性收益\n\n📊 实时浏览器：https://scan.eniac.network\n#NewtonProtocol #Staking #Governance #CryptoRewards",
        "text_en": "💎 <b>【Newton Protocol Showcase · Day 3: Staking, Governance & Ecosystem Rewards】</b>\n\nParticipate deeply in the Newton ecosystem to share in network growth and deflationary yield dividends!\n\n🌟 <b>Governance & Staking Benefits:</b>\n• Native validator staking yields and deflationary value accrual\n• Community DAO governance giving every token holder a voice\n• DEX liquidity pools for optimized flexibility and yield capture\n\n📊 Verify On-Chain: https://scan.eniac.network\n#NewtonProtocol #Staking #Governance #CryptoRewards",
        "text_ko": "💎 <b>【뉴턴 프로토콜 쇼케이스 · 3일차: 스테이킹, 거버넌스 및 보상】</b>\n\n뉴턴 생태계 구축에 참여하여 네트워크 성장과 디플레이션 수익 혜택을 함께 누리십시오!\n\n🌟 <b>거버넌스 및 스테이킹 혜택:</b>\n• 밸리데이터 스테이킹 보상 및 가치 축적 메커니즘\n• 모든 홀더에게 발언권을 부여하는 탈중앙화 DAO 거버넌스\n• 자산 유동성과 수익률을 최적화하는 DEX 유동성 풀\n\n📊 온체인 데이터 확인: https://scan.eniac.network\n#NewtonProtocol #Staking #Governance #CryptoRewards",
        "text_vi": "💎 <b>【Newton Protocol Showcase · Ngày 3: Staking, Quản trị & Phần thưởng hệ sinh thái】</b>\n\nTham gia sâu vào hệ sinh thái Newton để cùng chia sẻ sự phát triển của mạng lưới và lợi ích giảm phát!\n\n🌟 <b>Quyền lợi Staking & Quản trị:</b>\n• Lợi suất staking xác thực và cơ chế tích lũy giá trị bền vững\n• Quản trị cộng đồng DAO trao quyền biểu quyết cho từng thành viên\n• Các bể thanh khoản DEX tối ưu tính linh hoạt và thu nhập\n\n📊 Kiểm tra trực tiếp trên Explorer: https://scan.eniac.network\n#NewtonProtocol #Staking #Governance #CryptoRewards"
    }
]

async def seed_default_campaigns():
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT COUNT(*) FROM multi_day_campaigns")
        count = (await cursor.fetchone())[0]
        if count == 0:
            for c in DEFAULT_CAMPAIGNS:
                await db.execute("""
                    INSERT INTO multi_day_campaigns (
                        day_number, campaign_title, scheduled_time, poster_image,
                        text_zh, text_en, text_ko, text_vi, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (
                    c["day_number"], c["campaign_title"], c["scheduled_time"], c["poster_image"],
                    c["text_zh"], c["text_en"], c["text_ko"], c["text_vi"]
                ))
            await db.commit()

async def get_all_campaigns() -> List[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM multi_day_campaigns ORDER BY day_number ASC, id ASC")
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

async def get_campaign_by_id(cid: int) -> Optional[Dict[str, Any]]:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute("SELECT * FROM multi_day_campaigns WHERE id = ?", (cid,))
        row = await cursor.fetchone()
        return dict(row) if row else None

async def add_campaign(
    day_number: int,
    campaign_title: str,
    scheduled_time: str,
    poster_image: str,
    text_zh: str,
    text_en: str,
    text_ko: str,
    text_vi: str
) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO multi_day_campaigns (
                day_number, campaign_title, scheduled_time, poster_image,
                text_zh, text_en, text_ko, text_vi, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (day_number, campaign_title, scheduled_time, poster_image, text_zh, text_en, text_ko, text_vi))
        await db.commit()
        return cursor.lastrowid

async def update_campaign(
    cid: int,
    day_number: int,
    campaign_title: str,
    scheduled_time: str,
    poster_image: str,
    text_zh: str,
    text_en: str,
    text_ko: str,
    text_vi: str,
    status: str = "pending"
):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE multi_day_campaigns SET
                day_number = ?, campaign_title = ?, scheduled_time = ?, poster_image = ?,
                text_zh = ?, text_en = ?, text_ko = ?, text_vi = ?, status = ?
            WHERE id = ?
        """, (day_number, campaign_title, scheduled_time, poster_image, text_zh, text_en, text_ko, text_vi, status, cid))
        await db.commit()

async def delete_campaign(cid: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM multi_day_campaigns WHERE id = ?", (cid,))
        await db.commit()

async def mark_campaign_sent(cid: int, results_json: str):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            UPDATE multi_day_campaigns SET
                status = 'sent', sent_at = CURRENT_TIMESTAMP, send_results = ?
            WHERE id = ?
        """, (results_json, cid))
        await db.commit()

