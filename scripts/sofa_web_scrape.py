"""
Sofascore bloquea api.sofascore.com (y cualquier ruta /api/v1/*, sin importar
el subdominio) pero el sitio principal (www.sofascore.com) sigue respondiendo
normal. Las paginas usan Next.js con Server-Side Rendering: el HTML trae un
<script id="__NEXT_DATA__"> con bastante data util (rating por partido en
'lastYearSummary', transfers, plantel completo con IDs) que NO pasa por la
API bloqueada. Esto lo explota.

Uso interno / analisis propio - mismo encuadre legal que sofa_lib.py.
"""
import re
import json
import time
from pathlib import Path

from curl_cffi import requests
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
SLEEP = 1.5
ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache_web"
CACHE_DIR.mkdir(parents=True, exist_ok=True)


def _next_data(url: str, cache_key: str) -> dict:
    cpath = CACHE_DIR / f"{cache_key}.json"
    if cpath.exists():
        with open(cpath, encoding="utf-8") as f:
            return json.load(f)
    r = requests.get(url, headers=HEADERS, impersonate="chrome", timeout=20)
    r.raise_for_status()
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
    if not m:
        return {}
    data = json.loads(m.group(1))
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(data, f)
    time.sleep(SLEEP)
    return data


def team_full_squad(slug: str, team_id: int) -> tuple:
    """Devuelve (df_plantel_con_ids, df_transfers_out)"""
    url = f"https://www.sofascore.com/team/football/{slug}/{team_id}"
    data = _next_data(url, f"team_{team_id}")
    pp = data["props"]["pageProps"]
    rows = []
    for item in pp["players"]["players"]:
        p = item["player"]
        rows.append({"player_id": p["id"], "name": p["name"], "position": p.get("position"),
                     "jersey": p.get("jerseyNumber")})
    squad = pd.DataFrame(rows)

    trows = []
    for t in pp["teamTransfers"]["transfersOut"]:
        trows.append({
            "player": t.get("player", {}).get("name"),
            "to_team": t.get("transferTo", {}).get("name"),
            "date_ts": t.get("transferDateTimestamp"),
        })
    transfers_out = pd.DataFrame(trows)
    if not transfers_out.empty:
        transfers_out["date"] = pd.to_datetime(transfers_out["date_ts"], unit="s", errors="coerce")
    return squad, transfers_out


def player_rating_history(slug: str, player_id: int) -> pd.DataFrame:
    """lastYearSummary trae eventos de rating + marcas de transferencia."""
    url = f"https://www.sofascore.com/player/{slug}/{player_id}"
    data = _next_data(url, f"player_{player_id}")
    pp = data.get("props", {}).get("pageProps", {})
    summary = pp.get("lastYearSummary", [])
    rows = []
    for e in summary:
        if e.get("type") == "event":
            rows.append({
                "player_id": player_id,
                "date": pd.to_datetime(e["timestamp"], unit="s"),
                "rating": float(e["value"]),
                "tournament_id": e.get("uniqueTournamentId"),
            })
    return pd.DataFrame(rows)


def slugify(name: str) -> str:
    import unicodedata
    s = unicodedata.normalize("NFKD", name).encode("ascii", "ignore").decode()
    s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
    return s


if __name__ == "__main__":
    squad, transfers_out = team_full_squad("ferrocarril-midland", 270344)
    squad.to_csv(ROOT / "data/raw/midland_sofascore_squad.csv", index=False, encoding="utf-8-sig")
    transfers_out.to_csv(ROOT / "data/raw/midland_transfers_out.csv", index=False, encoding="utf-8-sig")
    print(f"Plantel: {len(squad)} jugadores | Transfers out: {len(transfers_out)}")
