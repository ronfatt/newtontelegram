import asyncio
import datetime
import json
import os
from typing import Dict, Any, Optional
from database import get_app_config, record_daily_slot_run, get_today_slot_runs, get_all_topic_bindings
from services.eni_content_generator import ENIContentGenerator
from services.alert_engine import alert_engine

class DailyScheduler:
    def __init__(self):
        self.is_running = False
        self._task: Optional[asyncio.Task] = None
        self.last_checked_minute = ""

    def get_today_date_str(self) -> str:
        return datetime.datetime.now().strftime("%Y-%m-%d")

    async def get_daily_status(self) -> Dict[str, Any]:
        config = await get_app_config()
        ds = config.daily_schedule
        today_str = self.get_today_date_str()
        runs = await get_today_slot_runs(today_str)

        return {
            "date": today_str,
            "enabled": ds.enabled,
            "slots": {
                "morning": {
                    "time": ds.morning_time,
                    "title": "🌅 晨间 09:00：ENI 链上数据实时战报 (#General 英文)",
                    "executed": "morning" in runs,
                    "info": runs.get("morning")
                },
                "afternoon": {
                    "time": ds.afternoon_time,
                    "title": "☀️ 午间 14:00：ENI 核心技术与愿景深度 (#General 英文)",
                    "executed": "afternoon" in runs,
                    "info": runs.get("afternoon")
                },
                "evening": {
                    "time": ds.evening_time,
                    "title": "🌙 晚间 20:00：ENI 生态交易与流动性速报 (#General 英文)",
                    "executed": "evening" in runs,
                    "info": runs.get("evening")
                }
            }
        }

    async def trigger_slot(self, slot: str, force: bool = True) -> Dict[str, Any]:
        """
        触发每日三篇发帖计划：
        - 针对 Telegram 官方群组的 【# General】(Thread ID: 1) 发送地道英文图文
        - 同时如果开启了 Twitter/X，自动发布推文
        """
        config = await get_app_config()
        today_str = self.get_today_date_str()

        if not force:
            runs = await get_today_slot_runs(today_str)
            if slot in runs:
                return {"skipped": True, "reason": f"Slot '{slot}' already executed today."}

        # 1. 动态获取 # General 的真实 Thread ID (默认 1)
        general_thread_id = 1
        all_topics = await get_all_topic_bindings()
        for t in all_topics:
            if "General" in t.get("topic_name", ""):
                general_thread_id = t.get("thread_id", 1)
                break

        # 2. 生成英文内容 (lang="en")
        if slot == "morning":
            event_data = await ENIContentGenerator.generate_morning_post(config, lang="en")
        elif slot == "afternoon":
            event_data = await ENIContentGenerator.generate_afternoon_post(config, lang="en")
        elif slot == "evening":
            event_data = await ENIContentGenerator.generate_evening_post(config, lang="en")
        else:
            raise ValueError(f"Unknown slot: {slot}")

        event_data["target_thread_id"] = general_thread_id

        # 3. 处理派发 (自动渲染图文卡片，发送至 #General 及 Twitter)
        result = await alert_engine.process_event(event_data, config)

        # 4. 记录日志
        post_id = result.get("post_id", 0)
        title = event_data.get("title", f"ENI {slot.capitalize()} Post")
        await record_daily_slot_run(today_str, slot, title, post_id)

        return {
            "success": True,
            "slot": slot,
            "target_topic": "# General",
            "thread_id": general_thread_id,
            "date": today_str,
            "post_id": post_id,
            "title": title,
            "event": result
        }

    async def trigger_campaign(self, campaign_id: int) -> Dict[str, Any]:
        """
        执行指定多天排期计划，自动将对应文案和海报并发推送到 4 大语言频道：
        - 🇬🇧 ENGLISH CHAT (Thread 16)
        - 🇨🇳 CHINESE CHAT (Thread 17)
        - 🇰🇷 KOREAN CHAT (Thread 18)
        - 🇻🇳 VIETNAMESE CHAT (Thread 19)
        """
        from database import get_campaign_by_id, mark_campaign_sent
        from publishers.telegram_bot import TelegramPublisher

        campaign = await get_campaign_by_id(campaign_id)
        if not campaign:
            raise ValueError(f"Campaign #{campaign_id} not found")

        config = await get_app_config()
        bot_token = config.telegram.bot_token
        chat_id = config.telegram.chat_id

        if not bot_token or not chat_id:
            raise ValueError("Telegram Bot Token 或 Chat ID 尚未配置")

        # 动态绑定 4 大语言话题线程
        topics = await get_all_topic_bindings()
        thread_map = {
            "en": 16,
            "zh": 17,
            "ko": 18,
            "vi": 19
        }
        for t in topics:
            name = t.get("topic_name", "")
            tid = t.get("thread_id")
            if "ENGLISH CHAT" in name:
                thread_map["en"] = tid
            elif "CHINESE CHAT" in name:
                thread_map["zh"] = tid
            elif "KOREAN CHAT" in name:
                thread_map["ko"] = tid
            elif "VIETNAMESE CHAT" in name:
                thread_map["vi"] = tid

        # 寻找真实海报路径
        poster = campaign.get("poster_image")
        real_image_path = None
        if poster:
            base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            if poster.startswith("/static/"):
                candidate = os.path.join(base_dir, poster.lstrip("/"))
                if os.path.exists(candidate):
                    real_image_path = candidate
            elif os.path.isabs(poster) and os.path.exists(poster):
                real_image_path = poster
            else:
                candidate = os.path.join(base_dir, poster)
                if os.path.exists(candidate):
                    real_image_path = candidate

        dispatches = [
            ("en", thread_map["en"], campaign.get("text_en") or campaign.get("text_zh")),
            ("zh", thread_map["zh"], campaign.get("text_zh") or campaign.get("text_en")),
            ("ko", thread_map["ko"], campaign.get("text_ko") or campaign.get("text_en")),
            ("vi", thread_map["vi"], campaign.get("text_vi") or campaign.get("text_en"))
        ]

        results = {}
        for lang, tid, text in dispatches:
            if not text:
                continue
            res = await TelegramPublisher.send_alert(
                bot_token=bot_token,
                chat_id=chat_id,
                text=text,
                image_path=real_image_path,
                thread_id=str(tid)
            )
            results[lang] = {
                "thread_id": tid,
                "success": res.get("success", False),
                "message_id": res.get("message_id"),
                "error": res.get("error")
            }

        await mark_campaign_sent(campaign_id, json.dumps(results, ensure_ascii=False))
        return {
            "success": True,
            "campaign_id": campaign_id,
            "title": campaign.get("campaign_title"),
            "results": results
        }

    async def _run_loop(self):
        print("[Daily Scheduler] Background scheduler started (3 Daily Posts to #General + Multi-day Campaigns)...")
        while self.is_running:
            try:
                now = datetime.datetime.now()
                current_hm = now.strftime("%H:%M")

                if current_hm != self.last_checked_minute:
                    self.last_checked_minute = current_hm
                    config = await get_app_config()
                    ds = config.daily_schedule

                    # 1. 每日三篇 #General 英文发帖
                    if ds.enabled:
                        today_str = self.get_today_date_str()
                        runs = await get_today_slot_runs(today_str)

                        if current_hm == ds.morning_time and "morning" not in runs:
                            print(f"[Daily Scheduler] Triggering morning post to #General at {current_hm}...")
                            await self.trigger_slot("morning", force=False)

                        elif current_hm == ds.afternoon_time and "afternoon" not in runs:
                            print(f"[Daily Scheduler] Triggering afternoon post to #General at {current_hm}...")
                            await self.trigger_slot("afternoon", force=False)

                        elif current_hm == ds.evening_time and "evening" not in runs:
                            print(f"[Daily Scheduler] Triggering evening post to #General at {current_hm}...")
                            await self.trigger_slot("evening", force=False)

                    # 2. 检查多天排期计划 (4 大语言频道)
                    from database import get_all_campaigns
                    campaigns = await get_all_campaigns()
                    today_ymd = now.strftime("%Y-%m-%d")
                    for c in campaigns:
                        if c.get("status") == "pending":
                            sched = c.get("scheduled_time", "").strip()
                            match_due = False
                            if len(sched) == 5 and sched == current_hm:
                                match_due = True
                            elif f"{today_ymd} {current_hm}" == sched:
                                match_due = True

                            if match_due:
                                print(f"[Daily Scheduler] Triggering campaign Day {c.get('day_number')} '{c.get('campaign_title')}' at {current_hm}...")
                                try:
                                    await self.trigger_campaign(c["id"])
                                except Exception as ce:
                                    print(f"[Daily Scheduler] Campaign trigger error: {ce}")

            except Exception as e:
                print(f"[Daily Scheduler] Loop error: {e}")

            await asyncio.sleep(25)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._task = asyncio.create_task(self._run_loop())

    def stop(self):
        self.is_running = False
        if self._task and not self._task.done():
            self._task.cancel()

daily_scheduler = DailyScheduler()
