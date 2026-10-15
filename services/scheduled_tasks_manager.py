import asyncio
from datetime import datetime
from typing import Dict, Any, List, Optional
from database import (
    get_all_scheduled_tasks,
    update_scheduled_task,
    log_task_run,
    get_recent_task_logs,
    record_post_history
)
from services.topic_manager import topic_manager
from services.research_desk import research_desk
from services.eni_content_generator import ENIContentGenerator
from database import get_app_config
from publishers.twitter_client import TwitterPublisher
from image_generator import generate_banner_image

class ScheduledTasksManager:
    def __init__(self):
        self.twitter = TwitterPublisher()
        self.is_running = False
        self._task_handle = None

    async def list_tasks(self) -> List[Dict[str, Any]]:
        return await get_all_scheduled_tasks()

    async def toggle_task(self, task_id: str, enabled: int, cron_expr: Optional[str] = None):
        await update_scheduled_task(task_id, enabled, cron_expr)

    async def get_logs(self, limit: int = 30) -> List[Dict[str, Any]]:
        return await get_recent_task_logs(limit)

    async def execute_task_now(self, task_id: str) -> Dict[str, Any]:
        """
        Manually or automatically triggers an execution of a scheduled task.
        """
        tasks = await get_all_scheduled_tasks()
        task = next((t for t in tasks if t["id"] == task_id), None)
        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        name = task["name"]
        thread_id = task["target_thread_id"]
        target_type = task.get("target_type", "telegram")
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        title = ""
        content = ""
        banner_theme = "tech"

        try:
            if task_id == "hourly_research":
                data = await research_desk.generate_desk_content("random")
                title, content = data["title"], data["content"]
                banner_theme = "tech"
            elif task_id == "gold_market":
                title = f"🪙 黄金与宏观市场流动性专报 ({now_str[:16]})"
                content = (
                    f"【{title}】\n\n"
                    f"📊 宏观大类资产与避险资产综述：\n"
                    f"• 现货黄金 (XAU/USD): 窄幅盘整于历史高位区间，抗通胀属性凸显\n"
                    f"• 美元指数 (DXY): 维持震荡整理，全球风险偏好对加密资产保持敏感\n"
                    f"• ENI 链上黄金与 RWA 代币化探索：通过 Newton Protocol 协议，支持将实物黄金资产映射至 ENI 进行低滑点清算。\n\n"
                    f"#Gold #Macro #RWA #ENIChain"
                )
                banner_theme = "staking"
            elif task_id == "global_markets":
                title = f"📈 全球主要股指与流动性跟踪 ({now_str[:16]})"
                content = (
                    f"【{title}】\n\n"
                    f"🌎 全球核心资产表现透视：\n"
                    f"• 纳斯达克100 / 标普500: AI 算力与科技巨头持续领跑全球资本市场\n"
                    f"• 加密总市值: 与纳斯达克科技板块相关系数收敛，结构性独立行情显现\n"
                    f"• ENI 跨市场结算: 赋能全球量化团队以毫秒级确定性执行跨市场对冲。\n\n"
                    f"#GlobalMarkets #Crypto #Nasdaq #ENI"
                )
                banner_theme = "summary"
            elif task_id == "morning_pulse":
                if thread_id in (1, 16):
                    cfg = await get_app_config()
                    data = await ENIContentGenerator.generate_morning_post(cfg, lang="en")
                    title, content = data.get("title", "ENI Morning Pulse"), data.get("content", "")
                else:
                    data = await research_desk.generate_desk_content("daily")
                    title, content = data["title"], data["content"]
                banner_theme = "summary"
            elif task_id == "arch_intel":
                if thread_id in (1, 16):
                    cfg = await get_app_config()
                    data = await ENIContentGenerator.generate_afternoon_post(cfg, lang="en")
                    title, content = data.get("title", "ENI Core Architecture"), data.get("content", "")
                else:
                    data = await research_desk.generate_desk_content("architecture")
                    title, content = data["title"], data["content"]
                banner_theme = "tech"
            elif task_id == "general_broadcast":
                if thread_id in (1, 16):
                    title = "💬 Newton Protocol × ENI Chain Community Pulse"
                    content = (
                        "🌟 <b>【Newton Protocol × ENI Chain Community Digest】</b> 🌟\n\n"
                        "Greetings to all global community members! ENI Mainnet is operating smoothly with sub-second finality.\n\n"
                        "📌 <b>Community Essentials:</b>\n"
                        "• Join discussions in your dedicated regional language chats\n"
                        "• Beware of scammers: Official admins will never DM first asking for private keys\n"
                        "• Official Block Explorer: https://scan.eniac.network\n"
                        "• Newton DEX Portal: https://xplan.eniac.network/swap\n\n"
                        "Building an autonomous, decentralized high-frequency future together! 🚀\n"
                        "#NewtonProtocol #ENIChain #Web3 #Community #Layer1"
                    )
                else:
                    title = f"💬 Newton ENI 社区每日交流与生态活跃指南"
                    content = (
                        f"【{title}】\n\n"
                        f"🌟 各位 Newton ENI 社区成员，主网当前稳定运行中！\n"
                        f"• 欢迎在各语言频道及技术投研板块畅所欲言；\n"
                        f"• 谨防任何非官方人员私信索要资产或私钥；\n"
                        f"• 官方区块链浏览器: https://scan.eniac.network/\n\n"
                        f"一起建设更高速、更去中心化的 Web3 未来！🚀\n"
                        f"#NewtonProtocol #ENI #Community"
                    )
                banner_theme = "news"
            elif task_id == "whale_evening":
                data = await research_desk.generate_desk_content("risk")
                title, content = data["title"], data["content"]
                banner_theme = "whale"
            else:
                title = f"⚡ 自动任务触发: {name}"
                content = f"【{name}】\n\n系统定时任务于 {now_str} 成功调度执行。"
                banner_theme = "tech"

            # Generate banner image
            img_path = generate_banner_image(
                theme=banner_theme,
                title=title[:25],
                subtitle=f"Scheduled Task #{task_id}",
                footer_text="Newton Protocol × ENI Chain Automation"
            )

            # Send to Telegram
            tg_res = {"success": False, "message_id": None, "error": None}
            if target_type in ("telegram", "both"):
                tg_res = await topic_manager.send_to_thread(
                    thread_id=thread_id,
                    text=content,
                    image_path=img_path
                )

            # Send to Twitter if needed
            tw_res = {"success": False, "tweet_id": None, "error": None}
            if target_type in ("twitter", "both"):
                # Shorten for Twitter
                tw_text = content[:200] + "...\n\n#ENI #NewtonProtocol"
                ok, tweet_id, tw_err = await TwitterPublisher.post_with_config(tw_text, img_path)
                tw_res = {"success": ok, "tweet_id": tweet_id, "error": tw_err}

            # Record log
            status_str = "success" if (tg_res.get("success") or tw_res.get("success")) else "failed"
            detail_msg = f"TG: {tg_res.get('message_id') or tg_res.get('error')}; TW: {tw_res.get('tweet_id') or tw_res.get('error')}"
            await log_task_run(task_id, name, thread_id, status_str, detail_msg)

            # Record post history
            await record_post_history(
                event_type="scheduler",
                tx_hash=None,
                title=title,
                content=content,
                image_path=img_path,
                telegram_status="success" if tg_res.get("success") else "failed",
                telegram_msg_id=str(tg_res.get("message_id") or ""),
                telegram_error=str(tg_res.get("error") or ""),
                twitter_status="success" if tw_res.get("success") else "failed",
                twitter_tweet_id=str(tw_res.get("tweet_id") or ""),
                twitter_error=str(tw_res.get("error") or "")
            )

            return {
                "success": True,
                "task_id": task_id,
                "task_name": name,
                "thread_id": thread_id,
                "telegram": tg_res,
                "twitter": tw_res,
                "executed_at": now_str
            }

        except Exception as e:
            err_msg = str(e)
            print(f"[ScheduledTasksManager] Error running task {task_id}: {e}")
            await log_task_run(task_id, name, thread_id, "error", err_msg)
            return {"success": False, "task_id": task_id, "error": err_msg}

    async def _loop(self):
        """
        Background loop inspecting tasks every 60s.
        """
        while self.is_running:
            try:
                now = datetime.now()
                # Check for hourly tasks (at minute 0)
                if now.minute == 0:
                    tasks = await get_all_scheduled_tasks()
                    for t in tasks:
                        if t.get("enabled"):
                            # Hourly tasks
                            if t["cron_expr"] == "0 * * * *":
                                await self.execute_task_now(t["id"])
                            # Morning 9:00
                            elif t["cron_expr"] == "0 9 * * *" and now.hour == 9:
                                await self.execute_task_now(t["id"])
                            # General broadcast 11:00
                            elif t["cron_expr"] == "0 11 * * *" and now.hour == 11:
                                await self.execute_task_now(t["id"])
                            # Whale evening 20:00
                            elif t["cron_expr"] == "0 20 * * *" and now.hour == 20:
                                await self.execute_task_now(t["id"])
                
                # Check 16:30 task
                elif now.minute == 30 and now.hour == 16:
                    tasks = await get_all_scheduled_tasks()
                    t = next((x for x in tasks if x["id"] == "arch_intel" and x.get("enabled")), None)
                    if t:
                        await self.execute_task_now(t["id"])

            except Exception as e:
                print(f"[ScheduledTasksManager] Scheduler loop tick error: {e}")

            await asyncio.sleep(60)

    def start(self):
        if not self.is_running:
            self.is_running = True
            self._task_handle = asyncio.create_task(self._loop())
            print("[ScheduledTasksManager] Automated task scheduler started.")

    def stop(self):
        self.is_running = False
        if self._task_handle:
            self._task_handle.cancel()

scheduled_tasks_manager = ScheduledTasksManager()
