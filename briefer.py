import os
import json as json_module
import requests
from calendar import monthrange
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


def get_clothing_hint(temp, code, wind, uv_max):
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
    if uv_max >= 11:
        return f"UV ekstrem ({uv_max}) · Hold huden tildækket"
    if uv_max >= 8:
        return f"Solcreme nødvendigt · UV meget høj ({uv_max})"
    if uv_max >= 6:
        return f"Husk solcreme · UV høj ({uv_max})"
    if uv_max >= 3:
        return f"SPF 30 anbefales · UV moderat ({uv_max})"
    return None


def get_weather_alerts(times, temps, winds, precips):
    alerts = []
    now_hour = datetime.now().hour

    def hour_of(t):
        return int(t.split("T")[1].split(":")[0])

    # Regnvarsel: første time med nedbør efter nu
    for i, t in enumerate(times):
        h = hour_of(t)
        if h <= now_hour:
            continue
        if precips[i] >= 0.2:
            alerts.append(f"🌧 Regn fra kl. {h}")
            break

    # Kraftig regn
    if max(precips) >= 3:
        alerts.append(f"⛈ Kraftig regn i dag (op til {max(precips):.0f} mm/t)")

    # Varmevarsel
    max_temp = max(temps)
    if max_temp >= 27:
        alerts.append(f"🌡 Varmt i dag — op til {round(max_temp)}°")

    # Frostvarsel i nat (kl. 18-23)
    night_temps = [temps[i] for i, t in enumerate(times) if hour_of(t) >= 18]
    if night_temps and min(night_temps) < 0:
        alerts.append(f"❄ Frost i nat ({round(min(night_temps))}°)")

    # Kraftig vind
    max_wind = max(winds)
    if max_wind >= 15:
        alerts.append(f"💨 Kraftig vind (op til {round(max_wind)} m/s)")

    return alerts


def last_sunday_of(year, month):
    last_day = monthrange(year, month)[1]
    d = date(year, month, last_day)
    while d.weekday() != 6:
        d -= timedelta(days=1)
    return d


def get_dst_alert():
    tomorrow = date.today() + timedelta(days=1)
    year = tomorrow.year
    summer_time = last_sunday_of(year, 3)
    winter_time = last_sunday_of(year, 10)
    if tomorrow == summer_time:
        return "⏰ I morgen skifter vi til sommertid — flyt uret 1 time frem"
    if tomorrow == winter_time:
        return "⏰ I morgen skifter vi til vintertid — flyt uret 1 time tilbage"
    return None


def get_weather():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": BIRKEROD_LAT,
        "longitude": BIRKEROD_LON,
        "hourly": "temperature_2m,weathercode,windspeed_10m,uv_index,precipitation",
        "wind_speed_unit": "ms",
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
    uvs = hourly["uv_index"]
    precips = hourly["precipitation"]

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
    uv_max = round(max(uvs))

    condition = WMO_CODES.get(code, "Ukendt")
    if wind >= 10 and code in (0, 1, 2, 3):
        condition = "Blæsende"

    hint = get_clothing_hint(temp_7, code, wind, uv_max)
    alerts = get_weather_alerts(times, temps, winds, precips)

    return temp_7, temp_14, condition, hint, alerts


def build_services():
    creds = Credentials(
        token=None,
        refresh_token=os.environ["GOOGLE_REFRESH_TOKEN"],
        client_id=os.environ["GOOGLE_CLIENT_ID"],
        client_secret=os.environ["GOOGLE_CLIENT_SECRET"],
        token_uri="https://oauth2.googleapis.com/token",
    )
    creds.refresh(Request())
    cal = build("calendar", "v3", credentials=creds)
    tasks = build("tasks", "v1", credentials=creds)
    return cal, tasks


def get_tasks(tasks_service):
    today = date.today().isoformat() + "T23:59:59Z"
    result = tasks_service.tasks().list(
        tasklist="@default",
        dueMax=today,
        showCompleted=False,
        showHidden=False,
    ).execute()
    return [t["title"] for t in result.get("items", []) if t.get("title")]


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
        if "T" in start_val:
            dt = datetime.fromisoformat(start_val)
            time_str = str(dt.hour) if dt.minute == 0 else dt.strftime("%H:%M")
        else:
            time_str = "Heldags"
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
    weekday = today.weekday()

    lines = []

    today_events = fetch_events(service, main_id, today)
    if today_events:
        lines += today_events

    if birthday_id:
        birthdays = fetch_events(service, birthday_id, today)
        lines += [f"🎂 {e.split(' ', 1)[1]}" if ' ' in e else e for e in birthdays]

    if weekday == 0:
        DAY_NAMES = ["Man", "Tir", "Ons", "Tor", "Fre", "Lør", "Søn"]
        lines.append("— Denne uge —")
        for i in range(1, 7):
            day = today + timedelta(days=i)
            day_events = fetch_events(service, main_id, day)
            for e in day_events:
                lines.append(f"{DAY_NAMES[day.weekday()]} {e}")

    elif weekday < 5:
        days_to_sat = 5 - weekday
        saturday = today + timedelta(days=days_to_sat)
        sunday = saturday + timedelta(days=1)
        for e in fetch_events(service, main_id, saturday):
            lines.append(f"Lør {e}")
        for e in fetch_events(service, main_id, sunday):
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
    temp_7, temp_14, condition, hint, alerts = get_weather()
    cal_service, tasks_service = build_services()
    event_lines = get_all_events(cal_service)
    task_lines = [f"☑ {t}" for t in get_tasks(tasks_service)]

    dst = get_dst_alert()
    if dst:
        alerts.append(dst)

    title = f"{temp_7}° {temp_14}° · {condition}"
    if hint:
        title += f" · {hint}"

    body_parts = alerts + event_lines + task_lines
    body = "\n".join(body_parts) if body_parts else "Ingen begivenheder i dag"

    send_notification(title, body)
    print(f"Sendt: {title}\n{body}")


if __name__ == "__main__":
    main()
