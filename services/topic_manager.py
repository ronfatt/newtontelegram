import asyncio
from typing import Dict, List, Optional, Any
from database import get_all_topic_bindings, update_topic_binding, log_task_run, get_app_config
from publishers.telegram_bot import TelegramPublisher
from services.translator import translate_to_all_languages, SUPPORTED_LANGUAGES

class TopicManager:
    async def get_all_topics(self) -> List[Dict[str, Any]]:
        return await get_all_topic_bindings()

    async def save_topic_thread(self, topic_id: int, thread_id: int, enabled: int = 1):
        await update_topic_binding(topic_id, thread_id, enabled)

    async def send_to_thread(
        self,
        thread_id: int,
        text: str,
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Sends a message or photo to a specific supergroup thread.
        """
        config = await get_app_config()
        bot_token = config.telegram.bot_token
        chat_id = config.telegram.chat_id

        if not bot_token or not chat_id:
            return {
                "success": False,
                "message_id": None,
                "error": "Telegram Bot Token 或 Chat ID 尚未在系统设置中配置",
                "thread_id": thread_id
            }

        res = await TelegramPublisher.send_alert(
            bot_token=bot_token,
            chat_id=chat_id,
            text=text,
            image_path=image_path,
            thread_id=str(thread_id) if thread_id else None
        )
        return {
            "success": res.get("success", False),
            "message_id": res.get("message_id"),
            "error": res.get("error"),
            "thread_id": thread_id
        }

    async def broadcast_multilingual(
        self,
        source_text: str,
        image_path: Optional[str] = None,
        target_langs: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Translates text into national languages and broadcasts each to its corresponding Telegram topic thread.
        """
        # 1. Fetch current topic bindings
        all_topics = await get_all_topic_bindings()
        lang_to_thread = {}
        for t in all_topics:
            if t.get("enabled") and t.get("lang_code") in ("en", "zh", "ko", "vi"):
                lang = t.get("lang_code")
                lang_to_thread[lang] = {
                    "thread_id": t.get("thread_id"),
                    "name": t.get("topic_name")
                }

        # 2. Translate text
        langs_to_send = target_langs or list(lang_to_thread.keys())
        translations = await translate_to_all_languages(source_text, langs_to_send)

        # 3. Dispatch concurrently to each topic
        results = {}
        
        async def _dispatch_lang(lang: str, translated_text: str):
            thread_info = lang_to_thread.get(lang)
            if not thread_info:
                # Fallback to default
                def_thread = SUPPORTED_LANGUAGES.get(lang, {}).get("default_thread_id", 1)
                thread_id = def_thread
                tname = SUPPORTED_LANGUAGES.get(lang, {}).get("name", lang)
            else:
                thread_id = thread_info["thread_id"]
                tname = thread_info["name"]

            # Add language header tag
            lang_meta = SUPPORTED_LANGUAGES.get(lang, {})
            flag = lang_meta.get("flag", "🌐")
            header = f"{flag} 【{lang_meta.get('native', tname)} 官方频道】\n\n"
            full_msg = header + translated_text

            res = await self.send_to_thread(thread_id, full_msg, image_path)
            res["lang"] = lang
            res["name"] = tname
            res["flag"] = flag
            res["translated_text"] = translated_text
            return lang, res

        tasks = [
            _dispatch_lang(lang, trans)
            for lang, trans in translations.items()
        ]
        completed = await asyncio.gather(*tasks, return_exceptions=True)

        for item in completed:
            if isinstance(item, tuple):
                lang, res = item
                results[lang] = res
            else:
                print(f"[TopicManager] Broadcast item failed: {item}")

        return {
            "total_broadcasted": len(results),
            "results": results
        }

topic_manager = TopicManager()
