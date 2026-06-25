import random
import requests
import feedparser
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from .config import get_random_headers


class NewsFetcher:
    # Edgy, general‑interest feeds – mix of mainstream, satire, and niche
    FEED_POOL = [
        # Reddit – r/all (covers everything, often edgy)
        "https://www.reddit.com/r/all/.rss",
        # Specific subreddits for hot takes
        "https://www.reddit.com/r/worldnews/.rss",
        "https://www.reddit.com/r/politics/.rss",
        "https://www.reddit.com/r/technology/.rss",
        "https://www.reddit.com/r/nottheonion/.rss",  # weird but true
        "https://www.reddit.com/r/funny/.rss",
        # Satire / edgy humour
        "https://www.theonion.com/rss",
        "https://www.clickhole.com/rss",
        # General news with edge
        "https://www.vice.com/en/rss",
        "https://www.buzzfeednews.com/feed",
        "https://www.dailybeast.com/feed",
        "https://www.rollingstone.com/feed",
        # Tech culture
        "https://www.theverge.com/rss/index.xml",
        "https://www.wired.com/feed/rss",
        "https://techcrunch.com/feed/",
    ]

    def __init__(self, sources=None, num_sources=4):
        if sources is None:
            self.sources = random.sample(
                self.FEED_POOL, min(num_sources, len(self.FEED_POOL))
            )
        else:
            self.sources = sources

        self.blacklist_keywords = [
            "logo",
            "icon",
            "avatar",
            "small",
            "placeholder",
            "default",
            "rss",
            "feed",
            "xml",  # avoid some false positives
        ]

    def fetch_feed(self, url: str, limit: int = 3) -> list:
        try:
            headers = get_random_headers()
            feed = feedparser.parse(url, request_headers=headers)
            items = []
            for entry in feed.entries[:limit]:
                title = entry.get("title")
                link = entry.get("link")
                if not title or not link:
                    continue
                image_url = self._extract_image(entry, link)
                items.append({"title": title, "link": link, "image_url": image_url})
            return items
        except Exception as e:
            print(f"Error fetching RSS {url}: {e}")
            return []

    def _extract_image(self, entry, link) -> str | None:
        # (same logic as before – unchanged)
        if "media_content" in entry:
            for media in entry.media_content:
                url = media.get("url")
                if url and self._is_valid_image_url(url):
                    return url
        if "media_thumbnail" in entry:
            for thumb in entry.media_thumbnail:
                url = thumb.get("url")
                if url and self._is_valid_image_url(url):
                    return url
        if "enclosures" in entry:
            for enc in entry.enclosures:
                if enc.get("type", "").startswith("image"):
                    url = enc.get("href")
                    if url and self._is_valid_image_url(url):
                        return url
        content = entry.get("content", [{}])[0].get("value", "")
        if not content:
            content = entry.get("summary", "")
        if content:
            soup = BeautifulSoup(content, "html.parser")
            for img in soup.find_all("img"):
                src = img.get("src")
                if not src:
                    continue
                if img.get("srcset"):
                    parts = img["srcset"].split(",")
                    last = parts[-1].strip().split()[0]
                    if last and self._is_valid_image_url(last):
                        src = last
                if src and not src.startswith(("http://", "https://")):
                    src = urljoin(link, src)
                if src and self._is_valid_image_url(src):
                    return src
        if link:
            og_image = self._fetch_og_image(link)
            if og_image:
                return og_image
        if link:
            try:
                headers = get_random_headers()
                resp = requests.get(link, timeout=10, headers=headers)
                if resp.status_code == 200:
                    soup = BeautifulSoup(resp.text, "html.parser")
                    for img in soup.find_all("img"):
                        src = img.get("src")
                        if src and self._is_valid_image_url(src):
                            if not src.startswith(("http://", "https://")):
                                src = urljoin(link, src)
                            return src
            except Exception:
                pass
        return None

    def _is_valid_image_url(self, url: str) -> bool:
        if not url:
            return False
        url_lower = url.lower()
        if any(kw in url_lower for kw in self.blacklist_keywords):
            return False
        if any(ext in url_lower for ext in [".jpg", ".jpeg", ".png", ".webp", ".gif"]):
            return True
        if "images" in url_lower or "media" in url_lower:
            return True
        return True

    def _fetch_og_image(self, url: str) -> str | None:
        try:
            headers = get_random_headers()
            resp = requests.get(url, timeout=8, headers=headers)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                for prop in ["og:image", "twitter:image"]:
                    tag = soup.find("meta", property=prop) or soup.find(
                        "meta", attrs={"name": prop}
                    )
                    if tag and tag.get("content"):
                        img_url = tag["content"]
                        if self._is_valid_image_url(img_url):
                            return img_url
        except Exception:
            pass
        return None

    def get_market_news(self, limit: int = 6) -> list:
        # Renamed for clarity – it's just "get_news" now
        all_items = []
        for source in self.sources:
            items = self.fetch_feed(source, limit=limit // len(self.sources) + 2)
            all_items.extend(items)
            random.shuffle(all_items)
        return all_items[:limit]

    # ─── REMOVED get_crypto_prices ───

    def get_context(self, limit: int = 3) -> tuple:
        """
        Build the full context string and return it along with the raw news items.
        Returns: (context_string, news_items_list)
        """
        news_items = self.get_market_news(limit)  # rename in mind
        lines = ["Latest edgy news from around the web:\n"]
        for i, item in enumerate(news_items, 1):
            lines.append(f"[{i}] {item['title']} ({item['link']})")
        context = "\n".join(lines)
        # Debug print
        for item in news_items:
            print(f"[DEBUG] {item['title'][:50]}... image: {item['image_url']}")
        return context, news_items
