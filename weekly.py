import os
import json as json_module
import requests
from datetime import date, datetime, timedelta, timezone
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build


def build_tasks_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return build("tasks", "v1", credentials=creds)


def get_completed_tasks(tasks_service):
    today = date.today()
    monday = today - timedelta(days=today.weekday())
    completed_min = datetime(monday.year, monday.month, monday.day, 0, 0, 0, tzinfo=timezone.utc).isoformat()
    completed_max = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc).isoformat()

    result = tasks_service.tasks().list(
        tasklist="@default",
        showCompleted=True,
        showHidden=True,
        completedMin=completed_min,
        completedMax=completed_max,
    ).execute()

    return [t["title"] for t in result.get("items", []) if t.get("status") == "completed" and t.get("title")]


def motivational_message(count):
    if count == 0:
        return "0 opgaver løst denne uge 😅\nIngen stress — næste uge er en ny chance. Du kan gøre det!"
    if count == 1:
        return "1 opgave løst ✅\nDu kom i gang — det er det vigtigste!"
    if count <= 3:
        return f"{count} opgaver løst 💪\nGodt arbejde! Du holder momentum — fortsæt sådan!"
    if count <= 5:
        return f"{count} opgaver løst 🚀✨\nFlot indsats! Du er på rette spor og leverer resultater!"
    if count <= 7:
        return f"{count} opgaver løst 🔥⭐\nImponerende uge! Du er i topform — hold det niveau!"
    if count <= 10:
        return f"{count} opgaver løst 🏆💎\nEkstraordinær præstation! Du er en produktivitetsmaskine!"
    return f"{count} opgaver løst! 🔥🏆🎯🌟\nLEGENDARISK uge — ingenting kan stoppe dig!"


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
    tasks_service = build_tasks_service()
    completed = get_completed_tasks(tasks_service)
    count = len(completed)

    title = f"Ugens opsummering — {count} opgaver løst"
    body = motivational_message(count)
    if completed:
        body += "\n\n" + "\n".join(f"✓ {t}" for t in completed)

    send_notification(title, body)
    print(f"Sendt: {title}\n{body}")


if __name__ == "__main__":
    main()
