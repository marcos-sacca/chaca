"""
Aplica la tecnica SSR (bypass del bloqueo de la API via el sitio principal
de Sofascore) a los 7 rivales restantes de Central de Rivales: baja el
plantel completo y el rating partido a partido de cada jugador con
minutos reales.
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_web_scrape import team_full_squad, player_rating_history, slugify, ROOT
import pandas as pd

RIVALES = {
    "Quilmes": (4936, "quilmes-atletico-club"),
    "Colegiales": (112493, "club-atletico-colegiales"),
    "Patronato": (43741, "patronato"),
    "Almagro": (4938, "almagro"),
    "Deportivo Maipu": (213042, "deportivo-maipu"),
    "Temperley": (112499, "temperley"),
    "Nueva Chicago": (3200, "nueva-chicago"),
}

PN_TOURNAMENT_ID = 703


def process_team(name, team_id, slug_guess):
    print(f"\n=== {name} (id={team_id}) ===")
    try:
        squad, transfers_out = team_full_squad(slug_guess, team_id)
    except Exception as e:
        print(f"  ERROR bajando plantel: {e}")
        return None, None
    print(f"  Plantel: {len(squad)} jugadores")
    squad.to_csv(ROOT / f"data/raw/rival_squad_{team_id}.csv", index=False, encoding="utf-8-sig")
    transfers_out.to_csv(ROOT / f"data/raw/rival_transfers_out_{team_id}.csv", index=False, encoding="utf-8-sig")

    all_ratings = []
    for _, row in squad.iterrows():
        pslug = slugify(row["name"])
        try:
            df = player_rating_history(pslug, int(row["player_id"]))
            if not df.empty:
                df_pn = df[df["tournament_id"] == PN_TOURNAMENT_ID]
                if not df_pn.empty:
                    df_pn = df_pn.copy()
                    df_pn["name"] = row["name"]
                    df_pn["position"] = row["position"]
                    all_ratings.append(df_pn)
        except Exception as e:
            print(f"    {row['name']}: error {e}")

    if not all_ratings:
        print("  Sin ratings encontrados")
        return squad, pd.DataFrame()

    ratings = pd.concat(all_ratings, ignore_index=True)
    summary = []
    for pname, g in ratings.groupby("name"):
        g = g.sort_values("date")
        last5 = g.tail(5)
        summary.append({
            "jugador": pname, "PJ": len(g),
            "rating_prom": round(g["rating"].mean(), 2),
            "rating_ultimos5": round(last5["rating"].mean(), 2),
            "tendencia": round(last5["rating"].mean() - g["rating"].mean(), 2),
        })
    summary_df = pd.DataFrame(summary).sort_values("rating_prom", ascending=False)
    print(f"  {len(summary_df)} jugadores con rating en Primera Nacional 2026")
    print(summary_df.to_string(index=False))
    summary_df.to_csv(ROOT / f"data/processed/rival_form_{team_id}.csv", index=False, encoding="utf-8-sig")
    return squad, summary_df


if __name__ == "__main__":
    results = {}
    for name, (tid, slug) in RIVALES.items():
        squad, summary = process_team(name, tid, slug)
        results[name] = summary
    print("\n\n=== RESUMEN FINAL: TOP 3 rating por equipo ===")
    for name, summary in results.items():
        if summary is not None and not summary.empty:
            print(f"\n{name}:")
            print(summary.head(3).to_string(index=False))
