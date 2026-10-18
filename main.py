import os
import json
import asyncio
from typing import Dict, Any, Optional, List
from fastapi import FastAPI, HTTPException, Request, Response, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from config import AppConfig, IMAGES_DIR, STATIC_DIR, IS_VERCEL
from database import (
    init_db, get_app_config, save_app_config,
    get_recent_posts, get_platform_metrics,
    get_all_topic_bindings, update_topic_binding,
    get_all_scheduled_tasks, update_scheduled_task,
    get_recent_task_logs, record_post_history
)
from eni_watcher import eni_watcher
from services.alert_engine import alert_engine
from services.simulator import ENISimulator
from services.eni_live_tracker import eni_live_tracker
from services.global_news_tracker import global_news_tracker
from services.daily_scheduler import daily_scheduler
from services.topic_manager import topic_manager
from services.research_desk import research_desk
from services.scheduled_tasks_manager import scheduled_tasks_manager
from services.translator import translate_to_all_languages, SUPPORTED_LANGUAGES
from publishers.telegram_bot import TelegramPublisher
from publishers.twitter_client import TwitterPublisher
from image_generator import generate_banner_image

app = FastAPI(title="Newton Protocol × ENI Chain Automation Operations Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# SSE subscriber queue
sse_subscribers = []

async def on_new_event(event_data: Dict[str, Any]):
    msg = f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"
    for q in list(sse_subscribers):
        try:
            await q.put(msg)
        except Exception:
            pass

@app.on_event("startup")
async def startup_event():
    await init_db()
    alert_engine.subscribe(on_new_event)
    if not IS_VERCEL:
        eni_watcher.start()
        daily_scheduler.start()
        scheduled_tasks_manager.start()
        print("[Platform] Super Console initialized: Background loops running.")
    else:
        print("[Platform] Running in Serverless mode (Vercel): Background loops disabled, triggers active.")

@app.on_event("shutdown")
def shutdown_event():
    if not IS_VERCEL:
        scheduled_tasks_manager.stop()
        daily_scheduler.stop()
        eni_watcher.stop()
    alert_engine.unsubscribe(on_new_event)

@app.get("/api/status")
async def get_status():
    config = await get_app_config()
    metrics = await get_platform_metrics()
    watcher_stat = eni_watcher.get_status()

    tg_connected = False
    tg_info = None
    if config.telegram.bot_token:
        chk = await TelegramPublisher.test_connection(config.telegram.bot_token)
        tg_connected = chk.get("success", False)
        tg_info = chk

    tw_connected = False
    tw_info = None
    if config.twitter.api_key and config.twitter.access_token:
        chk = TwitterPublisher.test_connection(
            config.twitter.api_key,
            config.twitter.api_secret,
            config.twitter.access_token,
            config.twitter.access_token_secret
        )
        tw_connected = chk.get("success", False)
        tw_info = chk

    return {
        "status": "online",
        "watcher": watcher_stat,
        "metrics": metrics,
        "channels": {
            "telegram": {
                "enabled": config.telegram.enabled,
                "connected": tg_connected,
                "info": tg_info
            },
            "twitter": {
                "enabled": config.twitter.enabled,
                "connected": tw_connected,
                "info": tw_info
            }
        },
        "simulation_mode": config.simulation_mode,
        "auto_publish": config.auto_publish
    }

@app.get("/api/config")
async def get_config_endpoint():
    config = await get_app_config()
    return config.model_dump()

@app.post("/api/config")
async def save_config_endpoint(new_config: AppConfig):
    await save_app_config(new_config)
    return {"success": True, "message": "配置已保存成功"}

@app.get("/api/posts")
async def get_posts_endpoint(limit: int = 50, offset: int = 0):
    posts = await get_recent_posts(limit=limit, offset=offset)
    return {"posts": posts}

@app.get("/api/eni/live")
async def get_eni_live_endpoint():
    """Fetches real-time stats and transactions directly from scan.eniac.network"""
    stats = await eni_live_tracker.get_live_stats()
    txs = await eni_live_tracker.get_live_transactions(limit=10)
    return {
        "stats": stats,
        "transactions": txs
    }

@app.get("/api/news")
async def get_news_endpoint():
    """Fetches latest international blockchain breaking news"""
    news = await global_news_tracker.get_latest_news(limit=12)
    return {"news": news}

class BroadcastNewsRequest(BaseModel):
    news_id: Optional[str] = None
    news_title: Optional[str] = None
    news_url: Optional[str] = None
    news_summary: Optional[str] = None
    news_source: Optional[str] = None

@app.post("/api/action/broadcast-news")
async def broadcast_news_endpoint(req: BroadcastNewsRequest):
    """Fetches a breaking international news item and publishes it to TG and Twitter"""
    config = await get_app_config()
    if req.news_title:
        item = {
            "news_id": req.news_id or "custom_news",
            "news_title": req.news_title,
            "news_url": req.news_url or "https://cointelegraph.com",
            "news_summary": req.news_summary or "",
            "news_source": req.news_source or "Global Intel",
            "news_time": "Real-time"
        }
    else:
        news_list = await global_news_tracker.get_latest_news(limit=5)
        if not news_list:
            raise HTTPException(status_code=500, detail="暂未抓取到国际新闻，请稍后重试")
        item = news_list[0]

    event = {
        "event_type": "news",
        "news_id": item.get("news_id", ""),
        "news_title": item.get("news_title", ""),
        "news_url": item.get("news_url", ""),
        "news_summary": item.get("news_summary", ""),
        "news_time": item.get("news_time", ""),
        "news_source": item.get("news_source", "")
    }
    result = await alert_engine.process_event(event, config)
    return {"success": True, "event": result}

@app.post("/api/action/broadcast-eni-summary")
async def broadcast_eni_summary_endpoint():
    """Builds and publishes an authentic live summary from scan.eniac.network"""
    config = await get_app_config()
    summary_event = await eni_live_tracker.build_live_summary_event(config)
    result = await alert_engine.process_event(summary_event, config)
    return {"success": True, "event": result}

@app.get("/api/daily-schedule/status")
async def get_daily_schedule_status():
    status = await daily_scheduler.get_daily_status()
    return status

class TriggerScheduleRequest(BaseModel):
    slot: str = "morning"

@app.post("/api/daily-schedule/trigger")
async def trigger_daily_schedule_endpoint(req: TriggerScheduleRequest):
    try:
        res = await daily_scheduler.trigger_slot(req.slot, force=True)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SimulateRequest(BaseModel):
    event_type: str = "whale"
    amount: Optional[float] = None

@app.post("/api/action/simulate")
async def simulate_event_endpoint(req: SimulateRequest):
    config = await get_app_config()
    event_data = ENISimulator.simulate_event(req.event_type, req.amount)
    result = await alert_engine.process_event(event_data, config)
    return {"success": True, "event": result}

class TestTelegramRequest(BaseModel):
    chat_id: Optional[str] = None
    thread_id: Optional[str] = None
    text: Optional[str] = None

@app.post("/api/action/test-telegram")
async def test_telegram_endpoint(req: Optional[TestTelegramRequest] = None):
    config = await get_app_config()
    target_chat_id = (req.chat_id if req and req.chat_id else config.telegram.chat_id) or ""
    if not config.telegram.bot_token or not target_chat_id:
        raise HTTPException(status_code=400, detail="Telegram Bot Token 或 Chat ID 未设置")

    thread_id = (req.thread_id if req and req.thread_id else config.telegram.thread_id) or None
    test_text = (
        req.text if req and req.text else (
            "<b>⚡ ENI Chain × 牛顿协议测试消息</b>\n\n"
            "这是一条来自自动化发帖平台的连通性测试消息。\n"
            "✅ Telegram Bot 连接正常\n"
            "🔗 当前监测公链: <b>ENI Mainnet (ChainID: 173)</b>\n"
            "🌐 区块浏览器: <a href='https://scan.eniac.network'>scan.eniac.network</a>\n"
            "🚀 准备就绪，实时链上监测运行中！"
        )
    )
    res = await TelegramPublisher.send_alert(
        bot_token=config.telegram.bot_token,
        chat_id=target_chat_id,
        text=test_text,
        thread_id=thread_id
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Telegram 发送失败"))
    return {"success": True, "result": res}

class TelegramDetectRequest(BaseModel):
    bot_token: Optional[str] = None

@app.post("/api/telegram/detect")
async def detect_telegram_endpoint(req: TelegramDetectRequest):
    config = await get_app_config()
    token = req.bot_token or config.telegram.bot_token
    if not token:
        raise HTTPException(status_code=400, detail="请先输入或配置 Telegram Bot Token")

    res = await TelegramPublisher.get_recent_updates(token)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "获取 Telegram 消息更新失败"))
    return res

@app.post("/api/action/test-twitter")
async def test_twitter_endpoint():
    config = await get_app_config()
    if not (config.twitter.api_key and config.twitter.access_token):
        raise HTTPException(status_code=400, detail="Twitter API 凭证未配置完整")

    test_tweet = (
        "⚡ [ENI Chain × Newton Protocol] Automation Platform Test Tweet.\n"
        "Real-time tracker connected to scan.eniac.network!\n\n"
        "#ENIChain #Newton #CryptoTest #Web3"
    )
    res = TwitterPublisher.post_tweet(
        api_key=config.twitter.api_key,
        api_secret=config.twitter.api_secret,
        access_token=config.twitter.access_token,
        access_token_secret=config.twitter.access_token_secret,
        text=test_tweet
    )
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "Twitter 发帖失败"))
    return {"success": True, "result": res}

@app.post("/api/action/watcher-toggle")
async def watcher_toggle_endpoint():
    if eni_watcher.is_running:
        eni_watcher.stop()
        return {"is_running": False, "message": "链上监听器已暂停"}
    else:
        eni_watcher.start()
        return {"is_running": True, "message": "链上监听器已启动"}

@app.get("/api/events/stream")
async def events_stream(request: Request):
    queue = asyncio.Queue()
    sse_subscribers.append(queue)

    async def event_generator():
        try:
            yield ": connected\n\n"
            while True:
                if await request.is_disconnected():
                    break
                try:
                    data = await asyncio.wait_for(queue.get(), timeout=20.0)
                    yield data
                except asyncio.TimeoutError:
                    yield ": ping\n\n"
        finally:
            if queue in sse_subscribers:
                sse_subscribers.remove(queue)

    return StreamingResponse(event_generator(), media_type="text/event-stream")

# ==========================================
# 1. Telegram Topic Bindings & Supergroup
# ==========================================

class TopicUpdateRequest(BaseModel):
    id: int
    thread_id: int
    enabled: int = 1
    topic_name: Optional[str] = None

class TopicCreateRequest(BaseModel):
    category: str = "自定义板块"
    topic_name: str
    thread_id: int
    notes: Optional[str] = ""

class TopicSendRequest(BaseModel):
    thread_id: int
    text: str
    image_path: Optional[str] = None

@app.get("/api/topics")
async def get_topics_endpoint():
    topics = await get_all_topic_bindings()
    # Group by category
    categories = {}
    for t in topics:
        cat = t.get("category", "默认板块")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(t)
    return {
        "topics": topics,
        "grouped": categories,
        "supported_languages": SUPPORTED_LANGUAGES
    }

@app.post("/api/topics/update")
async def update_topic_endpoint(req: TopicUpdateRequest):
    await update_topic_binding(req.id, req.thread_id, req.enabled, req.topic_name)
    return {"success": True, "message": f"话题 #{req.id} 绑定 Thread ID: {req.thread_id} 已更新"}

@app.post("/api/topics/create")
async def create_topic_endpoint(req: TopicCreateRequest):
    from database import add_custom_topic
    await add_custom_topic(req.category, req.topic_name, req.thread_id, req.notes or "")
    return {"success": True, "message": f"话题【{req.topic_name}】(Thread #{req.thread_id}) 已添加成功"}

@app.post("/api/topics/send")
async def send_to_topic_endpoint(req: TopicSendRequest):
    res = await topic_manager.send_to_thread(req.thread_id, req.text, req.image_path)
    if not res.get("success"):
        raise HTTPException(status_code=400, detail=res.get("error", "发送到话题失败"))
    return {"success": True, "result": res}

class SyncDetectedTopicsRequest(BaseModel):
    topics: List[Dict[str, Any]]

@app.post("/api/topics/sync-detected")
async def sync_detected_topics_endpoint(req: SyncDetectedTopicsRequest):
    from database import import_or_sync_detected_topics
    res = await import_or_sync_detected_topics(req.topics)
    return {
        "success": True,
        "message": f"成功同步话题：更新 {res['updated']} 个，新增 {res['created']} 个",
        "details": res
    }

# ==========================================
# 1.5 Multi-Day Campaigns (4 Languages Matrix)
# ==========================================

class CampaignCreateRequest(BaseModel):
    day_number: int
    campaign_title: str
    scheduled_time: str
    poster_image: Optional[str] = ""
    text_zh: Optional[str] = ""
    text_en: Optional[str] = ""
    text_ko: Optional[str] = ""
    text_vi: Optional[str] = ""

class CampaignUpdateRequest(BaseModel):
    id: int
    day_number: int
    campaign_title: str
    scheduled_time: str
    poster_image: Optional[str] = ""
    text_zh: Optional[str] = ""
    text_en: Optional[str] = ""
    text_ko: Optional[str] = ""
    text_vi: Optional[str] = ""
    status: Optional[str] = "pending"

class CampaignTranslateRequest(BaseModel):
    text: str
    source_lang: Optional[str] = "zh"

@app.get("/api/campaigns")
async def get_campaigns_endpoint():
    from database import get_all_campaigns
    campaigns = await get_all_campaigns()
    return {"campaigns": campaigns}

@app.post("/api/campaigns/create")
async def create_campaign_endpoint(req: CampaignCreateRequest):
    from database import add_campaign
    cid = await add_campaign(
        day_number=req.day_number,
        campaign_title=req.campaign_title,
        scheduled_time=req.scheduled_time,
        poster_image=req.poster_image or "",
        text_zh=req.text_zh or "",
        text_en=req.text_en or "",
        text_ko=req.text_ko or "",
        text_vi=req.text_vi or ""
    )
    return {"success": True, "id": cid, "message": f"排期计划【{req.campaign_title}】已成功创建"}

@app.post("/api/campaigns/update")
async def update_campaign_endpoint(req: CampaignUpdateRequest):
    from database import update_campaign
    await update_campaign(
        cid=req.id,
        day_number=req.day_number,
        campaign_title=req.campaign_title,
        scheduled_time=req.scheduled_time,
        poster_image=req.poster_image or "",
        text_zh=req.text_zh or "",
        text_en=req.text_en or "",
        text_ko=req.text_ko or "",
        text_vi=req.text_vi or "",
        status=req.status or "pending"
    )
    return {"success": True, "message": "排期计划已成功保存"}

@app.post("/api/campaigns/delete")
async def delete_campaign_endpoint(req: Dict[str, int]):
    from database import delete_campaign
    cid = req.get("id")
    if not cid:
        raise HTTPException(status_code=400, detail="缺少 ID")
    await delete_campaign(cid)
    return {"success": True, "message": f"计划 #{cid} 已删除"}

@app.post("/api/campaigns/translate")
async def translate_campaign_endpoint(req: CampaignTranslateRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="文案不能为空")
    from services.translator import translate_single_text
    targets = ["en", "zh", "ko", "vi"]
    res = {}
    for lang in targets:
        if lang == req.source_lang:
            res[lang] = req.text
        else:
            res[lang] = await translate_single_text(req.text, lang)
    return {"success": True, "translations": res}

@app.get("/api/campaigns/local-posters")
async def get_local_posters_endpoint():
    posters_dir = os.path.join(STATIC_DIR, "uploads", "posters")
    if not os.path.exists(posters_dir):
        return {"posters": []}
    files = []
    for f in os.listdir(posters_dir):
        if f.lower().endswith((".png", ".jpg", ".jpeg", ".webp")):
            files.append({
                "filename": f,
                "url": f"/static/uploads/posters/{f}"
            })
    files.sort(key=lambda x: x["filename"])
    return {"posters": files}

@app.post("/api/campaigns/upload-poster")
async def upload_poster_endpoint(file: UploadFile = File(...)):
    posters_dir = os.path.join(STATIC_DIR, "uploads", "posters")
    os.makedirs(posters_dir, exist_ok=True)
    import time
    clean_filename = f"poster_{int(time.time())}_{file.filename}"
    target_path = os.path.join(posters_dir, clean_filename)
    with open(target_path, "wb") as buffer:
        content = await file.read()
        buffer.write(content)
    return {
        "success": True,
        "filename": clean_filename,
        "url": f"/static/uploads/posters/{clean_filename}"
    }

@app.post("/api/campaigns/trigger")
async def trigger_campaign_endpoint(req: Dict[str, int]):
    cid = req.get("id")
    if not cid:
        raise HTTPException(status_code=400, detail="缺少计划 ID")
    try:
        res = await daily_scheduler.trigger_campaign(cid)
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ==========================================
# 2. 11-Language Multilingual Broadcast
# ==========================================

class MultilingualPreviewRequest(BaseModel):
    text: str
    langs: Optional[List[str]] = None

class MultilingualBroadcastRequest(BaseModel):
    text: str
    image_path: Optional[str] = None
    langs: Optional[List[str]] = None

@app.post("/api/multilingual/preview")
async def multilingual_preview_endpoint(req: MultilingualPreviewRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="广播文案不能为空")
    
    translations = await translate_to_all_languages(req.text, req.langs)
    all_topics = await get_all_topic_bindings()
    lang_to_thread = {
        t["lang_code"]: t["thread_id"]
        for t in all_topics if t.get("lang_code") and t.get("enabled")
    }

    cards = []
    active_langs = req.langs if req.langs else ["en", "zh", "ko", "vi"]
    for code in active_langs:
        meta = SUPPORTED_LANGUAGES.get(code)
        if not meta:
            continue
        cards.append({
            "lang": code,
            "name": meta["name"],
            "native": meta["native"],
            "flag": meta["flag"],
            "thread_id": lang_to_thread.get(code, meta["default_thread_id"]),
            "text": translations.get(code, req.text),
            "status": "ready"
        })

    return {"success": True, "cards": cards, "total": len(cards)}

@app.post("/api/multilingual/broadcast")
async def multilingual_broadcast_endpoint(req: MultilingualBroadcastRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="广播文案不能为空")

    target_langs = req.langs or ["en", "zh", "ko", "vi"]
    res = await topic_manager.broadcast_multilingual(
        source_text=req.text,
        image_path=req.image_path,
        target_langs=target_langs
    )
    return {"success": True, "broadcast": res}

# ==========================================
# 3. AI Research Desk (ENI 投研中心)
# ==========================================

class ResearchDispatchRequest(BaseModel):
    title: str
    content: str
    target_thread_id: Optional[int] = 1
    send_to_telegram: bool = True
    send_to_twitter: bool = False
    image_path: Optional[str] = None

@app.get("/api/research/desk/{desk_type}")
async def get_research_desk_endpoint(desk_type: str):
    data = await research_desk.generate_desk_content(desk_type)
    return data

@app.post("/api/research/dispatch")
async def dispatch_research_endpoint(req: ResearchDispatchRequest):
    config = await get_app_config()
    tg_res = {"success": False, "message_id": None, "error": None}
    tw_res = {"success": False, "tweet_id": None, "error": None}

    # 1. Telegram
    if req.send_to_telegram and req.target_thread_id:
        tg_res = await topic_manager.send_to_thread(
            thread_id=req.target_thread_id,
            text=req.content,
            image_path=req.image_path
        )

    # 2. Twitter
    if req.send_to_twitter:
        tw_text = req.content[:240] + "...\n\n#ENI #NewtonProtocol"
        ok, tweet_id, err = await TwitterPublisher.post_with_config(tw_text, req.image_path)
        tw_res = {"success": ok, "tweet_id": tweet_id, "error": err}

    # Record post history
    await record_post_history(
        event_type="research",
        tx_hash=None,
        title=req.title,
        content=req.content,
        image_path=req.image_path,
        telegram_status="success" if tg_res.get("success") else "failed",
        telegram_msg_id=str(tg_res.get("message_id") or ""),
        telegram_error=str(tg_res.get("error") or ""),
        twitter_status="success" if tw_res.get("success") else "failed",
        twitter_tweet_id=str(tw_res.get("tweet_id") or ""),
        twitter_error=str(tw_res.get("error") or "")
    )

    return {
        "success": True,
        "telegram": tg_res,
        "twitter": tw_res
    }

# ==========================================
# 4. Scheduled Tasks Automation
# ==========================================

class SchedulerToggleRequest(BaseModel):
    task_id: str
    enabled: int
    cron_expr: Optional[str] = None

@app.get("/api/scheduler/tasks")
async def list_scheduler_tasks_endpoint():
    tasks = await scheduled_tasks_manager.list_tasks()
    return {"tasks": tasks}

@app.post("/api/scheduler/toggle")
async def toggle_scheduler_task_endpoint(req: SchedulerToggleRequest):
    await scheduled_tasks_manager.toggle_task(req.task_id, req.enabled, req.cron_expr)
    return {"success": True, "message": f"任务 {req.task_id} 状态已更新"}

@app.post("/api/scheduler/run/{task_id}")
async def run_scheduler_task_endpoint(task_id: str):
    res = await scheduled_tasks_manager.execute_task_now(task_id)
    return res

@app.get("/api/scheduler/logs")
async def get_scheduler_logs_endpoint():
    logs = await scheduled_tasks_manager.get_logs()
    return {"logs": logs}

# ==========================================
# 5. Twitter (X.com) Matrix Operations
# ==========================================

class TwitterPublishRequest(BaseModel):
    text: str
    image_path: Optional[str] = None
    sync_tg_thread_id: Optional[int] = None

@app.post("/api/twitter/publish")
async def publish_tweet_endpoint(req: TwitterPublishRequest):
    if not req.text.strip():
        raise HTTPException(status_code=400, detail="推文内容不能为空")
    
    ok, tweet_id, err = await TwitterPublisher.post_with_config(req.text, req.image_path)
    if not ok:
        raise HTTPException(status_code=400, detail=f"Twitter 发送失败: {err}")

    tg_res = None
    if req.sync_tg_thread_id:
        tg_res = await topic_manager.send_to_thread(
            thread_id=req.sync_tg_thread_id,
            text=f"🐦 <b>X (Twitter) 同步发布</b>\n\n{req.text}\n\n🔗 https://x.com/eni_newton/status/{tweet_id}",
            image_path=req.image_path
        )

    # Save to post history
    await record_post_history(
        event_type="twitter_compose",
        tx_hash=None,
        title="推特矩阵运营发文",
        content=req.text,
        image_path=req.image_path,
        telegram_status="success" if (tg_res and tg_res.get("success")) else "skipped",
        telegram_msg_id=str(tg_res.get("message_id") if tg_res else ""),
        twitter_status="success",
        twitter_tweet_id=tweet_id
    )

    return {
        "success": True,
        "tweet_id": tweet_id,
        "tweet_url": f"https://x.com/eni_newton/status/{tweet_id}",
        "telegram_sync": tg_res
    }

# ==========================================
# 7. Vercel & Cloud Cron Trigger Endpoints
# ==========================================

@app.get("/api/cron/trigger/{slot}")
async def cron_trigger_slot_endpoint(slot: str):
    """
    Trigger morning / afternoon / evening post via HTTP GET (compatible with Vercel Cron & Uptime Monitors)
    """
    try:
        res = await daily_scheduler.trigger_slot(slot, force=True)
        return {"success": True, "result": res}
    except Exception as e:
        return {"success": False, "error": str(e)}

@app.get("/api/cron/trigger-task/{task_id}")
async def cron_trigger_task_endpoint(task_id: str):
    """
    Trigger a specific scheduled task by ID via HTTP GET
    """
    try:
        res = await scheduled_tasks_manager.execute_task_now(task_id)
        return {"success": True, "result": res}
    except Exception as e:
        return {"success": False, "error": str(e)}

_db_initialized = False

async def ensure_db_ready():
    global _db_initialized
    if not _db_initialized:
        await init_db()
        _db_initialized = True

@app.middleware("http")
async def db_ensure_middleware(request: Request, call_next):
    try:
        await ensure_db_ready()
    except Exception as e:
        print(f"[Middleware] DB init exception: {e}")
    try:
        response = await call_next(request)
        return response
    except Exception as exc:
        import traceback
        err_tb = traceback.format_exc()
        print(f"[Middleware] Request exception: {err_tb}")
        return HTMLResponse(
            f"<html><body style='background:#0d1117;color:#c9d1d9;font-family:sans-serif;padding:32px;'>"
            f"<h2 style='color:#f85149;'>⚠️ Newton Platform Request Error</h2>"
            f"<pre style='background:#161b22;padding:16px;border-radius:6px;overflow:auto;color:#ff7b72;border:1px solid #30363d;'>{err_tb}</pre>"
            f"</body></html>",
            status_code=500
        )

try:
    os.makedirs(IMAGES_DIR, exist_ok=True)
except Exception:
    pass

@app.get("/", response_class=HTMLResponse)
async def root():
    candidates = [
        os.path.join(STATIC_DIR, "index.html"),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "static", "index.html")),
        os.path.abspath("static/index.html"),
        "/var/task/static/index.html"
    ]
    for p in candidates:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read(), status_code=200, headers={
                    "Cache-Control": "no-cache, no-store, must-revalidate",
                    "Pragma": "no-cache",
                    "Expires": "0"
                })
    return HTMLResponse("<h1>Newton Telegram Operations Platform Backend Running</h1>")

@app.get("/static/{file_path:path}")
async def serve_static_file(file_path: str):
    candidates = [
        os.path.join(STATIC_DIR, file_path),
        os.path.abspath(os.path.join(os.path.dirname(__file__), "static", file_path)),
        os.path.abspath(os.path.join("static", file_path)),
        os.path.join("/var/task/static", file_path)
    ]
    for p in candidates:
        if os.path.exists(p) and os.path.isfile(p):
            media_type = "text/plain"
            if p.endswith(".css"):
                media_type = "text/css"
            elif p.endswith(".js"):
                media_type = "application/javascript"
            elif p.endswith(".html"):
                media_type = "text/html"
            elif p.endswith(".json"):
                media_type = "application/json"
            elif p.endswith((".png", ".jpg", ".jpeg")):
                with open(p, "rb") as bf:
                    return Response(content=bf.read(), media_type="image/png")
            with open(p, "r", encoding="utf-8", errors="ignore") as f:
                return Response(content=f.read(), media_type=media_type)
    raise HTTPException(status_code=404, detail="Static file not found")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8080, reload=True)
