# Briefer

En personaliseret daglig briefing service, der sender notifikationer med vejr, kalender, opgaver, inspiration og aktivitetsforslag.

## Hvad gør det?

Briefer sender automatisk daglige notifikationer via [ntfy.sh](https://ntfy.sh) med:

- **Vejr** — Temperatur, vejrtype, påklædningshints, UV-index og fremtidig regn/frost/varmevarsel
- **Kalender** — Dagens og kommende events fra Google Calendar
- **Opgaver** — Nuværende Google Tasks
- **Inspirationsspørgsmål** — Et dagligt reflektionsspørgsmål (skiftes hver dag)
- **Aktivitetsstreak** — Antal dage i træk med afsluttede opgaver
- **Datoforslag** — Aktiviteter baseret på vejr (museum, strand, park osv.)
- **Nyt fra Anthropic** — En gang om ugen (kører separat)
- **Ugeopsummering** — Motivationsboosted oversigt over løste opgaver

## Komponenter

| Fil | Formål | Schedule |
|-----|--------|----------|
| `briefer.py` | Hovedbriefing | Dagligt kl. 05:00 UTC (07:00 DK sommertid) |
| `news.py` | Anthropic nyheder fra sitemap.xml | Ugentligt |
| `weekly.py` | Ugeopsummering med opgave-tally | Ugentligt |
| `birthday.py` | Fødselsdag-påmindelser | Dagligt |
| `monthly.py` | Månedsstatistik | Første dag i måneden |
| `reminder.py` | Brugerdefinerede påmindelser | Fleksibelt |

## Setup

### 1. Miljøvariable

Opret en `.env`-fil eller indstil følgende i dit system/GitHub Secrets:

```env
GOOGLE_CLIENT_ID=<din-google-client-id>
GOOGLE_CLIENT_SECRET=<din-google-client-secret>
GOOGLE_REFRESH_TOKEN=<din-google-refresh-token>
NTFY_TOPIC=<dit-ntfy-topic>
```

**Google OAuth:** Opret en OAuth 2.0 client via [Google Cloud Console](https://console.cloud.google.com/) med Calendar og Tasks API.

**ntfy.sh:** Vælg et emne-navn (topic) — notifikationer sendes til `https://ntfy.sh/<topic>`.

### 2. Installér afhængigheder

```bash
pip install -r requirements.txt
```

### 3. GitHub Actions (optional)

Workflows ligger i `.github/workflows/`:
- `daily.yml` — Daglig briefing
- `weekly.yml` — Ugeopsummering
- `news.yml` — Anthropic nyheder
- Osv.

Tilføj secrets til GitHub:
- `GOOGLE_CLIENT_ID`
- `GOOGLE_CLIENT_SECRET`
- `GOOGLE_REFRESH_TOKEN`
- `NTFY_TOPIC`

## Lokal test

Kør hvilken som helst script direkte:

```bash
python briefer.py    # Test daglig briefing
python news.py       # Test nyheder
python weekly.py     # Test ugeopsummering
```

## Tilpasning

### Daglige spørgsmål
Rediger `DAILY_QUESTIONS` liste i `briefer.py`.

### Datoidéer
Rediger `DATE_IDEAS` i `briefer.py`. Format:
```python
(navn, vejr-tags, beskrivelse, rejsetid)
```

Vejr-tags: `"sunny"`, `"rainy"`, `"hot"`, `"mild"`, `"any"`

### Påklædning- og vejrlogik
- `get_clothing_hint()` — Baseret på temperatur, vejr, vind, UV
- `get_weather_alerts()` — Regn, frost, varme, vind

### Kalender-filtrering
Rediger `EXCLUDED_EVENTS` for at ignorere bestemte événementer.

## Placering

Hardkoded til Birkerød, Danmark (55.851°N, 12.431°E). Vejr hentes fra [Open-Meteo](https://open-meteo.com/).

Skift `BIRKEROD_LAT` og `BIRKEROD_LON` for anden lokation.

## API'er

- [Google Calendar API](https://developers.google.com/calendar)
- [Google Tasks API](https://developers.google.com/tasks)
- [Open-Meteo Forecast](https://open-meteo.com/en/docs/forecast-api)
- [ntfy.sh](https://ntfy.sh/docs/)

## License

Ikke specificeret.
