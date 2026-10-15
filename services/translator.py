import httpx
import urllib.parse
from typing import Dict, List, Optional
import asyncio
import logging

logger = logging.getLogger(__name__)

# Supported national languages for Telegram multi-language supergroup
SUPPORTED_LANGUAGES = {
    "en": {"name": "English", "native": "English", "flag": "🇬🇧", "default_thread_id": 16},
    "zh": {"name": "Chinese", "native": "简体中文", "flag": "🇨🇳", "default_thread_id": 17},
    "ko": {"name": "Korean", "native": "한국어", "flag": "🇰🇷", "default_thread_id": 18},
    "vi": {"name": "Vietnamese", "native": "Tiếng Việt", "flag": "🇻🇳", "default_thread_id": 19},
    "ja": {"name": "Japanese", "native": "日本語", "flag": "🇯🇵", "default_thread_id": 16},
    "th": {"name": "Thai", "native": "ภาษาไทย", "flag": "🇹🇭", "default_thread_id": 16},
    "id": {"name": "Indonesian", "native": "Bahasa Indonesia", "flag": "🇮🇩", "default_thread_id": 16},
    "ms": {"name": "Malay", "native": "Bahasa Melayu", "flag": "🇲🇾", "default_thread_id": 16},
    "es": {"name": "Spanish", "native": "Español", "flag": "🇪🇸", "default_thread_id": 16},
    "pt": {"name": "Portuguese", "native": "Português", "flag": "🇧🇷", "default_thread_id": 16},
    "ar": {"name": "Arabic", "native": "العربية", "flag": "🇸🇦", "default_thread_id": 16},
}

LANG_MAP = {
    "zh": "zh-CN",
    "ms": "ms",
    "id": "id",
    "vi": "vi",
    "th": "th",
    "ja": "ja",
    "ko": "ko",
    "ar": "ar",
    "pt": "pt",
    "es": "es",
    "en": "en"
}

MYMEMORY_LANG_MAP = {
    "zh": "zh-CN",
    "ms": "ms-MY",
    "id": "id-ID",
    "vi": "vi-VN",
    "th": "th-TH",
    "ja": "ja-JP",
    "ko": "ko-KR",
    "ar": "ar-SA",
    "pt": "pt-PT",
    "es": "es-ES",
    "en": "en-GB"
}

async def _translate_mymemory(text: str, target_lang: str) -> str:
    """MyMemory 备用翻译引擎 (参考 SparkPost，网络波动或 Google 被拦截时自动降级生效)"""
    tl = MYMEMORY_LANG_MAP.get(target_lang, target_lang)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    }
    url = "https://api.mymemory.translated.net/get"
    try:
        if len(text) <= 500:
            params = {"q": text, "langpair": f"zh-CN|{tl}"}
            async with httpx.AsyncClient(timeout=8.0, headers=headers) as client:
                resp = await client.get(url, params=params)
                if resp.status_code == 200:
                    t = resp.json().get("responseData", {}).get("translatedText")
                    if t and t.strip():
                        return t
        else:
            lines = text.split("\n")
            translated_lines = []
            async with httpx.AsyncClient(timeout=10.0, headers=headers) as client:
                for line in lines:
                    if not line.strip():
                        translated_lines.append("")
                        continue
                    params = {"q": line, "langpair": f"zh-CN|{tl}"}
                    resp = await client.get(url, params=params)
                    if resp.status_code == 200:
                        t = resp.json().get("responseData", {}).get("translatedText")
                        translated_lines.append(t if t else line)
                    else:
                        translated_lines.append(line)
            return "\n".join(translated_lines)
    except Exception as e:
        logger.warning(f"MyMemory fallback translate error: {e}")
    return text

async def translate_single_text(text: str, target_lang: str, timeout: float = 8.0) -> str:
    """
    Translates text to a single target language using Google's public translation endpoint,
    with automatic MyMemory fallback.
    """
    if not text or not text.strip():
        return ""

    # Check if target is Chinese and text is already predominantly Chinese
    is_chinese = any('\u4e00' <= char <= '\u9fff' for char in text[:100])
    if target_lang == "zh" and is_chinese:
        return text

    tl = LANG_MAP.get(target_lang, target_lang)
    try:
        url = (
            f"https://translate.googleapis.com/translate_a/single"
            f"?client=gtx&sl=auto&tl={tl}&dt=t&q={urllib.parse.quote(text)}"
        )
        async with httpx.AsyncClient(timeout=timeout) as client:
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "*/*",
                "Accept-Language": "en-US,en;q=0.9,zh-CN;q=0.8"
            }
            res = await client.get(url, headers=headers)
            if res.status_code == 200:
                data = res.json()
                if data and len(data) > 0 and isinstance(data[0], list):
                    translated = "".join(chunk[0] for chunk in data[0] if chunk and chunk[0])
                    if translated and translated.strip():
                        return translated
    except Exception as e:
        logger.warning(f"[Translator] Google Translate failed for {target_lang}: {e}, falling back to MyMemory...")

    # Fallback to MyMemory
    return await _translate_mymemory(text, target_lang)

async def translate_to_all_languages(text: str, target_langs: Optional[List[str]] = None) -> Dict[str, str]:
    """
    Translates text concurrently to all 11 target languages with semaphore flow control.
    """
    if target_langs is None:
        target_langs = list(SUPPORTED_LANGUAGES.keys())

    sem = asyncio.Semaphore(3)

    async def _worker(lang: str):
        async with sem:
            await asyncio.sleep(0.05)
            translated = await translate_single_text(text, lang)
            return lang, translated

    tasks = [_worker(lang) for lang in target_langs]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    translated_dict = {}
    for res in results:
        if isinstance(res, tuple):
            lang, trans_text = res
            translated_dict[lang] = trans_text
        else:
            logger.error(f"[Translator] Worker failed: {res}")

    return translated_dict
