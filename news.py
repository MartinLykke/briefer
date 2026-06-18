import os
import json as json_module
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta

SITEMAP_URL = "https://www.anthropic.com/sitemap.xml"


def fetch_anthropic_news():
    r = requests.get(SITEMAP_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()

    root = ET.fromstring(r.text)
    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    cutoff = datetime.now(timezone.utc) - timedelta(days=7)

    articles = []
    for url in root.findall("sm:url", ns):
        loc = url.findtext("sm:loc", "", ns)
        lastmod = url.findtext("sm:lastmod", "", ns)
        if "/news/" not in loc or not lastmod:
            continue
        try:
            dt = datetime.fromisoformat(lastmod.replace("Z", "+00:00"))
            if dt < cutoff:
                continue
        except ValueError:
            continue

        slug = loc.rstrip("/").split("/news/")[-1]
        title = slug.replace("-", " ").title()
        articles.append((title, dt.strftime("%d/%m")))

    articles.sort(key=lambda x: x[1], reverse=True)
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

    body = "\n".join(f"• {title} ({date})" for title, date in articles)
    send_notification(f"Anthropic nyheder ({len(articles)})", body)
    print(f"Sendt {len(articles)} artikler:\n{body}")


if __name__ == "__main__":
    main()
