"""
Modelo de fuerza de equipos (ataque/defensa basado en xG) + simulacion
Monte Carlo de las fechas que quedan en la Zona B 2026, para estimar
la probabilidad de descenso de Chacarita y de sus rivales directos.

Metodologia (simple a proposito, documentada para poder auditarla):
 1. Se limpia el calendario (Sofascore duplica partidos reprogramados).
 2. Fuerza de ataque/defensa de cada equipo = su xG a favor / en contra
    promedio, relativizado al promedio de la zona (estilo Dixon-Coles
    simplificado, con xG en vez de goles para reducir ruido de muestra).
 3. Para cada partido pendiente: lambda_home y lambda_away via Poisson.
 4. Se corren N_SIMS temporadas completas y se cuenta en cuantas
    Chacarita (y cada rival directo) termina 17 o 18 -zona de descenso-.
"""
import sys
import json
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sofa_lib as sl

RAW = sl.ROOT / "data" / "raw"
PROC = sl.ROOT / "data" / "processed"
N_SIMS = 30000
CHACARITA_ID = 3214

np.random.seed(42)


def clean_calendar(df: pd.DataFrame) -> pd.DataFrame:
    """Sofascore deja el evento 'Postponed' original ademas del reprogramado.
    Nos quedamos con: el que tenga status 'Ended' si existe, sino el de
    timestamp mas alto que no sea Postponed."""
    keep_rows = []
    for (h, a), g in df.groupby(["home_id", "away_id"]):
        ended = g[g["status"] == "Ended"]
        if len(ended) >= 1:
            keep_rows.append(ended.sort_values("start_timestamp").iloc[-1])
            continue
        not_pp = g[g["status"] != "Postponed"]
        if len(not_pp) >= 1:
            keep_rows.append(not_pp.sort_values("start_timestamp").iloc[-1])
        else:
            keep_rows.append(g.sort_values("start_timestamp").iloc[-1])
    return pd.DataFrame(keep_rows).reset_index(drop=True)


def build_team_strength(finished: pd.DataFrame, half_life_days=None) -> pd.DataFrame:
    """half_life_days=None -> pondera toda la temporada por igual.
    half_life_days=N -> pondera exponencialmente, un partido de hace N dias
    pesa la mitad que uno de hoy (para capturar la forma reciente)."""
    teams = pd.unique(finished[["home_id", "away_id"]].values.ravel())
    names = {}
    for _, r in finished.iterrows():
        names[r["home_id"]] = r["home_team"]
        names[r["away_id"]] = r["away_team"]

    if half_life_days:
        max_ts = finished["start_timestamp"].max()
        age_days = (max_ts - finished["start_timestamp"]) / 86400
        finished = finished.copy()
        finished["w"] = 0.5 ** (age_days / half_life_days)
    else:
        finished = finished.copy()
        finished["w"] = 1.0

    def wavg(vals, weights):
        vals, weights = np.asarray(vals, dtype=float), np.asarray(weights, dtype=float)
        mask = ~np.isnan(vals)
        if mask.sum() == 0:
            return np.nan
        return np.average(vals[mask], weights=weights[mask])

    league_home_xg = wavg(finished["home_Expected goals"], finished["w"])
    league_away_xg = wavg(finished["away_Expected goals"], finished["w"])

    rows = []
    for t in teams:
        home_games = finished[finished["home_id"] == t]
        away_games = finished[finished["away_id"] == t]
        xg_for = pd.concat([home_games["home_Expected goals"], away_games["away_Expected goals"]])
        xg_against = pd.concat([home_games["away_Expected goals"], away_games["home_Expected goals"]])
        w = pd.concat([home_games["w"], away_games["w"]])
        goals_for = pd.concat([home_games["home_score"], away_games["away_score"]])
        goals_against = pd.concat([home_games["away_score"], away_games["home_score"]])
        rows.append({
            "team_id": t, "team": names.get(t),
            "games_with_stats": xg_for.notna().sum(),
            "xg_for_avg": wavg(xg_for, w),
            "xg_against_avg": wavg(xg_against, w),
            "goals_for_avg": wavg(goals_for, w),
            "goals_against_avg": wavg(goals_against, w),
        })
    df = pd.DataFrame(rows)
    league_xg_avg = (league_home_xg + league_away_xg) / 2
    # si algun equipo tiene pocos partidos con stats, usamos goles reales como respaldo
    df["xg_for_avg"] = df["xg_for_avg"].fillna(df["goals_for_avg"])
    df["xg_against_avg"] = df["xg_against_avg"].fillna(df["goals_against_avg"])
    df["attack_strength"] = df["xg_for_avg"] / league_xg_avg
    df["defense_strength"] = df["xg_against_avg"] / league_xg_avg
    return df, league_home_xg, league_away_xg


def current_table(standings_rows: list) -> pd.DataFrame:
    df = pd.DataFrame(standings_rows)
    return df.set_index("team_id")


def simulate(remaining: pd.DataFrame, strength: pd.DataFrame, base_table: pd.DataFrame,
             league_home_xg: float, league_away_xg: float, n_sims: int = N_SIMS):
    s = strength.set_index("team_id")
    matches = []
    for _, m in remaining.iterrows():
        h, a = m["home_id"], m["away_id"]
        if h not in s.index or a not in s.index:
            continue
        lam_h = league_home_xg * s.loc[h, "attack_strength"] * s.loc[a, "defense_strength"]
        lam_a = league_away_xg * s.loc[a, "attack_strength"] * s.loc[h, "defense_strength"]
        matches.append((h, a, max(lam_h, 0.15), max(lam_a, 0.15)))

    team_ids = list(base_table.index)
    final_positions = {t: [] for t in team_ids}
    final_points = {t: [] for t in team_ids}

    base_pts = base_table["points"].to_dict()
    base_gd = base_table["gd"].to_dict()
    base_gf = base_table["gf"].to_dict()

    for _ in range(n_sims):
        pts = dict(base_pts)
        gd = dict(base_gd)
        gf = dict(base_gf)
        for h, a, lam_h, lam_a in matches:
            gh = np.random.poisson(lam_h)
            ga = np.random.poisson(lam_a)
            gf[h] += gh
            gf[a] += ga
            gd[h] += gh - ga
            gd[a] += ga - gh
            if gh > ga:
                pts[h] += 3
            elif gh < ga:
                pts[a] += 3
            else:
                pts[h] += 1
                pts[a] += 1
        ranking = sorted(team_ids, key=lambda t: (-pts[t], -gd[t], -gf[t]))
        for pos, t in enumerate(ranking, start=1):
            final_positions[t].append(pos)
            final_points[t].append(pts[t])

    out = []
    for t in team_ids:
        positions = np.array(final_positions[t])
        points = np.array(final_points[t])
        out.append({
            "team_id": t,
            "team": base_table.loc[t, "team"],
            "current_position": base_table.loc[t, "position"],
            "current_points": base_table.loc[t, "points"],
            "sim_avg_final_points": round(points.mean(), 1),
            "sim_avg_final_position": round(positions.mean(), 1),
            "prob_descenso_pct": round((positions >= 17).mean() * 100, 1),
            "prob_top8_playoff_pct": round((positions <= 8).mean() * 100, 1),
            "prob_gana_zona_pct": round((positions == 1).mean() * 100, 1),
        })
    return pd.DataFrame(out).sort_values("current_position")


def main():
    print("Cargando y limpiando calendario de Zona B...")
    cal = pd.read_csv(RAW / "zona_b_2026_calendario_completo.csv")
    cal_clean = clean_calendar(cal)
    finished = cal_clean[cal_clean["status"] == "Ended"].copy()
    remaining = cal_clean[cal_clean["status"] != "Ended"].copy()
    print(f"  Calendario limpio: {len(cal_clean)} partidos totales "
          f"({len(finished)} jugados, {len(remaining)} pendientes)")

    print("Cruzando con estadisticas (xG) de los partidos jugados...")
    stats = pd.read_csv(PROC / "zona_b_2026_partidos_stats.csv")
    stats_slim = stats[["event_id", "home_Expected goals", "away_Expected goals"]]
    finished = finished.merge(stats_slim, on="event_id", how="left")
    print(f"  Partidos jugados con xG disponible: {finished['home_Expected goals'].notna().sum()} / {len(finished)}")

    print("Calculando fuerza de ataque/defensa por equipo (ponderada por forma reciente, half-life=75 dias)...")
    strength, lg_h, lg_a = build_team_strength(finished, half_life_days=75)
    strength.to_csv(PROC / "zona_b_team_strength.csv", index=False, encoding="utf-8-sig")
    print(strength[["team", "attack_strength", "defense_strength"]].sort_values("attack_strength", ascending=False).to_string(index=False))

    strength_flat, _, _ = build_team_strength(finished, half_life_days=None)
    chaca_w = strength[strength["team_id"] == CHACARITA_ID].iloc[0]
    chaca_f = strength_flat[strength_flat["team_id"] == CHACARITA_ID].iloc[0]
    print(f"\n[sensibilidad] Chacarita ataque/defensa -> temporada completa: "
          f"{chaca_f['attack_strength']:.2f}/{chaca_f['defense_strength']:.2f} | "
          f"ponderado por forma reciente: {chaca_w['attack_strength']:.2f}/{chaca_w['defense_strength']:.2f}")

    print("\nTabla base actual (antes de simular)...")
    st_data = sl.get(f"/unique-tournament/703/season/87940/standings/total")
    base_rows = None
    for block in st_data["standings"]:
        if any(r["team"]["id"] == CHACARITA_ID for r in block["rows"]):
            base_rows = block["rows"]
    base_table = pd.DataFrame([{
        "team_id": r["team"]["id"], "team": r["team"]["name"], "position": r["position"],
        "points": r["points"], "gd": r["scoresFor"] - r["scoresAgainst"], "gf": r["scoresFor"],
    } for r in base_rows]).set_index("team_id")

    print(f"\nSimulando {N_SIMS} temporadas Monte Carlo (modelo ponderado por forma reciente)...")
    result = simulate(remaining, strength, base_table, lg_h, lg_a, N_SIMS)
    result.to_csv(PROC / "zona_b_simulacion_descenso.csv", index=False, encoding="utf-8-sig")

    print(f"Simulando de nuevo con el modelo SIN ponderar (toda la temporada por igual), como control de sensibilidad...")
    lg_h_f = finished["home_Expected goals"].mean()
    lg_a_f = finished["away_Expected goals"].mean()
    result_flat = simulate(remaining, strength_flat, base_table, lg_h_f, lg_a_f, N_SIMS)
    chaca_flat_prob = result_flat[result_flat["team_id"] == CHACARITA_ID]["prob_descenso_pct"].iloc[0]

    print("\n=== RESULTADO DE LA SIMULACION (Zona B completa) ===")
    print(result[["current_position", "team", "current_points", "sim_avg_final_points",
                   "prob_descenso_pct", "prob_top8_playoff_pct"]].to_string(index=False))

    chaca = result[result["team_id"] == CHACARITA_ID].iloc[0]
    print(f"\n>>> CHACARITA (modelo forma reciente): {chaca['prob_descenso_pct']}% de probabilidad de descenso "
          f"(posicion final promedio: {chaca['sim_avg_final_position']})")
    print(f">>> CHACARITA (modelo temporada completa, sin ponderar): {chaca_flat_prob}% de probabilidad de descenso")
    print(f">>> Diferencia entre ambos modelos: {abs(chaca['prob_descenso_pct'] - chaca_flat_prob):.1f} puntos porcentuales")


if __name__ == "__main__":
    main()
