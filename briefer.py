import os
import json
import requests
from datetime import datetime, timezone, timedelta
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BIRKEROD_LAT = 55.851
BIRKEROD_LON = 12.431

# WMO weather code → dansk beskrivelse
WMO_CODES = {
    0: "Solrigt",
    1: "Mest klart", 2: "Delvist skyet", 3: "Overskyet",
    45: "Tåget", 48: "Rimtåge",
    51: "Let støvregn", 53: "Støvregn", 55: "Kraftig støvregn",
    61: "Let regn", 63: "Regn", 65: "Kraftig regn",
    71: "Let sne", 73: "Sne", 75: "Kraftig sne",
    80: "Byger", 81: "Kraftige byger", 82: "Voldsomme byger",
    95: "Tordenvejr", 96: "Tordenvejr med hagl", 99: "Kraftigt tordenvejr",
}


def get_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": BIRKEROD_LAT,
        "longitude": BIRKEROD_LON,
        "current": "temperature_2m,weathercode,windspeed_10m",
        "timezone": "Europe/Copenhagen",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()["current"]

    temp = round(data["temperature_2m"])
    code = data["weathercode"]
    wind = data["windspeed_10m"]

    condition = WMO_CODES.get(code, "Ukendt")

    # Override til "Blæsende" hvis vinden er kraftig og vejret ellers er fint
    if wind >= 10 and code in (0, 1, 2, 3):
        condition = "Blæsende"

    return temp, condition


CALENDAR_NAME = "Martin og Rikke fælles kalender"


def get_calendar_events():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())

    service = build("calendar", "v3", credentials=creds)

    calendars = service.calendarList().list().execute()
    calendar_id = next(
        (c["id"] for c in calendars["items"] if c["summary"] == CALENDAR_NAME),
        "primary",
    )

    tz = timezone(timedelta(hours=2))
    now = datetime.now(tz).replace(hour=0, minute=0, second=0, microsecond=0)
    end = now.replace(hour=23, minute=59, second=59)

    result = service.events().list(
        calendarId=calendar_id,
        timeMin=now.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()

    events = []
    for e in result.get("items", []):
        start = e["start"].get("dateTime", e["start"].get("date", ""))
        if "T" in start:
            time_str = datetime.fromisoformat(start).strftime("%H:%M")
        else:
            time_str = "Hele dagen"
        events.append(f"{time_str} {e['summary']}")

    return events


def send_notification(title, body):
    topic = os.environ["NTFY_TOPIC"]
    requests.post(
        f"https://ntfy.sh/{topic}",
        json={"topic": topic, "title": title, "message": body},
        timeout=10,
    )


def main():
    temp, condition = get_weather()
    events = get_calendar_events()

    title = f"{temp}° · {condition}"

    if events:
        body = "\n".join(events)
    else:
        body = "Ingen begivenheder i dag"

    send_notification(title, body)
    print(f"Sendt: {title}\n{body}")


if __name__ == "__main__":
    main()
