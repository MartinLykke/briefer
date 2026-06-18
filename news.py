import os
import json as json_module
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

NEWS_URL = "https://www.anthropic.com/news"


def fetch_anthropic_news():
    r = requests.get(NEWS_URL, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    cutoff = datetime.now() - timedelta(days=7)
    articles = []

    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.startswith("/news/"):
            continue

        texts = [p.get_text(strip=True) for p in a.find_all("p")]
        if len(texts) < 2:
            continue

        date_str = texts[0]
        title = texts[-1]

        try:
            pub_date = datetime.strptime(date_str, "%b %d, %Y")
            if pub_date < cutoff:
                continue
        except ValueError:
            pass

        if title and title not in [x[0] for x in articles]:
            articles.append((title, date_str))

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
