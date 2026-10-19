"""
Motor de scouting: baja los rankings de jugadores destacados (goles,
asistencias, rating, regates, pases clave, etc.) de las ligas "feeder" de
Chacarita -Federal A, Primera B Metropolitana, Primera C Metropolitana-
para la temporada actual (2026, scouting en vivo) y la anterior (2025,
insumo para el backtest: "¿a estos jugadores los hubieramos fichado bien?").

Para cada jugador destacado, se baja tambien su ficha individual
(edad, nacionalidad, altura, pie habil, valor de mercado estimado) y,
cuando esta disponible, el equipo en el que juega HOY -para poder ver,
en el backtest, si un destacado de 2025 dio el salto de categoria en 2026-.
"""
import sys
import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import sofa_lib as sl
import pandas as pd

RAW = sl.ROOT / "data" / "raw"
PROC = sl.ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
PROC.mkdir(parents=True, exist_ok=True)

LEAGUES = {
    "federal_a": sl.TOURNAMENTS["federal_a"],
    "primera_b_metro": sl.TOURNAMENTS["primera_b_metro"],
    "primera_c_metro": sl.TOURNAMENTS["primera_c_metro"],
}

# metricas relevantes para armar un perfil de jugador de scouting
STAT_KEYS = [
    "goals", "assists", "goalsAssistsSum", "rating", "successfulDribbles",
    "keyPasses", "accurateLongBalls", "clearances", "saves", "totalShots",
]

TOP_N = 25  # cuantos jugadores por categoria


def season_id_for_year(tournament_id: int, year_str: str):
    seasons = sl.seasons_list(tournament_id)
    for s in seasons:
        if s.get("year") == year_str or s.get("name", "").endswith(year_str):
            return s["id"], s["name"]
    return None, None


def collect_top_players(tournament_id: int, season_id: int) -> pd.DataFrame:
    data = sl.get(f"/unique-tournament/{tournament_id}/season/{season_id}/top-players/overall")
    if not data or "topPlayers" not in data:
        return pd.DataFrame()
    rows = []
    seen = set()
    for stat_key in STAT_KEYS:
        entries = data["topPlayers"].get(stat_key, [])[:TOP_N]
        for rank, entry in enumerate(entries, start=1):
            p = entry.get("player", {})
            pid = p.get("id")
            if pid is None:
                continue
            rows.append({
                "player_id": pid,
                "name": p.get("name"),
                "position": p.get("position"),
                "team": entry.get("team", {}).get("name"),
                "team_id": entry.get("team", {}).get("id"),
                "stat_key": stat_key,
                "stat_value": entry.get("statistics", {}).get(stat_key),
                "rank_in_stat": rank,
            })
            seen.add(pid)
    return pd.DataFrame(rows)


def enrich_players(player_ids) -> pd.DataFrame:
    rows = []
    for pid in player_ids:
        d = sl.get(f"/player/{pid}")
        if not d or "player" not in d:
            continue
        p = d["player"]
        rows.append({
            "player_id": pid,
            "full_name": p.get("name"),
            "country": (p.get("country") or {}).get("name"),
            "height": p.get("height"),
            "preferred_foot": p.get("preferredFoot"),
            "date_of_birth_ts": p.get("dateOfBirthTimestamp"),
            "market_value_eur": p.get("proposedMarketValue"),
            "current_team": (p.get("team") or {}).get("name"),
            "current_team_id": (p.get("team") or {}).get("id"),
        })
    df = pd.DataFrame(rows)
    if not df.empty:
        df["birth_date"] = pd.to_datetime(df["date_of_birth_ts"], unit="s", errors="coerce")
        today = pd.Timestamp.now()
        df["age"] = ((today - df["birth_date"]).dt.days / 365.25).round(1)
    return df


def transfer_history(player_id: int) -> list:
    d = sl.get(f"/player/{player_id}/transfer-history")
    if not d:
        return []
    out = []
    for t in d.get("transferHistory", []):
        out.append({
            "player_id": player_id,
            "from_team": (t.get("transferFrom") or {}).get("name"),
            "from_team_id": (t.get("transferFrom") or {}).get("id"),
            "to_team": (t.get("transferTo") or {}).get("name"),
            "to_team_id": (t.get("transferTo") or {}).get("id"),
            "transfer_date_ts": t.get("transferDateTimestamp"),
            "fee": t.get("transferFeeDescription") or t.get("transferFeeRaw"),
        })
    return out


def main():
    all_rankings = []
    for league_key, tid in LEAGUES.items():
        for year in ("2026",):  # Sofascore no expone top-players de temporadas ya cerradas
            sid, sname = season_id_for_year(tid, year)
            if sid is None:
                print(f"  [skip] no se encontro temporada {year} para {league_key}")
                continue
            print(f"Bajando top-players: {league_key} {sname} (season_id={sid})...")
            df = collect_top_players(tid, sid)
            if df.empty:
                print("   -> vacio")
                continue
            df["league"] = league_key
            df["season_year"] = year
            df["season_id"] = sid
            all_rankings.append(df)
            print(f"   -> {df['player_id'].nunique()} jugadores unicos, {len(df)} filas de ranking")

    rankings = pd.concat(all_rankings, ignore_index=True) if all_rankings else pd.DataFrame()
    rankings.to_csv(RAW / "scouting_feeder_rankings.csv", index=False, encoding="utf-8-sig")
    print(f"\nTotal filas de ranking guardadas: {len(rankings)}")

    unique_ids = rankings["player_id"].dropna().unique().tolist() if not rankings.empty else []
    print(f"Enriqueciendo {len(unique_ids)} jugadores unicos con ficha individual (edad, valor, equipo actual)...")
    enriched = enrich_players(unique_ids)
    enriched.to_csv(PROC / "scouting_feeder_players_enriched.csv", index=False, encoding="utf-8-sig")
    print(f"Guardado: {len(enriched)} fichas de jugador en data/processed/scouting_feeder_players_enriched.csv")

    print(f"\nBajando historial de transferencias de {len(unique_ids)} jugadores destacados...")
    all_transfers = []
    for pid in unique_ids:
        all_transfers.extend(transfer_history(pid))
    df_transfers = pd.DataFrame(all_transfers)
    df_transfers.to_csv(PROC / "scouting_feeder_transfer_history.csv", index=False, encoding="utf-8-sig")
    print(f"Guardado: {len(df_transfers)} movimientos de transferencia")

    print("\nBajando historial de transferencias del plantel actual de Chacarita y rivales de Zona B "
          "(para ver de que categorias vienen los jugadores que hoy estan en Primera Nacional)...")
    zb_calendar = pd.read_csv(RAW / "zona_b_2026_calendario_completo.csv")
    zb_team_ids = pd.unique(zb_calendar[["home_id", "away_id"]].values.ravel())
    zb_players = []
    for tid in zb_team_ids:
        sq = sl.squad(int(tid))
        zb_players.extend(sq)
    df_zb_squads = pd.DataFrame(zb_players)
    df_zb_squads.to_csv(RAW / "zona_b_2026_planteles_completos.csv", index=False, encoding="utf-8-sig")
    print(f"   -> {len(df_zb_squads)} jugadores en los 18 planteles de Zona B")

    zb_unique_players = df_zb_squads["player_id"].dropna().unique().tolist()
    zb_transfers = []
    for i, pid in enumerate(zb_unique_players):
        zb_transfers.extend(transfer_history(int(pid)))
        if (i + 1) % 50 == 0:
            print(f"   ... {i+1}/{len(zb_unique_players)} jugadores de Zona B procesados")
    df_zb_transfers = pd.DataFrame(zb_transfers)
    df_zb_transfers.to_csv(PROC / "zona_b_planteles_transfer_history.csv", index=False, encoding="utf-8-sig")
    print(f"Guardado: {len(df_zb_transfers)} movimientos de transferencia de planteles de Zona B")


if __name__ == "__main__":
    main()
