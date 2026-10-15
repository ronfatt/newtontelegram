import re
import time
import hashlib
import asyncio
import httpx
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional

NEWS_FEEDS = [
    {
        "name": "Cointelegraph",
        "url": "https://cointelegraph.com/rss",
        "weight": 1
    },
    {
        "name": "Decrypt",
        "url": "https://decrypt.co/feed",
        "weight": 2
    },
    {
        "name": "Google News Crypto",
        "url": "https://news.google.com/rss/search?q=blockchain+crypto+bitcoin+web3&hl=en-US&gl=US&ceid=US:en",
        "weight": 3
    }
]

def clean_html(raw_html: str) -> str:
    if not raw_html:
        return ""
    clean = re.sub(r'<[^>]+>', '', raw_html)
    clean = re.sub(r'&nbsp;', ' ', clean)
    clean = re.sub(r'&amp;', '&', clean)
    clean = re.sub(r'&quot;', '"', clean)
    clean = re.sub(r'&#39;', "'", clean)
    return clean.strip()

class GlobalNewsTracker:
    def __init__(self):
        self.seen_guids = set()

    async def fetch_feed(self, client: httpx.AsyncClient, feed_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
        results = []
        name = feed_meta["name"]
        url = feed_meta["url"]
        try:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10.0)
            if resp.status_code == 200:
                root = ET.fromstring(resp.content)
                channel = root.find("channel")
                if channel is not None:
                    items = channel.findall("item")
                    for it in items[:15]:
                        title_el = it.find("title")
                        link_el = it.find("link")
                        desc_el = it.find("description")
                        date_el = it.find("pubDate")
                        guid_el = it.find("guid")

                        title = title_el.text if title_el is not None else ""
                        link = link_el.text if link_el is not None else ""
                        desc = clean_html(desc_el.text if desc_el is not None else "")
                        pub_date = date_el.text if date_el is not None else ""
                        guid = guid_el.text if guid_el is not None else link

                        if not title or not link:
                            continue

                        news_id = hashlib.md5((guid or link).encode()).hexdigest()

                        results.append({
                            "news_id": news_id,
                            "news_title": title.strip(),
                            "news_url": link.strip(),
                            "news_summary": desc[:160] + "..." if len(desc) > 160 else desc,
                            "news_time": pub_date,
                            "news_source": name
                        })
        except Exception as e:
            print(f"[NewsTracker] Fetch error for {name}: {e}")
        return results

    async def get_latest_news(self, limit: int = 15) -> List[Dict[str, Any]]:
        all_news = []
        async with httpx.AsyncClient(timeout=12.0) as client:
            tasks = [self.fetch_feed(client, f) for f in NEWS_FEEDS]
            feed_results = await asyncio.gather(*tasks, return_exceptions=True)
            for res in feed_results:
                if isinstance(res, list):
                    all_news.extend(res)

        # Deduplicate
        unique_news = []
        seen_titles = set()
        for n in all_news:
            t_key = n["news_title"].lower()[:40]
            if t_key not in seen_titles:
                seen_titles.add(t_key)
                unique_news.append(n)

        return unique_news[:limit]

global_news_tracker = GlobalNewsTracker()
