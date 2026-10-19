"""
Libreria reutilizable para hablar con la API no documentada de Sofascore.
Uso interno / analisis propio de Chacarita Juniors - ver informe_datos_chacarita.html
para el encuadre legal (Sofascore no autoriza por escrito el uso de su API).

Todas las funciones devuelven estructuras ya "aplanadas", listas para pandas.
Se guarda cache en disco (data/cache/) para no repetir requests entre corridas.
"""
import time
import json
import hashlib
from pathlib import Path

from curl_cffi import requests

BASE = "https://api.sofascore.com/api/v1"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
IMPERSONATE = "chrome"
SLEEP = 1.3  # cortesia entre requests (subido tras un bloqueo 403 real en la sesion del 6-sep)

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

# IDs ya confirmados en la sesion anterior
CHACARITA_ID = 3214
ARGENTINA_CATEGORY_ID = 48
TOURNAMENTS = {
    "primera_nacional": 703,
    "liga_profesional": 155,
    "primera_b_metro": 1347,
    "primera_c_metro": 11386,
    "primera_d_metro": 14101,
    "federal_a": 14090,
    "copa_argentina": 1024,
    "copa_de_la_liga": 13475,
}


def _cache_path(endpoint: str) -> Path:
    h = hashlib.sha1(endpoint.encode()).hexdigest()[:16]
    safe = endpoint.strip("/").replace("/", "_")[:60]
    return CACHE_DIR / f"{safe}_{h}.json"


class RateLimited(Exception):
    """Sofascore devolvio 403: dejar de insistir, no es un error transitorio comun."""


CONSECUTIVE_403 = 0
MAX_CONSECUTIVE_403 = 3


def get(endpoint: str, use_cache: bool = True, retries: int = 3):
    """GET a la API de Sofascore con cache en disco y reintentos.
    Si detecta varios 403 seguidos, corta en vez de seguir insistiendo
    -un bloqueo por abuso no se resuelve reintentando mas rapido-."""
    global CONSECUTIVE_403
    cpath = _cache_path(endpoint)
    if use_cache and cpath.exists():
        with open(cpath, encoding="utf-8") as f:
            return json.load(f)

    last_err = None
    for attempt in range(retries):
        try:
            r = requests.get(f"{BASE}{endpoint}", headers=HEADERS,
                              impersonate=IMPERSONATE, timeout=20)
            if r.status_code == 403:
                CONSECUTIVE_403 += 1
                if CONSECUTIVE_403 >= MAX_CONSECUTIVE_403:
                    raise RateLimited(
                        f"{MAX_CONSECUTIVE_403} respuestas 403 seguidas - "
                        "Sofascore esta bloqueando, hay que parar y esperar."
                    )
                time.sleep(5 * CONSECUTIVE_403)
                continue
            CONSECUTIVE_403 = 0
            if r.status_code == 404:
                data = None
            else:
                r.raise_for_status()
                data = r.json()
            with open(cpath, "w", encoding="utf-8") as f:
                json.dump(data, f)
            time.sleep(SLEEP)
            return data
        except RateLimited:
            raise
        except Exception as e:  # noqa
            last_err = e
            time.sleep(2 * (attempt + 1))
    print(f"  [WARN] fallo definitivo en {endpoint}: {last_err}")
    return None


# ---------------------------------------------------------------- teams/events

def flatten_event(e: dict) -> dict:
    return {
        "event_id": e.get("id"),
        "tournament_id": e.get("tournament", {}).get("uniqueTournament", {}).get("id"),
        "tournament": e.get("tournament", {}).get("uniqueTournament", {}).get("name"),
        "season_id": e.get("season", {}).get("id"),
        "season": e.get("season", {}).get("name"),
        "round": e.get("roundInfo", {}).get("round"),
        "home_id": e.get("homeTeam", {}).get("id"),
        "home_team": e.get("homeTeam", {}).get("name"),
        "away_id": e.get("awayTeam", {}).get("id"),
        "away_team": e.get("awayTeam", {}).get("name"),
        "home_score": (e.get("homeScore") or {}).get("current"),
        "away_score": (e.get("awayScore") or {}).get("current"),
        "start_timestamp": e.get("startTimestamp"),
        "status": (e.get("status") or {}).get("description"),
        "status_type": (e.get("status") or {}).get("type"),
        "winner_code": e.get("winnerCode"),
    }


def team_events(team_id: int, kind: str = "last", max_pages: int = 6) -> list:
    """kind: 'last' o 'next'. Pagina hasta que no haya mas eventos."""
    out = []
    for page in range(max_pages):
        data = get(f"/team/{team_id}/events/{kind}/{page}")
        if not data or not data.get("events"):
            break
        out.extend(flatten_event(e) for e in data["events"])
    return out


def round_events(tournament_id: int, season_id: int, round_num: int) -> list:
    data = get(f"/unique-tournament/{tournament_id}/season/{season_id}/events/round/{round_num}")
    if not data or not data.get("events"):
        return []
    return [flatten_event(e) for e in data["events"]]


def season_all_events(tournament_id: int, season_id: int, n_rounds: int) -> list:
    out = []
    for r in range(1, n_rounds + 1):
        evs = round_events(tournament_id, season_id, r)
        out.extend(evs)
    return out


def seasons_list(tournament_id: int) -> list:
    data = get(f"/unique-tournament/{tournament_id}/seasons")
    if not data:
        return []
    return data.get("seasons", [])


def current_round(tournament_id: int, season_id: int) -> dict:
    data = get(f"/unique-tournament/{tournament_id}/season/{season_id}/rounds")
    return data or {}


def standings(tournament_id: int, season_id: int) -> list:
    data = get(f"/unique-tournament/{tournament_id}/season/{season_id}/standings/total")
    if not data:
        return []
    rows_out = []
    for block in data.get("standings", []):
        for row in block.get("rows", []):
            rows_out.append({
                "team_id": row["team"]["id"],
                "team": row["team"]["name"],
                "position": row.get("position"),
                "played": row.get("matches"),
                "wins": row.get("wins"),
                "draws": row.get("draws"),
                "losses": row.get("losses"),
                "gf": row.get("scoresFor"),
                "ga": row.get("scoresAgainst"),
                "gd": (row.get("scoresFor") or 0) - (row.get("scoresAgainst") or 0),
                "points": row.get("points"),
            })
    return rows_out


def squad(team_id: int) -> list:
    data = get(f"/team/{team_id}/players")
    if not data:
        return []
    out = []
    for item in data.get("players", []):
        p = item["player"]
        out.append({
            "player_id": p.get("id"),
            "name": p.get("name"),
            "position": p.get("position"),
            "jersey_number": p.get("jerseyNumber"),
            "country": (p.get("country") or {}).get("name"),
            "height": p.get("height"),
            "preferred_foot": p.get("preferredFoot"),
            "date_of_birth_ts": p.get("dateOfBirthTimestamp"),
            "market_value_eur": p.get("proposedMarketValue"),
            "team_id": team_id,
        })
    return out


def match_stats_flat(event_id: int) -> dict:
    data = get(f"/event/{event_id}/statistics")
    if not data:
        return {}
    flat = {}
    for period in data.get("statistics", []):
        if period.get("period") != "ALL":
            continue
        for group in period.get("groups", []):
            for item in group.get("statisticsItems", []):
                flat[item["name"]] = {"home": item.get("home"), "away": item.get("away")}
    return flat


def top_players(tournament_id: int, season_id: int, stat_type: str = "goals") -> list:
    """stat_type: goals, assists, rating, yellowCards, etc (segun lo que exponga sofascore)"""
    data = get(f"/unique-tournament/{tournament_id}/season/{season_id}/statistics/info")
    return data or {}


def player_statistics_season(player_id: int, tournament_id: int, season_id: int) -> dict:
    data = get(f"/player/{player_id}/unique-tournament/{tournament_id}/season/{season_id}/statistics/overall")
    return data or {}


def category_tournaments(category_id: int = ARGENTINA_CATEGORY_ID) -> list:
    data = get(f"/category/{category_id}/unique-tournaments")
    out = []
    for g in (data or {}).get("groups", []):
        for t in g.get("uniqueTournaments", []):
            out.append({"tournament_id": t.get("id"), "name": t.get("name")})
    return out


def search(query: str) -> list:
    data = get(f"/search/all?q={query}", use_cache=False)
    return (data or {}).get("results", [])
