import os
import hashlib
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

DAILY_QUESTIONS = [
    "Hvad er den vigtigste ting du kan gøre i dag?",
    "Hvem ville du ønske du ringede mere til?",
    "Hvad er du mest taknemlig for lige nu?",
    "Hvad ville fremtids-dig ønske, at du gjorde i dag?",
    "Hvad er én vane du gerne vil opbygge?",
    "Hvad gjorde dig glad i går?",
    "Hvad ville du gøre, hvis du ikke kunne fejle?",
    "Hvem har inspireret dig for nylig, og hvorfor?",
    "Hvad er én ting du har udskudt for længe?",
    "Hvad ville du råde dit yngre jeg?",
    "Hvad er du stolt af fra i går?",
    "Hvad er én ting du kan gøre i dag for din fremtid?",
    "Hvis du kun havde én time mere i dag, hvad ville du bruge den på?",
    "Hvad er én frygt du gerne vil overvinde?",
    "Hvad giver dig mest energi?",
    "Hvad er din største drøm lige nu?",
    "Hvad kan du lære af en fejl du lavede for nylig?",
    "Hvem i din omgangskreds fortjener mere af din tid?",
    "Hvad er én ting der altid gør dig glad?",
    "Hvad ville perfekt se ud for dig om 5 år?",
    "Hvad holder dig tilbage fra at nå dine mål?",
    "Hvad er den bedste investering du kan gøre i dig selv?",
    "Hvad har du lært denne uge?",
    "Hvad kan du forenkle i dit liv?",
    "Hvad er én kompliment du gerne vil give nogen i dag?",
    "Hvad er du nysgerrig på at lære mere om?",
    "Hvad er det smukkeste ved dit liv lige nu?",
    "Hvad ville du gøre anderledes, hvis du startede forfra?",
    "Hvad er én ting der fylder for meget i dit hoved?",
    "Hvad er din største styrke, og bruger du den nok?",
    "Hvad kan gøre denne uge ekstraordinær?",
    "Hvornår var du sidst virkelig til stede i nuet?",
    "Hvad er én ting du kan give slip på?",
    "Hvad inspirerer dig allermest?",
    "Hvad er den bedste beslutning du har truffet for nylig?",
    "Hvad vil du huske fra denne periode om 10 år?",
    "Hvad giver dit liv mest mening?",
    "Hvad er én ting du kan gøre i dag for Rikke?",
    "Hvad er én ting du kan gøre i dag for Aya?",
    "Hvad er du allermest nysgerrig på lige nu?",
    "Hvis ingen kunne dømme dig, hvad ville du så gøre?",
    "Hvad er én vane hos dig selv, du er stolt af?",
    "Hvad kan du gøre i dag for at have det bedre i morgen?",
    "Hvornår følte du dig sidst virkelig levende?",
    "Hvad er én grænse du har brug for at sætte?",
    "Hvad er den største forandring du ønsker at skabe?",
    "Hvad ville du gøre, hvis du vidste du ikke kunne mislykkes?",
    "Hvad er én ting du tager for givet?",
    "Hvad er dit mål for denne måned?",
    "Hvad er det første skridt mod noget du drømmer om?",
]


DATE_IDEAS = [
    ("Frilandsmuseet", ["sunny", "mild"], "Friluftsmuseum i Lyngby — perfekt til Aya", "15 min"),
    ("Blå Planet", ["any"], "Danmarks bedste akvarium", "35 min"),
    ("Zoologisk Have", ["any"], "Altid et hit med Aya", "30 min"),
    ("Bellevue Strand", ["hot", "sunny"], "Husk solcreme og badetøj", "20 min"),
    ("Dyrehaven", ["sunny", "mild"], "Imponerende hjorte og skov", "20 min"),
    ("Dyrehavsbakken", ["sunny", "mild"], "Verdens ældste forlystelsespark", "20 min"),
    ("Louisiana Museum", ["any"], "Verdensklasse kunst med havudsigt", "30 min"),
    ("Botanisk Have", ["sunny", "mild"], "Gratis og smukt midt i København", "30 min"),
    ("Experimentarium", ["any"], "Interaktivt science museum", "25 min"),
    ("Nationalmuseet", ["rainy", "any"], "Dansk historie fra vikinger til nu", "35 min"),
    ("Arken Museum", ["any"], "Moderne kunst ved Køge Bugt", "45 min"),
    ("Frederiksberg Have", ["sunny", "mild"], "Romantisk park med slotssø", "30 min"),
    ("Torvehallerne", ["rainy", "any"], "Frokost og marked på Israels Plads", "35 min"),
    ("Kronborg Slot", ["sunny", "mild"], "Hamlets slot i Helsingør", "35 min"),
    ("Humlebæk Strand", ["hot", "sunny"], "Hyggelig strandbad nord for Birkerød", "20 min"),
    ("Ordrupgaard", ["any"], "Impressionisme i smukke omgivelser", "20 min"),
    ("Bakken + Dyrehaven", ["mild", "sunny"], "Kombiner skov og forlystelser", "20 min"),
    ("Statens Museum for Kunst", ["rainy", "any"], "Gratis Danmarks nationalmuseum", "35 min"),
    ("Charlottenlund Fort Strand", ["hot", "sunny"], "Hyggelig strandbad tæt på", "15 min"),
    ("Nivå Havn", ["sunny", "mild"], "Idyllisk lille havn med is og udsigt", "15 min"),
]


def get_daily_question():
    idx = int(hashlib.md5(date.today().isoformat().encode()).hexdigest(), 16) % len(DAILY_QUESTIONS)
    return DAILY_QUESTIONS[idx]


def get_aya_uv_alert(uv_max):
    if uv_max >= 6:
        return f"🧴 Aya: solhat + SPF 50 nødvendigt · UV {uv_max}"
    if uv_max >= 3:
        return f"🧴 Aya: husk solhat og solcreme · UV {uv_max}"
    return None


def _is_danish_holiday(d):
    year = d.year
    # Påske (easter) beregning — anonym algoritme
    a = year % 19
    b = year // 100
    c = year % 100
    d_ = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d_ - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    from datetime import date as _date
    easter = _date(year, month, day)
    holidays = {
        easter,
        easter - timedelta(days=3),   # Skærtorsdag
        easter - timedelta(days=2),   # Langfredag
        easter + timedelta(days=1),   # 2. påskedag
        easter + timedelta(days=39),  # Kr. himmelfartsdag
        easter + timedelta(days=49),  # 1. pinsedag
        easter + timedelta(days=50),  # 2. pinsedag
        _date(year, 1, 1),   # Nytårsdag
        _date(year, 12, 24), # Juleaften
        _date(year, 12, 25), # 1. juledag
        _date(year, 12, 26), # 2. juledag
    }
    return d in holidays


def get_date_idea(code, temp):
    today = date.today()
    weekday = today.weekday()
    is_weekend = weekday >= 4  # fre=4, lør=5, søn=6
    if not is_weekend and not _is_danish_holiday(today):
        return None
    hot = temp >= 22
    sunny = code in (0, 1, 2) and temp >= 14
    rainy = code in (51, 53, 55, 61, 63, 65, 80, 81, 82)
    mild = 12 <= temp < 22
    matching = []
    for name, tags, desc, dist in DATE_IDEAS:
        if "any" in tags or \
           (hot and "hot" in tags) or \
           (sunny and "sunny" in tags) or \
           (rainy and "rainy" in tags) or \
           (mild and "mild" in tags):
            matching.append((name, desc, dist))
    if not matching:
        matching = [(n, d, di) for n, t, d, di in DATE_IDEAS if "any" in t]
    idx = int(hashlib.md5(today.isoformat().encode()).hexdigest(), 16) % len(matching)
    name, desc, dist = matching[idx]
    return f"📍 {name} ({dist}): {desc}"



def calculate_streak(tasks_service):
    today = date.today()
    lookback = today - timedelta(days=30)
    result = tasks_service.tasks().list(
        tasklist="@default",
        showCompleted=True,
        showHidden=True,
        completedMin=datetime(lookback.year, lookback.month, lookback.day, tzinfo=timezone.utc).isoformat(),
        completedMax=datetime(today.year, today.month, today.day, 23, 59, 59, tzinfo=timezone.utc).isoformat(),
    ).execute()
    completed_days = set()
    for t in result.get("items", []):
        if t.get("status") == "completed" and t.get("completed"):
            try:
                d = datetime.fromisoformat(t["completed"].replace("Z", "+00:00")).date()
                completed_days.add(d)
            except Exception:
                pass
    streak = 0
    for i in range(30):
        if (today - timedelta(days=i)) in completed_days:
            streak += 1
        else:
            break
    return streak


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

    return temp_7, temp_14, condition, hint, alerts, uv_max, code


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


def weather_tag(code):
    if code == 0:
        return "sunny"
    if code in (1, 2):
        return "partly_sunny"
    if code == 3:
        return "cloud"
    if code in (45, 48):
        return "fog"
    if code in (51, 53, 55, 56, 57):
        return "droplet"
    if code in (61, 63, 65, 66, 67, 80, 81, 82):
        return "umbrella"
    if code in (71, 73, 75, 77, 85, 86):
        return "snowflake"
    if code in (95, 96, 99):
        return "zap"
    return "sunny"


def send_notification(title, body, tag=None):
    topic = os.environ["NTFY_TOPIC"]
    data = {"topic": topic, "title": title, "message": body}
    if tag:
        data["tags"] = [tag]
    payload = json_module.dumps(data, ensure_ascii=False).encode("utf-8")
    requests.post(
        "https://ntfy.sh/",
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        timeout=10,
    )


def main():
    temp_7, temp_14, condition, hint, alerts, uv_max, code = get_weather()
    cal_service, tasks_service = build_services()
    event_lines = get_all_events(cal_service)
    task_lines = [f"☑ {t}" for t in get_tasks(tasks_service)]
    streak = calculate_streak(tasks_service)

    dst = get_dst_alert()
    if dst:
        alerts.append(dst)

    aya = get_aya_uv_alert(uv_max)
    if aya:
        alerts.append(aya)

    title = f"{temp_7}° {temp_14}° · {condition}"
    if hint:
        title += f" · {hint}"

    body_parts = alerts + event_lines + task_lines
    if streak > 0:
        body_parts.append(f"🔥 {streak} dages streak")

    date_idea = get_date_idea(code, temp_14)
    if date_idea:
        body_parts.append(date_idea)


    body_parts.append(f"💭 {get_daily_question()}")

    body = "\n".join(body_parts) if body_parts else "Ingen begivenheder i dag"

    send_notification(title, body, tag=weather_tag(code))
    print(f"Sendt: {title}\n{body}")


if __name__ == "__main__":
    main()
