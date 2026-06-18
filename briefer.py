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


def get_clothing_hint(temp, code, wind):
    if code in (71, 73, 75):
        return "Husk varmt tøj og gode støvler"
    if code in (95, 96, 99):
        return "Bliv indendørs hvis muligt"
    if code in (51, 53, 55, 61, 63, 65, 80, 81, 82):
        return "Husk paraply"
    if temp <= 0:
        return "Klæd dig godt på — frostvejr"
    if temp <= 8:
        return "Tag en varm jakke på"
    if temp <= 14:
        return "Tag en jakke på"
    if wind >= 10:
        return "Tag en vindjakke på"
    if temp >= 24:
        return "Husk solcreme"
    return None


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

    if wind >= 10 and code in (0, 1, 2, 3):
        condition = "Blæsende"

    hint = get_clothing_hint(temp, code, wind)
    return temp, condition, hint


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
    print("Tilgængelige kalendere:", [c["summary"] for c in calendars["items"]])
    calendar_id = next(
        (c["id"] for c in calendars["items"] if c["summary"] == CALENDAR_NAME),
        "primary",
    )
    print(f"Bruger kalender: {calendar_id}")

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
        if e.get("summary") == "R arbejde":
            continue
        start = e["start"].get("dateTime", e["start"].get("date", ""))
        if "T" in start:
            time_str = datetime.fromisoformat(start).strftime("%H:%M")
        else:
            time_str = "Hele dagen"
        events.append(f"{time_str} {e['summary']}")

    return events


def send_notification(weather_line, events_body):
    topic = os.environ["NTFY_TOPIC"]
    requests.post(
        f"https://ntfy.sh/{topic}",
        data=events_body.encode("utf-8"),
        headers={
            "Title": weather_line,
            "Content-Type": "text/plain; charset=utf-8",
        },
        timeout=10,
    )


def main():
    temp, condition, hint = get_weather()
    events = get_calendar_events()

    weather_line = f"{temp}° · {condition}"
    if hint:
        weather_line += f" · {hint}"

    if events:
        events_body = "\n".join(events)
    else:
        events_body = "Ingen begivenheder i dag"

    send_notification(weather_line, events_body)
    print(f"Sendt: {weather_line}\n{events_body}")


if __name__ == "__main__":
    main()
