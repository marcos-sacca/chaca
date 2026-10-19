"""
Baja TODO el calendario 2026 de la Zona B de Primera Nacional (18 equipos,
donde juega Chacarita): partidos jugados + estadisticas + fixture restante.
Es el insumo para simular las 8 fechas que quedan y estimar probabilidad
de descenso.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sofa_lib as sl
import pandas as pd

RAW = sl.ROOT / "data" / "raw"
PROC = sl.ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

TOURNAMENT_ID = 703
SEASON_ID = 87940
TOTAL_ROUNDS = 36


def main():
    print("1) Standings actuales (para identificar los 18 equipos de Zona B)...")
    st = sl.standings(TOURNAMENT_ID, SEASON_ID)
    data = sl.get(f"/unique-tournament/{TOURNAMENT_ID}/season/{SEASON_ID}/standings/total")
    zone_b_ids = set()
    zone_b_name = None
    for block in data["standings"]:
        if any(r["team"]["id"] == sl.CHACARITA_ID for r in block["rows"]):
            zone_b_name = block.get("name")
            zone_b_ids = {r["team"]["id"] for r in block["rows"]}
    print(f"   Zona de Chacarita: {zone_b_name} -> {len(zone_b_ids)} equipos")
    pd.DataFrame(st).to_csv(RAW / "primera_nacional_2026_standings_full.csv", index=False, encoding="utf-8-sig")

    print(f"2) Bajando las {TOTAL_ROUNDS} fechas del calendario (round por round)...")
    all_events = []
    for r in range(1, TOTAL_ROUNDS + 1):
        evs = sl.round_events(TOURNAMENT_ID, SEASON_ID, r)
        all_events.extend(evs)
        print(f"   fecha {r}: {len(evs)} partidos totales (ambas zonas)")
    df_all = pd.DataFrame(all_events).drop_duplicates(subset="event_id")

    df_zb = df_all[df_all["home_id"].isin(zone_b_ids) & df_all["away_id"].isin(zone_b_ids)].copy()
    df_zb.to_csv(RAW / "zona_b_2026_calendario_completo.csv", index=False, encoding="utf-8-sig")
    print(f"   Zona B: {len(df_zb)} partidos totales en el calendario")

    finished = df_zb[df_zb["status"] == "Ended"]
    pending = df_zb[df_zb["status"] != "Ended"]
    print(f"   Jugados: {len(finished)} | Pendientes: {len(pending)}")

    print("3) Bajando estadisticas (xG, posesion, tiros...) de cada partido jugado...")
    stat_rows = []
    try:
        for i, (_, m) in enumerate(finished.iterrows()):
            stats = sl.match_stats_flat(m["event_id"])
            row = m.to_dict()
            for stat_name, vals in stats.items():
                row[f"home_{stat_name}"] = vals["home"]
                row[f"away_{stat_name}"] = vals["away"]
            stat_rows.append(row)
            if (i + 1) % 20 == 0:
                print(f"   ... {i+1}/{len(finished)} partidos con stats")
    except sl.RateLimited as e:
        print(f"   [CORTADO] {e} -- progreso parcial ({len(stat_rows)}/{len(finished)}) guardado igual.")
    df_stats = pd.DataFrame(stat_rows)
    df_stats.to_csv(PROC / "zona_b_2026_partidos_stats.csv", index=False, encoding="utf-8-sig")
    print(f"   Guardado: {len(df_stats)} partidos con estadisticas completas")

    print("4) Guardando fixture pendiente (para la simulacion)...")
    pending.to_csv(PROC / "zona_b_2026_fixture_pendiente.csv", index=False, encoding="utf-8-sig")

    print("\nListo. Archivos generados:")
    print(" - data/raw/primera_nacional_2026_standings_full.csv")
    print(" - data/raw/zona_b_2026_calendario_completo.csv")
    print(" - data/processed/zona_b_2026_partidos_stats.csv")
    print(" - data/processed/zona_b_2026_fixture_pendiente.csv")


if __name__ == "__main__":
    main()
