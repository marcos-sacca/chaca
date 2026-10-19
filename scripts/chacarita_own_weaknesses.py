"""
Debilidades propias de Chacarita: pelota parada (ofensiva/defensiva) y
patron de goles recibidos, para el cuerpo tecnico.

Fuente 1: data/processed/chacarita_partidos_stats.csv (ya en disco, de antes
del bloqueo de Sofascore) -> stats de equipo por partido: corners, duelos
aereos, centros, big chances.

Fuente 2 (nueva): SSR de sofascore.com via redirect /event/<id> -> pagina
completa del partido con __NEXT_DATA__.incidents (goles minuto a minuto,
asistencia, si fue penal). No pasa por la API bloqueada.
"""
import re
import json
import time
import sys
from pathlib import Path

from curl_cffi import requests
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "cache_web" / "chaca_matches"
CACHE_DIR.mkdir(parents=True, exist_ok=True)
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
SLEEP = 1.4
CHACA_ID = 3214


def parse_ratio(val):
    """Parsea formatos tipo '25/42 (60%)' -> (ganados, totales). None si no aplica."""
    if pd.isna(val):
        return None, None
    s = str(val)
    m = re.match(r"(\d+)/(\d+)", s)
    if m:
        return int(m.group(1)), int(m.group(2))
    m2 = re.match(r"(\d+)%?$", s.strip())
    if m2:
        return None, None
    try:
        return None, float(s)
    except ValueError:
        return None, None


def fetch_match_incidents(event_id: int):
    cpath = CACHE_DIR / f"{event_id}.json"
    if cpath.exists():
        with open(cpath, encoding="utf-8") as f:
            return json.load(f)
    url = f"https://www.sofascore.com/event/{event_id}"
    r = requests.get(url, headers=HEADERS, impersonate="chrome", timeout=20, allow_redirects=True)
    if r.status_code != 200:
        return None
    m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', r.text, re.DOTALL)
    if not m:
        return None
    data = json.loads(m.group(1))
    pp = data.get("props", {}).get("pageProps", {})
    result = {
        "event": pp.get("event", {}),
        "incidents": pp.get("incidents", []),
    }
    with open(cpath, "w", encoding="utf-8") as f:
        json.dump(result, f)
    time.sleep(SLEEP)
    return result


def main():
    partidos = pd.read_csv(ROOT / "data/raw/chacarita_partidos.csv")
    stats = pd.read_csv(ROOT / "data/processed/chacarita_partidos_stats.csv")

    pn26 = partidos[(partidos["season"] == "Primera Nacional 2026") & partidos["home_score"].notna()].copy()
    pn26 = pn26.sort_values("start_timestamp").reset_index(drop=True)
    print(f"Partidos validos PN2026: {len(pn26)}")

    # ---- Parte A: agregados de pelota parada / duelos aereos (ya en disco) ----
    merged = pn26.merge(stats, on="event_id", suffixes=("", "_s"))
    rows = []
    for _, r in merged.iterrows():
        is_home = "Chacarita" in str(r["home_team"])
        pref_us, pref_rival = ("home_", "away_") if is_home else ("away_", "home_")
        gf = r["home_score"] if is_home else r["away_score"]
        ga = r["away_score"] if is_home else r["home_score"]
        rival = r["away_team"] if is_home else r["home_team"]
        def g(col):
            v = r.get(pref_us + col)
            return v if pd.notna(v) else None
        def g_r(col):
            v = r.get(pref_rival + col)
            return v if pd.notna(v) else None
        aereos_favor_won, aereos_favor_tot = parse_ratio(g("Aerial duels"))
        aereos_contra_won, aereos_contra_tot = parse_ratio(g_r("Aerial duels"))
        centros_favor_ok, centros_favor_tot = parse_ratio(g("Crosses"))
        centros_contra_ok, centros_contra_tot = parse_ratio(g_r("Crosses"))
        rows.append({
            "round": r["round"], "rival": rival, "local": is_home, "gf": gf, "ga": ga,
            "corners_favor": g("Corner kicks"), "corners_contra": g_r("Corner kicks"),
            "aereos_ganados_favor": aereos_favor_won, "aereos_totales_favor": aereos_favor_tot,
            "aereos_ganados_contra": aereos_contra_won, "aereos_totales_contra": aereos_contra_tot,
            "centros_ok_favor": centros_favor_ok, "centros_int_favor": centros_favor_tot,
            "centros_ok_contra": centros_contra_ok, "centros_int_contra": centros_contra_tot,
            "big_chances_favor": g("Big chances"), "big_chances_contra": g_r("Big chances"),
            "big_chances_missed": g("Big chances missed"),
            "touches_penalty_area_favor": g("Touches in penalty area"),
            "touches_penalty_area_contra": g_r("Touches in penalty area"),
        })
    setpiece_df = pd.DataFrame(rows)
    setpiece_df.to_csv(ROOT / "data/processed/chacarita_setpiece_aggregado_2026.csv", index=False, encoding="utf-8-sig")
    print("\n=== AGREGADO SEASON-LONG (pelota parada / duelos) ===")
    n = len(setpiece_df)
    print(f"Partidos con datos: {n}")
    print(f"Corners a favor/partido: {setpiece_df['corners_favor'].mean():.2f} | en contra/partido: {setpiece_df['corners_contra'].mean():.2f}")
    tot_aereos_favor_w = setpiece_df['aereos_ganados_favor'].sum()
    tot_aereos_favor_t = setpiece_df['aereos_totales_favor'].sum()
    tot_aereos_contra_w = setpiece_df['aereos_ganados_contra'].sum()
    tot_aereos_contra_t = setpiece_df['aereos_totales_contra'].sum()
    if tot_aereos_favor_t:
        print(f"Duelos aereos GANADOS por Chacarita: {tot_aereos_favor_w:.0f}/{tot_aereos_favor_t:.0f} = {100*tot_aereos_favor_w/tot_aereos_favor_t:.1f}%")
    if tot_aereos_contra_t:
        print(f"Duelos aereos GANADOS por el RIVAL: {tot_aereos_contra_w:.0f}/{tot_aereos_contra_t:.0f} = {100*tot_aereos_contra_w/tot_aereos_contra_t:.1f}%")
    print(f"Centros propios/partido intentados: {setpiece_df['centros_int_favor'].mean():.2f} (acierto {100*setpiece_df['centros_ok_favor'].sum()/setpiece_df['centros_int_favor'].sum():.1f}%)")
    print(f"Centros rival/partido intentados: {setpiece_df['centros_int_contra'].mean():.2f} (acierto rival {100*setpiece_df['centros_ok_contra'].sum()/setpiece_df['centros_int_contra'].sum():.1f}%)")
    if setpiece_df['big_chances_favor'].notna().sum() > 5:
        print(f"Big chances a favor/partido: {setpiece_df['big_chances_favor'].mean():.2f} | en contra/partido: {setpiece_df['big_chances_contra'].mean():.2f}")
    else:
        print("Big chances: columna casi vacia en la fuente (1/84 partidos) -- no se reporta, dato no confiable.")

    # ---- Parte B: log de goles gol-a-gol via SSR (nuevo) ----
    print("\n=== Descargando incidentes partido por partido (SSR, sin API) ===")
    goles_favor = []
    goles_contra = []
    partidos_no_confiables = []
    for i, r in pn26.iterrows():
        eid = int(r["event_id"])
        is_home = "Chacarita" in str(r["home_team"])
        data = fetch_match_incidents(eid)
        expected_total = int(r["home_score"]) + int(r["away_score"])
        if not data:
            print(f"  [{r['round']}] {r['home_team']} vs {r['away_team']}: SIN DATOS (fetch fallo)")
            partidos_no_confiables.append(r["round"])
            continue
        incidents = data["incidents"]
        goal_incidents = [inc for inc in incidents if inc.get("incidentType") == "goal"]
        n_goals = len(goal_incidents)
        confiable = (n_goals == expected_total)
        estado = "OK" if confiable else f"DESCARTADO (esperaba {expected_total}, incidents trae {n_goals} -- pagina SSR sin datos completos para partidos viejos)"
        print(f"  [{r['round']:>2}] {r['home_team'][:28]:28s} vs {r['away_team'][:28]:28s} -> {estado}")
        if not confiable:
            partidos_no_confiables.append(r["round"])
            continue
        for inc in goal_incidents:
            scored_by_home = inc.get("isHome")
            es_gol_nuestro = (scored_by_home == is_home)
            rec = {
                "round": r["round"], "rival": r["away_team"] if is_home else r["home_team"],
                "local": is_home, "minuto": inc.get("time"), "tiempo_extra": inc.get("addedTime"),
                "jugador": (inc.get("player") or {}).get("name"),
                "asistencia": (inc.get("assist1") or {}).get("name") if inc.get("assist1") else None,
                "penal": inc.get("incidentClass") == "penalty",
                "en_contra_propia": inc.get("incidentClass") == "owngoal",
                "marcador_local": inc.get("homeScore"), "marcador_visitante": inc.get("awayScore"),
            }
            (goles_favor if es_gol_nuestro else goles_contra).append(rec)

    print(f"\nPartidos con datos de incidentes CONFIABLES: {len(pn26) - len(partidos_no_confiables)}/{len(pn26)}")
    print(f"Fechas descartadas por datos incompletos en el SSR: {sorted(partidos_no_confiables)}")

    gf_df = pd.DataFrame(goles_favor)
    gc_df = pd.DataFrame(goles_contra)
    gf_df.to_csv(ROOT / "data/processed/chacarita_goles_favor_2026.csv", index=False, encoding="utf-8-sig")
    gc_df.to_csv(ROOT / "data/processed/chacarita_goles_contra_2026.csv", index=False, encoding="utf-8-sig")

    print(f"\nTotal goles a favor reconstruidos: {len(gf_df)}")
    print(f"Total goles en contra reconstruidos: {len(gc_df)}")

    if not gc_df.empty:
        print("\n=== GOLES EN CONTRA: distribucion por minuto ===")
        bins = [0, 15, 30, 45, 60, 75, 90, 200]
        labels = ["0-15", "16-30", "31-45", "46-60", "61-75", "76-90", "90+"]
        gc_df["bucket"] = pd.cut(gc_df["minuto"], bins=bins, labels=labels, right=True)
        print(gc_df["bucket"].value_counts().reindex(labels))
        print(f"\nCon asistencia registrada (posible centro/combinacion): {gc_df['asistencia'].notna().sum()} de {len(gc_df)}")
        print(f"De penal: {gc_df['penal'].sum()} | en contra propia: {gc_df['en_contra_propia'].sum()}")

    if not gf_df.empty:
        print("\n=== GOLES A FAVOR: distribucion por minuto ===")
        gf_df["bucket"] = pd.cut(gf_df["minuto"], bins=bins, labels=labels, right=True)
        print(gf_df["bucket"].value_counts().reindex(labels))
        print(f"\nCon asistencia registrada: {gf_df['asistencia'].notna().sum()} de {len(gf_df)}")
        print(f"De penal: {gf_df['penal'].sum()}")


if __name__ == "__main__":
    main()
