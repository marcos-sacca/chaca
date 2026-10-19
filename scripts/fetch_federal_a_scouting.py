"""
Sofascore no calcula 'top-players' (goleadores/asistentes) para el Federal A
-la liga a la que Chacarita caeria si desciende, por ser afiliado directo a
AFA-, asi que se reconstruye a mano a partir de los incidentes (goles,
asistencias) de cada partido ya jugado.
"""
import sys
from pathlib import Path
from collections import defaultdict

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sofa_lib as sl
import pandas as pd

RAW = sl.ROOT / "data" / "raw"
PROC = sl.ROOT / "data" / "processed"

TOURNAMENT_ID = 14090  # Federal A
SEASON_ID = 91002      # 2026
TOTAL_ROUNDS = 18


def goal_incidents(event_id: int) -> list:
    d = sl.get(f"/event/{event_id}/incidents")
    if not d:
        return []
    out = []
    for inc in d.get("incidents", []):
        if inc.get("incidentType") != "goal":
            continue
        scorer = inc.get("player") or {}
        assist = inc.get("assist1") or {}
        out.append({
            "event_id": event_id,
            "time": inc.get("time"),
            "is_home": inc.get("isHome"),
            "incident_class": inc.get("incidentClass"),  # regular / penalty / owngoal
            "scorer_id": scorer.get("id"),
            "scorer_name": scorer.get("name"),
            "assist_id": assist.get("id"),
            "assist_name": assist.get("name"),
        })
    return out


def main():
    print("1) Bajando calendario Federal A 2026 (todas las zonas)...")
    all_events = []
    for r in range(1, TOTAL_ROUNDS + 1):
        evs = sl.round_events(TOURNAMENT_ID, SEASON_ID, r)
        all_events.extend(evs)
        print(f"   fecha {r}: {len(evs)} partidos")
    df_all = pd.DataFrame(all_events).drop_duplicates(subset="event_id")
    df_all.to_csv(RAW / "federal_a_2026_calendario.csv", index=False, encoding="utf-8-sig")

    finished = df_all[df_all["status"] == "Ended"]
    print(f"   Total partidos: {len(df_all)} | Jugados: {len(finished)}")

    print("2) Extrayendo goles/asistencias de cada partido jugado (reconstruccion manual)...")
    all_goals = []
    try:
        for i, (_, m) in enumerate(finished.iterrows()):
            goals = goal_incidents(m["event_id"])
            for g in goals:
                g["home_team"] = m["home_team"]
                g["away_team"] = m["away_team"]
            all_goals.extend(goals)
            if (i + 1) % 25 == 0:
                print(f"   ... {i+1}/{len(finished)} partidos procesados, {len(all_goals)} goles acumulados")
    except sl.RateLimited as e:
        print(f"   [CORTADO] {e} -- se guarda el progreso parcial ({len(all_goals)} goles) y se sale limpio.")

    df_goals = pd.DataFrame(all_goals)
    df_goals.to_csv(RAW / "federal_a_2026_goles_detalle.csv", index=False, encoding="utf-8-sig")
    print(f"   Total goles registrados: {len(df_goals)}")

    print("3) Armando tabla de goleadores y asistentes...")
    real_goals = df_goals[df_goals["incident_class"] != "owngoal"]
    scorers = (real_goals.groupby(["scorer_id", "scorer_name"]).size()
               .reset_index(name="goles").sort_values("goles", ascending=False))
    assists = (real_goals.dropna(subset=["assist_id"]).groupby(["assist_id", "assist_name"]).size()
               .reset_index(name="asistencias").sort_values("asistencias", ascending=False))
    scorers.to_csv(PROC / "federal_a_2026_goleadores.csv", index=False, encoding="utf-8-sig")
    assists.to_csv(PROC / "federal_a_2026_asistentes.csv", index=False, encoding="utf-8-sig")

    print("\nTop 15 goleadores Federal A 2026 (reconstruido manualmente):")
    print(scorers.head(15).to_string(index=False))
    print("\nTop 10 asistentes Federal A 2026:")
    print(assists.head(10).to_string(index=False))


if __name__ == "__main__":
    main()
