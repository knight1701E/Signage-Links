"""Fetch MCS Group's own website news feed and write rssfeedlinks/mcs-news.json.

Runs hourly from GitHub Actions. Uses only the standard library.
"""
import html, json, re, sys, urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

FEED = "https://www.mcs-ltd.com/feed/"
OUT = "rssfeedlinks/mcs-news.json"
UA = {"User-Agent": "Mozilla/5.0 (KnightsoftSignage news fetch)"}
MAX_ITEMS = 8


def get(url):
    req = urllib.request.Request(url, headers=UA)
    with urllib.request.urlopen(req, timeout=30) as r:
        return r.read().decode("utf-8", "replace")


def text(s, limit=220):
    s = re.sub(r"<[^>]+>", " ", s or "")
    s = html.unescape(s)
    s = re.sub(r"The post .* appeared first on .*", "", s)
    s = re.sub(r"\s+", " ", s).replace("[…]", "").replace("[...]", "").strip()
    if len(s) > limit:
        s = s[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"
    return s


def og_image(url):
    try:
        page = get(url)
    except Exception:
        return ""
    m = re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)', page)
    return m.group(1) if m and m.group(1).startswith("https://") else ""


def main():
    root = ET.fromstring(get(FEED))
    items = []
    for it in root.iter("item"):
        title = html.unescape((it.findtext("title") or "").strip())
        link = (it.findtext("link") or "").strip()
        if not title or not link.startswith("https://"):
            continue
        try:
            d = parsedate_to_datetime(it.findtext("pubDate"))
            date = f"{d.day} {d:%B %Y}"
        except Exception:
            date = ""
        items.append({"title": title, "date": date,
                      "summary": text(it.findtext("description")),
                      "image": og_image(link)})
        if len(items) >= MAX_ITEMS:
            break
    if not items:
        print("No items found; keeping the previous file.")
        return 1
    data = {"source": "mcs-ltd.com", "items": items,
            # Daily heartbeat keeps the scheduled workflow alive (GitHub pauses idle schedules after 60 days).
            "checked": datetime.now(timezone.utc).strftime("%Y-%m-%d")}
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print(f"Wrote {len(items)} items")
    return 0


if __name__ == "__main__":
    sys.exit(main())
