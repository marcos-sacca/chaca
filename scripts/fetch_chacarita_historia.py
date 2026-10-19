"""
Historial completo de partidos de Chacarita (todas las competiciones que
indexa Sofascore para el equipo), pidiendo directamente por el team_id
en vez de iterar ronda por ronda de cada temporada -mucho mas liviano-.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sofa_lib as sl
import pandas as pd

RAW = sl.ROOT / "data" / "raw"
PROC = sl.ROOT / "data" / "processed"


def main():
    print("Bajando historial completo de Chacarita (paginando hacia atras)...")
    matches = sl.team_events(sl.CHACARITA_ID, kind="last", max_pages=45)
    df = pd.DataFrame(matches).drop_duplicates(subset="event_id")
    df = df.sort_values("start_timestamp")
    df.to_csv(RAW / "chacarita_historia_completa.csv", index=False, encoding="utf-8-sig")
    print(f"Total partidos historicos: {len(df)}")
    if len(df):
        import datetime
        print("Rango de fechas:", datetime.datetime.fromtimestamp(df['start_timestamp'].min()),
              "a", datetime.datetime.fromtimestamp(df['start_timestamp'].max()))
        print(df['season'].value_counts().to_string())

    print("\nBajando estadisticas (xG etc) de los partidos ya finalizados sin stats previas...")
    finished = df[df["status"] == "Ended"]
    stat_rows = []
    try:
        for i, (_, m) in enumerate(finished.iterrows()):
            stats = sl.match_stats_flat(m["event_id"])
            row = m.to_dict()
            for k, v in stats.items():
                row[f"home_{k}"] = v["home"]
                row[f"away_{k}"] = v["away"]
            stat_rows.append(row)
            if (i + 1) % 30 == 0:
                print(f"   ... {i+1}/{len(finished)}")
    except sl.RateLimited as e:
        print(f"   [CORTADO] {e} -- se guarda el progreso parcial ({len(stat_rows)}/{len(finished)}) y se sale limpio.")
    pd.DataFrame(stat_rows).to_csv(PROC / "chacarita_historia_stats.csv", index=False, encoding="utf-8-sig")
    print("Listo.")


if __name__ == "__main__":
    main()
