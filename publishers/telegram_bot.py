import os
import json
import re
import asyncio
import logging
import httpx
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class TelegramPublisher:
    BASE_URL = "https://api.telegram.org/bot"

    @classmethod
    def clean_token(cls, token: Optional[str]) -> str:
        """Sanitizes bot token by stripping whitespace, quotes, and unnecessary 'bot' prefix"""
        if not token:
            return ""
        t = str(token).strip().strip('"').strip("'")
        if t.lower().startswith("bot") and ":" in t:
            t = t[3:].strip()
        return t

    @classmethod
    async def test_connection(cls, bot_token: str) -> Dict[str, Any]:
        """Validates bot token by calling getMe"""
        bot_token = cls.clean_token(bot_token)
        if not bot_token:
            return {"success": False, "error": "Bot token is empty"}
        url = f"{cls.BASE_URL}{bot_token}/getMe"
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    try:
                        err_json = resp.json()
                        desc = err_json.get("description", f"Telegram API 返回错误 ({resp.status_code})")
                    except Exception:
                        desc = f"Telegram HTTP {resp.status_code}: 请检查 Bot Token 是否正确"
                    return {"success": False, "error": desc}
                data = resp.json()
                if data.get("ok"):
                    bot_user = data["result"]
                    return {
                        "success": True,
                        "bot_id": bot_user.get("id"),
                        "bot_name": bot_user.get("first_name"),
                        "username": bot_user.get("username")
                    }
                else:
                    return {"success": False, "error": data.get("description", "Unknown error")}
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def format_text(cls, text: Optional[str]) -> Optional[str]:
        """
        自动将常用的 Markdown 语法 (**粗体**, *斜体*, `代码`, [链接](url)) 转换为 Telegram 官方 HTML 格式。
        参考 SparkPost 最佳实践，避免 Telegram parse_mode 实体解析报错。
        """
        if not text:
            return text
        # 1. 粗体: **文本** -> <b>文本</b>
        text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)
        # 2. Markdown 链接: [文字](url) -> <a href="url">文字</a>
        text = re.sub(r'\[([^\]]+)\]\((https?://[^\)]+)\)', r'<a href="\2">\1</a>', text)
        # 3. 多行代码块: ```代码``` -> <pre>代码</pre>
        text = re.sub(r'\`\`\`([a-zA-Z]*)\n?(.*?)\`\`\`', r'<pre>\2</pre>', text, flags=re.DOTALL)
        # 4. 行内代码: `代码` -> <code>代码</code>
        text = re.sub(r'\`([^\`\n]+)\`', r'<code>\1</code>', text)
        # 5. 斜体: *文本* -> <i>文本</i> (排除以 * 开头的项目符号列表)
        text = re.sub(r'(?<![\*\w])\*([^\*\n\s][^\*\n]*?[^\*\n\s])\*(?![\*\w])', r'<i>\1</i>', text)
        return text

    @classmethod
    async def get_recent_updates(cls, bot_token: str) -> Dict[str, Any]:
        """
        通过 getUpdates?limit=50 自动侦测群里的消息和话题 (Topics)
        用户在各个 Topic 话题下发一条消息（例如打字 'test'），点击按钮即可自动识别其 thread_id！
        """
        bot_token = cls.clean_token(bot_token)
        if not bot_token:
            return {"success": False, "error": "Bot token 为空，请输入有效的 Telegram Bot Token"}
        url = f"{cls.BASE_URL}{bot_token}/getUpdates?limit=50"
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.get(url)
                if resp.status_code != 200:
                    try:
                        err_json = resp.json()
                        desc = err_json.get("description", f"Telegram API 返回错误 ({resp.status_code})")
                    except Exception:
                        desc = f"Telegram HTTP {resp.status_code}: 请检查 Bot Token 是否正确（勿包含多余空格或前缀）"
                    return {"success": False, "error": desc}

                try:
                    data = resp.json()
                except Exception:
                    return {"success": False, "error": "Telegram 返回了非 JSON 数据，请检查网络或 Bot Token"}

                if not data.get("ok"):
                    return {"success": False, "error": data.get("description", "Failed to get updates")}

                updates = data.get("result", [])
                detected_chats = {}
                detected_topics = {}

                for u in updates:
                    msg = u.get("message") or u.get("channel_post") or u.get("edited_message")
                    if not msg:
                        continue
                    chat = msg.get("chat", {})
                    cid = str(chat.get("id"))
                    cname = chat.get("title") or chat.get("username") or "Telegram Group"
                    if cid and cid != "None":
                        detected_chats[cid] = cname

                    thread_id = msg.get("message_thread_id")
                    reply_to = msg.get("reply_to_message") or {}
                    topic_info = msg.get("forum_topic_created") or msg.get("forum_topic_edited") or reply_to.get("forum_topic_created") or reply_to.get("forum_topic_edited") or {}
                    topic_name = topic_info.get("name")
                    text_snippet = msg.get("text") or msg.get("caption") or "[附件/事件]"

                    if thread_id:
                        str_tid = str(thread_id)
                        detected_topics[str_tid] = {
                            "thread_id": thread_id,
                            "chat_id": cid,
                            "chat_title": cname,
                            "topic_name": topic_name or f"话题 #{thread_id}",
                            "last_message": text_snippet[:60]
                        }

                return {
                    "success": True,
                    "detected_chats": [{"id": cid, "title": title} for cid, title in detected_chats.items()],
                    "detected_topics": list(detected_topics.values())
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    async def send_alert(
        cls,
        bot_token: str,
        chat_id: str,
        text: str,
        image_path: Optional[str] = None,
        buttons: Optional[List[List[Dict[str, str]]]] = None,
        thread_id: Optional[str] = None,
        parse_mode: str = "HTML",
        retry_count: int = 3
    ) -> Dict[str, Any]:
        """
        向 Telegram 发送消息或图片，内置：
        1. 自动 Markdown -> Telegram HTML 转换
        2. 429 智能限流自愈 (依据 retry_after 智能等待后重试)
        3. parse_mode 解析实体出错自动降级为纯文本重试
        """
        bot_token = cls.clean_token(bot_token)
        chat_id = str(chat_id).strip() if chat_id else ""
        if not bot_token or not chat_id:
            return {"success": False, "error": "Telegram Bot Token or Chat ID not configured"}

        # 格式化文本
        if parse_mode == "HTML" and text:
            text = cls.format_text(text)

        reply_markup = None
        if buttons:
            reply_markup = json.dumps({"inline_keyboard": buttons})

        async with httpx.AsyncClient(timeout=30.0) as client:
            for attempt in range(retry_count):
                try:
                    # In Telegram forum supergroups, # General is the root topic (omitting message_thread_id routes to # General)
                    clean_tid = str(thread_id).strip() if thread_id is not None else ""
                    use_tid = clean_tid if clean_tid and clean_tid not in ["0", "1"] else None

                    if image_path and os.path.exists(image_path):
                        url = f"{cls.BASE_URL}{bot_token}/sendPhoto"
                        data = {
                            "chat_id": chat_id,
                            "caption": text,
                            "parse_mode": parse_mode
                        }
                        if use_tid:
                            data["message_thread_id"] = use_tid
                        if reply_markup:
                            data["reply_markup"] = reply_markup

                        with open(image_path, "rb") as f:
                            files = {"photo": ("alert.png", f, "image/png")}
                            resp = await client.post(url, data=data, files=files)
                    else:
                        url = f"{cls.BASE_URL}{bot_token}/sendMessage"
                        payload = {
                            "chat_id": chat_id,
                            "text": text,
                            "parse_mode": parse_mode,
                            "disable_web_page_preview": False
                        }
                        if use_tid:
                            payload["message_thread_id"] = use_tid
                        if reply_markup:
                            payload["reply_markup"] = reply_markup

                        resp = await client.post(url, json=payload)

                    res_json = resp.json()
                    if res_json.get("ok"):
                        msg_id = str(res_json["result"]["message_id"])
                        return {"success": True, "message_id": msg_id, "result": res_json["result"]}

                    # 1. 遇到 429 限流自愈
                    err_desc = res_json.get("description", "")
                    if resp.status_code == 429 or "too many requests" in err_desc.lower():
                        retry_after = res_json.get("parameters", {}).get("retry_after", 2)
                        logger.warning(f"触发 Telegram 限流 (429)，等待 {retry_after} 秒后自动重试 (尝试 {attempt+1}/{retry_count})...")
                        await asyncio.sleep(retry_after + 0.5)
                        continue

                    # 2. 如果是 message thread not found，自动降级为 root/General topic 重试
                    if "message thread not found" in err_desc.lower():
                        logger.warning("Telegram message_thread_id 不存在，降级为默认/General 话题重试...")
                        use_tid = None
                        thread_id = None
                        continue

                    # 3. 如果是 parse_mode 报错，自动降级为纯文本重试
                    if "can't parse entities" in err_desc.lower():
                        logger.warning(f"Telegram HTML 解析实体失败，自动降级为纯文本重发...")
                        if image_path and os.path.exists(image_path):
                            data.pop("parse_mode", None)
                            with open(image_path, "rb") as f:
                                files = {"photo": ("alert.png", f, "image/png")}
                                retry_resp = await client.post(url, data=data, files=files)
                        else:
                            payload.pop("parse_mode", None)
                            retry_resp = await client.post(url, json=payload)

                        retry_json = retry_resp.json()
                        if retry_json.get("ok"):
                            return {"success": True, "message_id": str(retry_json["result"]["message_id"]), "result": retry_json["result"]}

                    # 其他错误直接返回
                    return {"success": False, "error": err_desc}

                except Exception as e:
                    if attempt == retry_count - 1:
                        return {"success": False, "error": str(e)}
                    await asyncio.sleep(1.0)

            return {"success": False, "error": "Exceeded retry limit"}
