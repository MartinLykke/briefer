import os
import json as json_module
import requests
from datetime import datetime, timezone, timedelta, date
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

BIRKEROD_LAT = 55.851
BIRKEROD_LON = 12.431
CALENDAR_NAME = "Martin og Rikke fælles kalender"
EXCLUDED_EVENTS = {"R arbejde"}

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
        "hourly": "temperature_2m,weathercode,windspeed_10m",
        "timezone": "Europe/Copenhagen",
        "forecast_days": 1,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    hourly = r.json()["hourly"]

    times = hourly["time"]
    temps = hourly["temperature_2m"]
    codes = hourly["weathercode"]
    winds = hourly["windspeed_10m"]

    def pick_hour(h):
        suffix = f"T{h:02d}:00"
        idx = next((i for i, t in enumerate(times) if t.endswith(suffix)), 0)
        return idx

    idx_7 = pick_hour(7)
    idx_14 = pick_hour(14)

    temp_7 = round(temps[idx_7])
    temp_14 = round(temps[idx_14])
    code = codes[idx_7]
    wind = winds[idx_7]

    condition = WMO_CODES.get(code, "Ukendt")
    if wind >= 10 and code in (0, 1, 2, 3):
        condition = "Blæsende"

    hint = get_clothing_hint(temp_7, code, wind)
    return temp_7, temp_14, condition, hint


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


def fetch_events(service, calendar_id, day):
    tz = timezone(timedelta(hours=2))
    start = datetime(day.year, day.month, day.day, 0, 0, 0, tzinfo=tz)
    end = datetime(day.year, day.month, day.day, 23, 59, 59, tzinfo=tz)
    result = service.events().list(
        calendarId=calendar_id,
        timeMin=start.isoformat(),
        timeMax=end.isoformat(),
        singleEvents=True,
        orderBy="startTime",
    ).execute()
    events = []
    for e in result.get("items", []):
        summary = e.get("summary", "")
        if summary in EXCLUDED_EVENTS:
            continue
        display = summary.rstrip("!")
        start_val = e["start"].get("dateTime", e["start"].get("date", ""))
        time_str = datetime.fromisoformat(start_val).strftime("%H:%M") if "T" in start_val else "Hele dagen"
        events.append(f"{time_str} {display}")
    return events


def get_all_events(service):
    calendars = service.calendarList().list().execute()
    calendar_map = {c["summary"]: c["id"] for c in calendars["items"]}

    main_id = calendar_map.get(CALENDAR_NAME, "primary")

    birthday_id = next(
        (cid for name, cid in calendar_map.items()
         if "ødselsdage" in name or "irthday" in name.lower()),
        None,
    )

    today = date.today()
    weekday = today.weekday()  # 0=mandag, 6=søndag

    lines = []

    # Dagens begivenheder
    today_events = fetch_events(service, main_id, today)
    if today_events:
        lines += today_events

    # Fødselsdage i dag
    if birthday_id:
        birthdays = fetch_events(service, birthday_id, today)
        lines += [f"🎂 {e.split(' ', 1)[1]}" if ' ' in e else e for e in birthdays]

    # Mandag: vis hele ugen
    if weekday == 0:
        DAY_NAMES = ["Man", "Tir", "Ons", "Tor", "Fre", "Lør", "Søn"]
        lines.append("— Denne uge —")
        for i in range(1, 7):
            day = today + timedelta(days=i)
            day_events = fetch_events(service, main_id, day)
            for e in day_events:
                lines.append(f"{DAY_NAMES[day.weekday()]} {e}")

    # Øvrige hverdage: vis weekenden
    elif weekday < 5:
        days_to_sat = 5 - weekday
        saturday = today + timedelta(days=days_to_sat)
        sunday = saturday + timedelta(days=1)

        sat_events = fetch_events(service, main_id, saturday)
        sun_events = fetch_events(service, main_id, sunday)

        for e in sat_events:
            lines.append(f"Lør {e}")
        for e in sun_events:
            lines.append(f"Søn {e}")

    return lines


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
    temp_7, temp_14, condition, hint = get_weather()
    service = build_service()
    lines = get_all_events(service)

    title = f"{temp_7}° {temp_14}° · {condition}"
    if hint:
        title += f" · {hint}"

    body = "\n".join(lines) if lines else "Ingen begivenheder i dag"

    send_notification(title, body)
    print(f"Sendt: {title}\n{body}")


if __name__ == "__main__":
    main()
