import asyncio
import datetime
from typing import Dict, Any, Optional
from database import get_app_config, record_daily_slot_run, get_today_slot_runs
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
                    "title": "晨间 09:00：ENI 链上数据实时战报",
                    "executed": "morning" in runs,
                    "info": runs.get("morning")
                },
                "afternoon": {
                    "time": ds.afternoon_time,
                    "title": "午间 14:00：ENI 官网核心技术与愿景",
                    "executed": "afternoon" in runs,
                    "info": runs.get("afternoon")
                },
                "evening": {
                    "time": ds.evening_time,
                    "title": "晚间 20:00：ENI 生态交易与巨鲸速报",
                    "executed": "evening" in runs,
                    "info": runs.get("evening")
                }
            }
        }

    async def trigger_slot(self, slot: str, force: bool = True) -> Dict[str, Any]:
        """Triggers one of the 3 daily posts (morning, afternoon, evening)"""
        config = await get_app_config()
        today_str = self.get_today_date_str()

        if not force:
            runs = await get_today_slot_runs(today_str)
            if slot in runs:
                return {"skipped": True, "reason": f"Slot '{slot}' already executed today."}

        # 1. Generate content according to slot
        if slot == "morning":
            event_data = await ENIContentGenerator.generate_morning_post(config)
        elif slot == "afternoon":
            event_data = await ENIContentGenerator.generate_afternoon_post(config)
        elif slot == "evening":
            event_data = await ENIContentGenerator.generate_evening_post(config)
        else:
            raise ValueError(f"Unknown slot: {slot}")

        # 2. Process event (format text, render graphic card, dispatch to TG & Twitter)
        result = await alert_engine.process_event(event_data, config)

        # 3. Record slot execution in DB
        post_id = result.get("post_id", 0)
        title = event_data.get("title", f"ENI {slot.capitalize()} Post")
        await record_daily_slot_run(today_str, slot, title, post_id)

        return {
            "success": True,
            "slot": slot,
            "date": today_str,
            "post_id": post_id,
            "title": title,
            "event": result
        }

    async def _run_loop(self):
        print("[Daily Scheduler] Background scheduler started for 3 daily ENI posts...")
        while self.is_running:
            try:
                now = datetime.datetime.now()
                current_hm = now.strftime("%H:%M")

                if current_hm != self.last_checked_minute:
                    self.last_checked_minute = current_hm
                    config = await get_app_config()
                    ds = config.daily_schedule

                    if ds.enabled:
                        today_str = self.get_today_date_str()
                        runs = await get_today_slot_runs(today_str)

                        if current_hm == ds.morning_time and "morning" not in runs:
                            print(f"[Daily Scheduler] Triggering morning post at {current_hm}...")
                            await self.trigger_slot("morning", force=False)

                        elif current_hm == ds.afternoon_time and "afternoon" not in runs:
                            print(f"[Daily Scheduler] Triggering afternoon post at {current_hm}...")
                            await self.trigger_slot("afternoon", force=False)

                        elif current_hm == ds.evening_time and "evening" not in runs:
                            print(f"[Daily Scheduler] Triggering evening post at {current_hm}...")
                            await self.trigger_slot("evening", force=False)

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
