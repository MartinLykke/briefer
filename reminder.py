import os
import json as json_module
import requests
from datetime import datetime, timezone, timedelta, date
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

CALENDAR_NAME = "Martin og Rikke fælles kalender"
REMINDER_WINDOW_MINUTES = 20


def build_service():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    return build("calendar", "v3", credentials=creds)


def get_upcoming_important_events(service):
    calendars = service.calendarList().list().execute()
    calendar_id = next(
        (c["id"] for c in calendars["items"] if c["summary"] == CALENDAR_NAME),
        "primary",
    )

    tz = timezone(timedelta(hours=2))
    now = datetime.now(tz)
    window_end = now + timedelta(minutes=REMINDER_WINDOW_MINUTES)

    today = date.today()
    day_start = datetime(today.year, today.month, today.day, 0, 0, 0, tzinfo=tz)
    day_end = datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=tz)

    result = service.events().list(
        calendarId=calendar_id,
        timeMin=day_start.isoformat(),
        timeMax=day_end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    reminders = []
    for e in result.get("items", []):
        summary = e.get("summary", "")
        if not summary.endswith("!"):
            continue

        start_val = e["start"].get("dateTime")
        if not start_val:
            continue

        event_time = datetime.fromisoformat(start_val)
        if now <= event_time <= window_end:
            display_name = summary.rstrip("!")
            reminders.append((event_time.strftime("%H:%M"), display_name))

    return reminders


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
    service = build_service()
    reminders = get_upcoming_important_events(service)

    if not reminders:
        print("Ingen påmindelser inden for de næste 20 minutter.")
        return

    for time_str, name in reminders:
        send_notification(f"Husk: {name}", f"Starter kl. {time_str}")
        print(f"Påmindelse sendt: {name} kl. {time_str}")


if __name__ == "__main__":
    main()
