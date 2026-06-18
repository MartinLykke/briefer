import os
import json as json_module
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

ANTHROPIC_RSS_URLS = [
    "https://www.anthropic.com/rss.xml",
    "https://www.anthropic.com/feed.xml",
    "https://www.anthropic.com/news/rss",
]


def fetch_anthropic_news():
    for url in ANTHROPIC_RSS_URLS:
        try:
            r = requests.get(url, timeout=10, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code == 200 and "<rss" in r.text:
                return parse_rss(r.text)
        except Exception:
            continue
    return []


def parse_rss(xml_text):
    root = ET.fromstring(xml_text)
    ns = {"atom": "http://www.w3.org/2005/Atom"}
    channel = root.find("channel")
    if channel is None:
        return []

    cutoff = datetime.now(timezone.utc) - timedelta(days=7)
    articles = []

    for item in channel.findall("item"):
        title = item.findtext("title", "").strip()
        pub_date = item.findtext("pubDate", "").strip()
        link = item.findtext("link", "").strip()

        try:
            from email.utils import parsedate_to_datetime
            dt = parsedate_to_datetime(pub_date)
            if dt < cutoff:
                continue
        except Exception:
            pass

        if title:
            articles.append(title)

    return articles


def send_notification(title, body):
    topic = os.environ["NTFY_TOPIC"]
    payload = json_module.dumps(
        {"topic": topic, "title": title, "message": body},
        ensure_ascii=False,
    ).encode("utf-8")
    requests.post(
        "https://ntfy.sh/",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=10,
    )


def main():
    articles = fetch_anthropic_news()

    if not articles:
        print("Ingen nye Anthropic-nyheder denne uge.")
        return

    body = "\n".join(f"• {a}" for a in articles)
    send_notification(f"Anthropic nyheder ({len(articles)})", body)
    print(f"Sendt {len(articles)} artikler:\n{body}")


if __name__ == "__main__":
    main()
