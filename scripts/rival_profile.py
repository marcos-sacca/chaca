"""
Perfil tactico-estadistico profundo de un rival de Zona B, a partir de los
datos ya descargados (no requiere Sofascore desbloqueado). Calcula estilo
de juego, fortalezas/debilidades relativas a la zona, forma reciente,
splits local/visitante, y disciplina.
"""
import sys
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
PROC = ROOT / "data" / "processed"
RAW = ROOT / "data" / "raw"

CHACA_ID = 3214


def load_zone_stats() -> pd.DataFrame:
    df = pd.read_csv(PROC / "zona_b_2026_partidos_stats.csv")
    return df[df["status"] == "Ended"].copy()


def pct(x):
    """Convierte strings tipo '23/50 (46%)' al valor porcentual float, o deja el numero tal cual."""
    if pd.isna(x):
        return np.nan
    s = str(x)
    if "%" in s:
        try:
            return float(s.split("(")[-1].replace("%)", "").replace("%", ""))
        except ValueError:
            return np.nan
    try:
        return float(s)
    except ValueError:
        return np.nan


def team_match_log(df: pd.DataFrame, team_id: int) -> pd.DataFrame:
    mask = (df["home_id"] == team_id) | (df["away_id"] == team_id)
    sub = df[mask].copy()
    is_home = sub["home_id"] == team_id

    def pick(col):
        return np.where(is_home, sub[f"home_{col}"], sub[f"away_{col}"])

    def pick_rival(col):
        return np.where(is_home, sub[f"away_{col}"], sub[f"home_{col}"])

    log = pd.DataFrame({
        "event_id": sub["event_id"],
        "round": sub["round"],
        "date": pd.to_datetime(sub["start_timestamp"], unit="s"),
        "condicion": np.where(is_home, "Local", "Visitante"),
        "rival": np.where(is_home, sub["away_team"], sub["home_team"]),
        "gf": pick("score"), "gc": pick_rival("score"),
        "xg_for": pick("Expected goals"), "xg_against": pick_rival("Expected goals"),
        "posesion": [pct(v) for v in pick("Ball possession")],
        "shots_total": pick("Total shots"), "shots_on_target": pick("Shots on target"),
        "shots_inside": pick("Shots inside box"), "shots_outside": pick("Shots outside box"),
        "corners_for": pick("Corner kicks"), "corners_against": pick_rival("Corner kicks"),
        "crosses_raw": pick("Crosses"),
        "aerial_raw": pick("Aerial duels"),
        "long_balls_raw": pick("Long balls"),
        "dribbles_raw": pick("Dribbles"),
        "tackles": pick("Total tackles"), "interceptions": pick("Interceptions"),
        "fouls": pick("Fouls"), "yellow": pick("Yellow cards"), "red": pick("Red cards"),
        "passes": pick("Passes"), "accurate_passes": pick("Accurate passes"),
    })
    log["gf"] = pd.to_numeric(log["gf"], errors="coerce")
    log["gc"] = pd.to_numeric(log["gc"], errors="coerce")
    log["resultado"] = np.select(
        [log["gf"] > log["gc"], log["gf"] == log["gc"]], ["V", "E"], default="D")
    log["pts"] = log["resultado"].map({"V": 3, "E": 1, "D": 0})
    # desglosar los campos "N/M (P%)"
    for base in ["crosses", "aerial", "long_balls", "dribbles"]:
        raw = log[f"{base}_raw"].astype(str)
        log[f"{base}_ok"] = raw.str.extract(r"^(\d+)/")[0].astype(float)
        log[f"{base}_att"] = raw.str.extract(r"/(\d+)")[0].astype(float)
        log[f"{base}_pct"] = raw.apply(pct)
    return log.sort_values("round")


def zone_averages(df: pd.DataFrame, team_ids: list) -> dict:
    """Promedio de la zona para cada metrica clave, para poder comparar un rival contra el resto."""
    logs = [team_match_log(df, t) for t in team_ids]
    all_logs = pd.concat(logs, ignore_index=True)
    keys = ["xg_for", "xg_against", "posesion", "shots_total", "shots_on_target",
            "shots_inside", "shots_outside", "corners_for", "corners_against",
            "crosses_att", "crosses_pct", "aerial_pct", "long_balls_pct", "dribbles_pct",
            "tackles", "interceptions", "fouls", "yellow"]
    return {k: all_logs[k].mean() for k in keys}


def summarize(log: pd.DataFrame, last_n: int = 6) -> dict:
    recent = log.tail(last_n)
    keys = ["xg_for", "xg_against", "posesion", "shots_total", "shots_on_target",
            "shots_inside", "shots_outside", "corners_for", "corners_against",
            "crosses_att", "crosses_pct", "aerial_pct", "long_balls_pct", "dribbles_pct",
            "tackles", "interceptions", "fouls", "yellow"]
    out = {"PJ_total": len(log), "Pts_total": int(log["pts"].sum()),
           "PtsPJ_total": round(log["pts"].mean(), 2),
           "forma_reciente": "".join(recent["resultado"].tolist()),
           "PtsPJ_reciente": round(recent["pts"].mean(), 2)}
    for k in keys:
        out[f"{k}_temporada"] = round(log[k].mean(), 2)
        out[f"{k}_reciente"] = round(recent[k].mean(), 2)
    return out


if __name__ == "__main__":
    df = load_zone_stats()
    team_ids_str = sys.argv[1] if len(sys.argv) > 1 else str(CHACA_ID)
    tid = int(team_ids_str)
    log = team_match_log(df, tid)
    print(log[["round", "date", "condicion", "rival", "gf", "gc", "resultado",
               "xg_for", "xg_against", "posesion", "corners_for", "corners_against"]].to_string(index=False))
