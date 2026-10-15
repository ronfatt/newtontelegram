import os
import re
from typing import Optional, Dict, Any
from requests_oauthlib import OAuth1Session

class TwitterPublisher:
    UPLOAD_URL = "https://upload.twitter.com/1.1/media/upload.json"
    TWEET_URL = "https://api.twitter.com/2/tweets"
    ME_URL = "https://api.twitter.com/2/users/me"

    @classmethod
    def test_connection(
        cls,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_token_secret: str
    ) -> Dict[str, Any]:
        """Validates credentials by fetching the authenticated Twitter user profile"""
        if not (api_key and api_secret and access_token and access_token_secret):
            return {"success": False, "error": "Twitter API credentials incomplete"}

        try:
            oauth = OAuth1Session(
                api_key,
                client_secret=api_secret,
                resource_owner_key=access_token,
                resource_owner_secret=access_token_secret
            )
            resp = oauth.get(cls.ME_URL, timeout=15)
            if resp.status_code == 200:
                user_data = resp.json().get("data", {})
                return {
                    "success": True,
                    "user_id": user_data.get("id"),
                    "name": user_data.get("name"),
                    "username": user_data.get("username")
                }
            else:
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": resp.text
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    def clean_html_for_tweet(cls, text: str) -> str:
        """Strips HTML tags like <b>, <a> and converts them to plain text for Twitter"""
        # Convert <a href='URL'>TEXT</a> to TEXT (URL)
        text = re.sub(r'<a\s+(?:[^>]*?\s+)?href=["\'](.*?)["\'][^>]*>(.*?)</a>', r'\2: \1', text)
        # Strip all other HTML tags
        clean = re.sub(r'<[^>]+>', '', text)
        return clean.strip()

    @classmethod
    def twitter_weight(cls, s: str) -> int:
        """Calculates Twitter weighted length: URLs=23, CJK/Emoji=2, ASCII=1"""
        s_no_url = re.sub(r'https?://\S+', 'U' * 23, s)
        weight = 0
        for ch in s_no_url:
            code = ord(ch)
            if code <= 4351 or (8192 <= code <= 8205):
                weight += 1
            else:
                weight += 2
        return weight

    @classmethod
    def truncate_tweet(cls, text: str, max_weight: int = 250) -> str:
        """Ensures the tweet fits within Twitter's 280-weighted-limit (safe margin: 250)"""
        if cls.twitter_weight(text) <= max_weight:
            return text

        lines = text.split("\n")
        selected = []
        current_w = 0
        for line in lines:
            line_w = cls.twitter_weight(line) + 1
            if current_w + line_w > max_weight - 20:
                # Add partial or ellipsis
                remaining = max_weight - current_w - 6
                if remaining > 15:
                    part = ""
                    for ch in line:
                        ch_w = 1 if ord(ch) <= 4351 else 2
                        if cls.twitter_weight(part) + ch_w > remaining:
                            break
                        part += ch
                    selected.append(part.rstrip() + "...")
                break
            selected.append(line)
            current_w += line_w

        res = "\n".join(selected).strip()
        if not res:
            res = text[:100] + "..."
        return res

    @classmethod
    def post_tweet(
        cls,
        api_key: str,
        api_secret: str,
        access_token: str,
        access_token_secret: str,
        text: str,
        image_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Uploads optional media and posts a tweet via Twitter API v2.
        """
        if not (api_key and api_secret and access_token and access_token_secret):
            return {"success": False, "error": "Twitter API credentials missing"}

        try:
            oauth = OAuth1Session(
                api_key,
                client_secret=api_secret,
                resource_owner_key=access_token,
                resource_owner_secret=access_token_secret
            )

            media_id = None
            if image_path and os.path.exists(image_path):
                # 1. Upload media
                with open(image_path, "rb") as img_file:
                    upload_resp = oauth.post(
                        cls.UPLOAD_URL,
                        files={"media": img_file},
                        timeout=30
                    )
                if upload_resp.status_code in [200, 201, 202]:
                    media_id = upload_resp.json().get("media_id_string")
                else:
                    print(f"[Twitter] Media upload failed ({upload_resp.status_code}): {upload_resp.text}")

            # 2. Format tweet text
            tweet_text = cls.clean_html_for_tweet(text)
            tweet_text = cls.truncate_tweet(tweet_text)

            payload: Dict[str, Any] = {"text": tweet_text}
            if media_id:
                payload["media"] = {"media_ids": [media_id]}

            # 3. Create Tweet
            resp = oauth.post(
                cls.TWEET_URL,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=20
            )

            if resp.status_code in [200, 201]:
                res_data = resp.json().get("data", {})
                tweet_id = res_data.get("id")
                return {
                    "success": True,
                    "tweet_id": tweet_id,
                    "tweet_url": f"https://x.com/i/web/status/{tweet_id}" if tweet_id else ""
                }
            else:
                err_text = resp.text
                if "oauth1-permissions" in err_text or "not configured with the appropriate oauth1 app permissions" in err_text:
                    err_text = (
                        "权限不足(403)：当前 Twitter App 缺少写入权限。\n"
                        "【解决步骤】\n"
                        "1. 打开 https://developer.x.com 进入 App 设置\n"
                        "2. 在 [User authentication settings] 中将 App permissions 修改为【Read and write】并保存\n"
                        "3. ⚠️ 最关键一步：进入 [Keys and tokens] 页面，对【Access Token and Secret】点击【Regenerate】重新生成！\n"
                        "4. 将新生成的 Access Token 和 Secret 填入控制台保存即可发帖。"
                    )
                return {
                    "success": False,
                    "status_code": resp.status_code,
                    "error": err_text
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    @classmethod
    async def post_with_config(cls, text: str, image_path: Optional[str] = None):
        """Auto loads credentials from database and posts tweet"""
        from database import get_app_config
        cfg = await get_app_config()
        tw = cfg.twitter
        res = cls.post_tweet(
            api_key=tw.api_key,
            api_secret=tw.api_secret,
            access_token=tw.access_token,
            access_token_secret=tw.access_token_secret,
            text=text,
            image_path=image_path
        )
        return res.get("success", False), res.get("tweet_id"), res.get("error")
