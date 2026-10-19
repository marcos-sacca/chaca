import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sofa_web_scrape import player_rating_history, slugify, ROOT
import pandas as pd

squad = pd.read_csv(ROOT / "data/raw/midland_sofascore_squad.csv")

all_ratings = []
for i, row in squad.iterrows():
    slug = slugify(row["name"])
    try:
        df = player_rating_history(slug, int(row["player_id"]))
        if not df.empty:
            df["name"] = row["name"]
            df["position"] = row["position"]
            all_ratings.append(df)
            print(f"  {row['name']}: {len(df)} partidos con rating")
        else:
            print(f"  {row['name']}: SIN DATOS (0 eventos)")
    except Exception as e:
        print(f"  {row['name']}: ERROR {type(e).__name__} {e}")

result = pd.concat(all_ratings, ignore_index=True) if all_ratings else pd.DataFrame()
result.to_csv(ROOT / "data/processed/midland_player_ratings.csv", index=False, encoding="utf-8-sig")
print(f"\nTotal: {len(result)} filas de rating, {result['player_id'].nunique() if not result.empty else 0} jugadores con datos")
