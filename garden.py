import os
import json as json_module
import requests
from datetime import date, datetime, timezone, timedelta
from calendar import monthrange

BIRKEROD_LAT = 55.851
BIRKEROD_LON = 12.431

GARDEN_TASKS = [
    {
        "name": "Græsseeding",
        "months": [4, 5, 6, 7, 8, 9],
        "temp_min": 10,
        "temp_max": 20,
        "needs_dry": True,
        "precip_threshold": 0.5,
        "description": "Ideel temperatur og fugt til græsfrø",
        "emoji": "🌱"
    },
    {
        "name": "Græsklipning",
        "months": [4, 5, 6, 7, 8, 9, 10],
        "temp_min": 10,
        "temp_max": 30,
        "needs_dry": True,
        "precip_threshold": 1.0,
        "description": "Tørt vejr gør klipning nemmere",
        "emoji": "✂️"
    },
    {
        "name": "Basilikum-planting",
        "months": [5, 6, 7],
        "temp_min": 15,
        "temp_max": 25,
        "needs_dry": True,
        "precip_threshold": 0.5,
        "description": "Efter sidste frost, når varmt og tørt",
        "emoji": "🌿"
    },
    {
        "name": "Basilikum-stell",
        "months": [5, 6, 7, 8, 9],
        "temp_min": 12,
        "temp_max": 30,
        "needs_dry": False,
        "precip_threshold": 2.0,
        "description": "Vand hvis ingen regn i 2-3 dage",
        "emoji": "💧"
    },
    {
        "name": "Grøntsager sæd",
        "months": [4, 5, 6, 7],
        "temp_min": 10,
        "temp_max": 22,
        "needs_dry": True,
        "precip_threshold": 0.5,
        "description": "Tørt, varm jord for spirekraft",
        "emoji": "🥬"
    },
    {
        "name": "Blomster-planting",
        "months": [5, 6, 7, 8],
        "temp_min": 12,
        "temp_max": 25,
        "needs_dry": True,
        "precip_threshold": 0.5,
        "description": "Efter sidste frost, etablering uden stress",
        "emoji": "🌻"
    }
]

CRITICAL_ALERTS = {
    "frost": {"temp_threshold": 2, "icon": "❄️"},
    "heat": {"temp_threshold": 27, "icon": "🌡️"},
    "drought": {"days_no_rain": 3, "icon": "🏜️"},
    "heavy_rain": {"precip_mm": 10, "icon": "⛈️"}
}


def get_weather_forecast():
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": BIRKEROD_LAT,
        "longitude": BIRKEROD_LON,
        "daily": "temperature_2m_max,temperature_2m_min,weathercode,precipitation_sum",
        "timezone": "Europe/Copenhagen",
        "forecast_days": 7,
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()["daily"]


def is_task_viable(task, temp_max, temp_min, precip):
    month = date.today().month

    if month not in task["months"]:
        return False

    if not (task["temp_min"] <= temp_max <= task["temp_max"]):
        return False

    if task["needs_dry"] and precip > task["precip_threshold"]:
        return False

    return True


def get_recommended_tasks(forecast):
    today_idx = 0
    temps_max = forecast["temperature_2m_max"]
    temps_min = forecast["temperature_2m_min"]
    precips = forecast["precipitation_sum"]

    recommended = []

    for task in GARDEN_TASKS:
        temp_max = temps_max[today_idx]
        temp_min = temps_min[today_idx]
        precip = precips[today_idx]

        if is_task_viable(task, temp_max, temp_min, precip):
            recommended.append({
                "emoji": task["emoji"],
                "name": task["name"],
                "reason": task["description"],
                "temp": f"{int(temp_min)}°-{int(temp_max)}°C"
            })

    return recommended


def get_critical_alerts(forecast):
    temps_max = forecast["temperature_2m_max"]
    temps_min = forecast["temperature_2m_min"]
    precips = forecast["precipitation_sum"]

    alerts = []

    for i in range(min(3, len(temps_min))):
        temp_min = temps_min[i]
        if temp_min < CRITICAL_ALERTS["frost"]["temp_threshold"]:
            days_out = "i dag" if i == 0 else f"om {i} dag(e)"
            alerts.append(f"{CRITICAL_ALERTS['frost']['icon']} Frost {days_out} ({int(temp_min)}°) — basilikum skal indendørs!")

    for i in range(min(3, len(temps_max))):
        temp_max = temps_max[i]
        if temp_max >= CRITICAL_ALERTS["heat"]["temp_threshold"]:
            days_out = "i dag" if i == 0 else f"om {i} dag(e)"
            alerts.append(f"{CRITICAL_ALERTS['heat']['icon']} Varmt {days_out} ({int(temp_max)}°) — vand grundigt!")

    if sum(precips[0:3]) == 0 and sum(precips[3:7]) < 2:
        alerts.append(f"{CRITICAL_ALERTS['drought']['icon']} Tørke forude — planlæg vandingsindsats")

    max_precip = max(precips[0:3])
    if max_precip > CRITICAL_ALERTS["heavy_rain"]["precip_mm"]:
        alerts.append(f"{CRITICAL_ALERTS['heavy_rain']['icon']} Kraftig regn kommende — vent inden beplantning")

    return alerts


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


def should_run():
    run_every_n = int(os.environ.get("RUN_EVERY_N_DAYS", "1"))
    if run_every_n == 1:
        return True

    today = date.today()
    day_of_year = today.timetuple().tm_yday
    return day_of_year % run_every_n == 0


def main():
    if not should_run():
        print(f"Springer over — kører kun hver {os.environ.get('RUN_EVERY_N_DAYS', '1')}. dag")
        return

    forecast = get_weather_forecast()

    temp_max_today = forecast["temperature_2m_max"][0]
    temp_min_today = forecast["temperature_2m_min"][0]

    recommended = get_recommended_tasks(forecast)
    alerts = get_critical_alerts(forecast)

    title_parts = [f"{int(temp_min_today)}°-{int(temp_max_today)}°C"]

    if alerts:
        title_parts.append("⚠️")

    if recommended:
        title_parts.append(f"{len(recommended)} task(s)")

    title = f"🌱 Haven: {' · '.join(title_parts)}"

    body_parts = []

    if alerts:
        body_parts.extend(alerts)
        body_parts.append("")

    if recommended:
        body_parts.append("— I dag kan du gøre —")
        for task in recommended:
            body_parts.append(f"{task['emoji']} {task['name']}")
            body_parts.append(f"   {task['reason']} ({task['temp']})")
        body_parts.append("")

    body_parts.append("💡 Tjek vejrudsigten inden du starter")

    body = "\n".join(body_parts) if body_parts else "Venlig havevejr — intet presserende i dag"

    send_notification(title, body)
    print(f"Sendt: {title}\n{body}")


if __name__ == "__main__":
    main()
