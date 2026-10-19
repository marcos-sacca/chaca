"""
Pipeline de prueba de concepto: extrae datos de Chacarita Juniors y de la
Primera Nacional desde la API no documentada de Sofascore, y los deja
en CSV listos para pandas.

USO INTERNO / ANALISIS PROPIO. Sofascore no ofrece esta API publicamente:
sus Terminos de Servicio prohiben copiar o redistribuir su contenido sin
permiso escrito. No usar esto para republicar datos ni para un producto
comercial sin antes conseguir autorizacion o migrar a una fuente con
licencia clara (ver informe adjunto).

Requiere: pip install requests pandas
"""
import time
import json
from pathlib import Path

from curl_cffi import requests
import pandas as pd

BASE = "https://api.sofascore.com/api/v1"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
IMPERSONATE = "chrome"  # curl_cffi imita el fingerprint TLS de Chrome real

CHACARITA_TEAM_ID = 3214
PRIMERA_NACIONAL_TOURNAMENT_ID = 703

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
RAW_DIR = DATA_DIR / "raw"
PROC_DIR = DATA_DIR / "processed"
RAW_DIR.mkdir(parents=True, exist_ok=True)
PROC_DIR.mkdir(parents=True, exist_ok=True)


def get(endpoint: str) -> dict:
    """GET con user-agent de navegador y pausa para no martillar la API."""
    url = f"{BASE}{endpoint}"
    r = requests.get(url, headers=HEADERS, impersonate=IMPERSONATE, timeout=15)
    time.sleep(1.0)  # cortesia: no golpear la API sin pausas
    r.raise_for_status()
    return r.json()


def fetch_squad(team_id: int = CHACARITA_TEAM_ID) -> pd.DataFrame:
    data = get(f"/team/{team_id}/players")
    rows = []
    for item in data.get("players", []):
        p = item["player"]
        rows.append({
            "player_id": p.get("id"),
            "name": p.get("name"),
            "position": p.get("position"),
            "jersey_number": p.get("jerseyNumber"),
            "country": p.get("country", {}).get("name"),
            "height": p.get("height"),
            "preferred_foot": p.get("preferredFoot"),
            "date_of_birth_ts": p.get("dateOfBirthTimestamp"),
            "market_value_eur": p.get("proposedMarketValue") or p.get("marketValue"),
        })
    df = pd.DataFrame(rows)
    if not df.empty and "date_of_birth_ts" in df:
        df["date_of_birth"] = pd.to_datetime(df["date_of_birth_ts"], unit="s", errors="coerce")
    return df


def fetch_recent_matches(team_id: int = CHACARITA_TEAM_ID, pages: int = 3) -> pd.DataFrame:
    """Trae resultados pasados. Sofascore pagina de a ~15-20 eventos por pagina."""
    rows = []
    for page in range(pages):
        data = get(f"/team/{team_id}/events/last/{page}")
        events = data.get("events", [])
        if not events:
            break
        for e in events:
            rows.append({
                "event_id": e.get("id"),
                "tournament": e.get("tournament", {}).get("name"),
                "season": e.get("season", {}).get("name"),
                "round": e.get("roundInfo", {}).get("round"),
                "home_team": e.get("homeTeam", {}).get("name"),
                "away_team": e.get("awayTeam", {}).get("name"),
                "home_score": e.get("homeScore", {}).get("current"),
                "away_score": e.get("awayScore", {}).get("current"),
                "start_timestamp": e.get("startTimestamp"),
                "status": e.get("status", {}).get("description"),
            })
    df = pd.DataFrame(rows).drop_duplicates(subset="event_id")
    if not df.empty:
        df["date"] = pd.to_datetime(df["start_timestamp"], unit="s", errors="coerce")
    return df


def fetch_match_stats(event_id: int) -> dict:
    """Devuelve un dict plano {stat_name: (home, away)} para un partido."""
    try:
        data = get(f"/event/{event_id}/statistics")
    except Exception:
        return {}
    flat = {}
    for period in data.get("statistics", []):
        if period.get("period") != "ALL":
            continue
        for group in period.get("groups", []):
            for item in group.get("statisticsItems", []):
                flat[item["name"]] = {"home": item.get("home"), "away": item.get("away")}
    return flat


def build_match_stats_table(matches_df: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for _, m in matches_df.iterrows():
        if m["status"] != "Ended":
            continue
        stats = fetch_match_stats(m["event_id"])
        row = {
            "event_id": m["event_id"],
            "date": m["date"],
            "home_team": m["home_team"],
            "away_team": m["away_team"],
            "home_score": m["home_score"],
            "away_score": m["away_score"],
        }
        for stat_name, vals in stats.items():
            row[f"home_{stat_name}"] = vals["home"]
            row[f"away_{stat_name}"] = vals["away"]
        rows.append(row)
    return pd.DataFrame(rows)


def fetch_league_tournaments_by_country(category_id: int = 48) -> pd.DataFrame:
    """category 48 = Argentina. Devuelve todos los torneos (para mapear
    ligas feeder de scouting: Federal A, Primera B/C/D Metropolitana, etc.)"""
    data = get(f"/category/{category_id}/unique-tournaments")
    rows = []
    for group in data.get("groups", []):
        for t in group.get("uniqueTournaments", []):
            rows.append({"tournament_id": t.get("id"), "name": t.get("name")})
    return pd.DataFrame(rows)


if __name__ == "__main__":
    print("1/4 Descargando plantel de Chacarita...")
    squad = fetch_squad()
    squad.to_csv(RAW_DIR / "chacarita_plantel.csv", index=False, encoding="utf-8-sig")
    print(f"   -> {len(squad)} jugadores guardados en data/raw/chacarita_plantel.csv")

    print("2/4 Descargando partidos recientes...")
    matches = fetch_recent_matches(pages=3)
    matches.to_csv(RAW_DIR / "chacarita_partidos.csv", index=False, encoding="utf-8-sig")
    print(f"   -> {len(matches)} partidos guardados en data/raw/chacarita_partidos.csv")

    print("3/4 Descargando estadisticas partido a partido (xG, posesion, tiros...)...")
    stats_table = build_match_stats_table(matches)
    stats_table.to_csv(PROC_DIR / "chacarita_partidos_stats.csv", index=False, encoding="utf-8-sig")
    print(f"   -> {len(stats_table)} partidos con estadisticas detalladas guardados en data/processed/")

    print("4/4 Descargando mapa de torneos argentinos (ligas feeder para scouting)...")
    tournaments = fetch_league_tournaments_by_country()
    tournaments.to_csv(RAW_DIR / "argentina_torneos.csv", index=False, encoding="utf-8-sig")
    print(f"   -> {len(tournaments)} torneos guardados en data/raw/argentina_torneos.csv")

    print("\nListo. Revisa la carpeta data/ para ver los CSV generados.")
