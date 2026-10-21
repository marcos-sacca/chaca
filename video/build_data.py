"""
Arma los pasos del video "Chacarita fecha por fecha" a partir de la cache de
Sofascore (data/cache/*events_round_*.json, bajada por scripts/fetch_zone_b.py).

Un paso = un partido de Chacarita (en el orden en que se jugo de verdad) y la
tabla de la Zona B con TODO lo jugado hasta el cierre de ese dia, incluidas las
fechas interzonales (7 y 25), que el calendario de fetch_zone_b.py descarta.

Salida: video/out/steps.json
No hace requests: lee solo la cache. Para traer fechas nuevas, correr antes
video/refresh_data.py (necesita acceso a api.sofascore.com).
"""
import glob
import json
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE = ROOT / "data" / "cache"
OUT = Path(__file__).resolve().parent / "out"

TOURNAMENT_ID = 703
SEASON_ID = 87940
CHACARITA_ID = 3214
AR = timezone(timedelta(hours=-3))

SHORT = {
    "Agropecuario Argentino": "Agropecuario",
    "Club Atlético Chacarita Juniors": "Chacarita",
    "Gimnasia Y Esgrima De Jujuy": "Gimnasia (J)",
    "Gimnasia y Tiro de Salta": "Gimnasia y Tiro",
    "Atlético de Rafaela": "Atlético Rafaela",
    "Deportivo Maipú": "Maipú",
    "Ferrocarril Midland": "Midland",
    "Quilmes Atlético Club": "Quilmes",
    "San Martín de San Juan": "San Martín",
    "San Martín de Tucumán": "San Martín (T)",
    "Nueva Chicago": "Chicago",
}


def short(name):
    return SHORT.get(name, name)


def local(ts):
    return datetime.fromtimestamp(ts, AR)


def load_events():
    evs = []
    pattern = f"unique-tournament_{TOURNAMENT_ID}_season_{SEASON_ID}_events_round_*.json"
    for f in sorted(glob.glob(str(CACHE / pattern))):
        for e in json.load(open(f, encoding="utf-8")).get("events", []):
            evs.append(
                dict(
                    id=e["id"],
                    round=(e.get("roundInfo") or {}).get("round"),
                    home=e["homeTeam"]["id"],
                    away=e["awayTeam"]["id"],
                    hs=(e.get("homeScore") or {}).get("current"),
                    as_=(e.get("awayScore") or {}).get("current"),
                    ts=e["startTimestamp"],
                    status=e["status"]["description"],
                    teams={
                        e["homeTeam"]["id"]: e["homeTeam"],
                        e["awayTeam"]["id"]: e["awayTeam"],
                    },
                )
            )
    return evs


def dedupe(evs):
    """Un partido reprogramado aparece dos veces (el 'Postponed' original y el
    jugado, con otro id). Nos quedamos con el definitivo y guardamos la fecha
    original (orig_ts) para poder mostrar 'partido pendiente'."""
    groups = defaultdict(list)
    for e in evs:
        groups[(e["round"], e["home"], e["away"])].append(e)
    out = []
    for g in groups.values():
        g.sort(key=lambda e: e["ts"])
        final = next((e for e in g if e["status"] == "Ended"), g[-1])
        if final["status"] == "Postponed" and len(g) > 1:
            final = g[-1]
        final = dict(final)
        final["orig_ts"] = g[0]["ts"]
        out.append(final)
    return out


def apply_manual(evs):
    """Pisa los placeholders 'Not started' de la cache con los resultados cargados
    a mano (video/data/chacarita_f29_f34_manual.json). Si la cache ya trae el
    partido jugado (despues de refresh_data.py), el dato real manda. Devuelve cuantos aplico."""
    path = Path(__file__).resolve().parent / "data" / "chacarita_f29_f34_manual.json"
    if not path.exists():
        return 0
    by_name = {}
    for e in evs:
        for tid, t in e["teams"].items():
            by_name[short(t["name"])] = tid
    n = 0
    for m in json.load(open(path, encoding="utf-8"))["matches"]:
        h, a = by_name[m["home"]], by_name[m["away"]]
        for e in evs:
            if e["round"] == m["round"] and e["home"] == h and e["away"] == a and e["status"] != "Ended":
                ts = int(datetime.fromisoformat(m["date"] + "T18:00:00").replace(tzinfo=AR).timestamp())
                e.update(hs=m["hs"], as_=m["as"], status="Ended", ts=ts, orig_ts=ts)
                n += 1
    return n


def apply_results_csv(evs):
    """Completa partidos sin resultado desde video/data/resultados_faltantes.csv
    (columnas: fecha, dia, local, visitante, goles_local, goles_visitante).
    Solo se usan las filas con los dos goles cargados. 'dia' (AAAA-MM-DD) es el dia
    en que se jugo; si queda vacio se mantiene el de la cache. Devuelve cuantas aplico."""
    import csv

    path = Path(__file__).resolve().parent / "data" / "resultados_faltantes.csv"
    if not path.exists():
        return 0
    by_name = {}
    for e in evs:
        for tid, t in e["teams"].items():
            by_name[short(t["name"])] = tid
    n = 0
    with open(path, encoding="utf-8-sig") as f:
        for row in csv.DictReader(f):
            if row["goles_local"].strip() == "" or row["goles_visitante"].strip() == "":
                continue
            h, a = by_name[row["local"].strip()], by_name[row["visitante"].strip()]
            for e in evs:
                if e["round"] == int(row["fecha"]) and e["home"] == h and e["away"] == a and e["status"] != "Ended":
                    e.update(hs=int(row["goles_local"]), as_=int(row["goles_visitante"]), status="Ended")
                    if row["dia"].strip():
                        e["ts"] = int(datetime.fromisoformat(row["dia"].strip() + "T18:00:00").replace(tzinfo=AR).timestamp())
                    n += 1
    return n


def standings(matches, teams, cutoff_ts):
    st = {t: dict(pts=0, pj=0, gf=0, gc=0, g=0, e=0, p=0, form=[]) for t in teams}
    for m in sorted(matches, key=lambda m: m["ts"]):
        if m["status"] != "Ended" or m["ts"] >= cutoff_ts or m["hs"] is None:
            continue
        for tid, gf, gc in ((m["home"], m["hs"], m["as_"]), (m["away"], m["as_"], m["hs"])):
            if tid not in st:
                continue
            s = st[tid]
            s["pj"] += 1
            s["gf"] += gf
            s["gc"] += gc
            if gf > gc:
                s["pts"] += 3
                s["g"] += 1
                s["form"].append("V")
            elif gf == gc:
                s["pts"] += 1
                s["e"] += 1
                s["form"].append("E")
            else:
                s["p"] += 1
                s["form"].append("D")
    rows = []
    for tid, s in st.items():
        rows.append(dict(team=tid, **{k: v for k, v in s.items() if k != "form"}, dg=s["gf"] - s["gc"], form=s["form"][-5:]))
    rows.sort(key=lambda r: (-r["pts"], -r["dg"], -r["gf"], teams[r["team"]]["name"]))
    for i, r in enumerate(rows, 1):
        r["pos"] = i
    return rows


def day_end(ts):
    d = local(ts)
    return int((d.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).timestamp())


def main():
    evs = dedupe(load_events())
    manual = apply_manual(evs)
    from_csv = apply_results_csv(evs)
    # Zona B: los 18 equipos del calendario que bajo scripts/fetch_zone_b.py
    # (partidos entre si). Las interzonales traen rivales de la otra zona.
    import csv
    with open(ROOT / "data" / "raw" / "zona_b_2026_calendario_completo.csv", encoding="utf-8-sig") as f:
        zone = {int(r["home_id"]) for r in csv.DictReader(f)}
    teams = {}
    for e in evs:
        for tid, t in e["teams"].items():
            if tid in zone or CHACARITA_ID in (e["home"], e["away"]):
                teams[tid] = t
    zone_teams = {tid: t for tid, t in teams.items() if tid in zone}
    assert len(zone) == 18, f"se esperaban 18 equipos de Zona B, hay {len(zone)}"

    matches = [e for e in evs if e["home"] in zone or e["away"] in zone]
    chac = [e for e in evs if CHACARITA_ID in (e["home"], e["away"])]
    played = sorted((e for e in chac if e["status"] == "Ended"), key=lambda e: e["ts"])
    last_round_played = max((e["round"] for e in played), default=0)

    def round_close(r):
        """Ultimo partido de la fecha r jugado 'en fecha' (a lo sumo 5 dias
        despues de lo previsto; mas que eso es un partido recuperado)."""
        ts = [x["ts"] for x in matches if x["round"] == r and x["status"] in ("Ended", "Not started") and x["ts"] - x["orig_ts"] <= 5 * 86400]
        return max(ts) if ts else 0

    steps = []

    skipped = []

    def add(kind, m, ts_for_table, label_ts, note=None):
        cutoff = day_end(ts_for_table)
        # Faltan resultados del resto de la zona (cache vieja): la tabla seria
        # falsa, asi que no se genera la pantalla en vez de inventarla.
        stale = [x for x in matches if x["status"] == "Not started" and x["ts"] < cutoff]
        if stale:
            skipped.append((m["round"], local(label_ts).strftime("%d/%m"), len(stale)))
            return
        table = standings(matches, zone_teams, cutoff)
        me = next(r for r in table if r["team"] == CHACARITA_ID)
        steps.append(
            dict(
                kind=kind,
                round=m["round"],
                date=local(label_ts).strftime("%d/%m/%Y"),
                table_date=local(ts_for_table).strftime("%d/%m/%Y"),  # cierre de la fecha: lo que muestra el encabezado
                home=m["home"],
                away=m["away"],
                hs=m["hs"] if kind != "pending" else None,
                as_=m["as_"] if kind != "pending" else None,
                note=note,
                chac_pos=me["pos"],
                chac_pts=me["pts"],
                table=table,
                _ts=label_ts,
            )
        )

    for m in played:
        postponed = m["orig_ts"] != m["ts"] and m["orig_ts"] < m["ts"]
        between = [p for p in played if m["orig_ts"] < p["ts"] < m["ts"] and p["round"] > m["round"]]
        close = round_close(m["round"])
        if postponed and between:
            close = max(close, m["orig_ts"])
            add("pending", m, close, close, note="PARTIDO PENDIENTE AL CIERRE DE ESTA FECHA")
            add("recovered", m, m["ts"], m["ts"], note=f"RECUPERADO · se postergó del {local(m['orig_ts']).strftime('%d/%m')}")
        else:
            # tabla al cierre de la fecha (como el video original), con tope de 3 dias
            base = max(m["ts"], min(close, m["ts"] + 3 * 86400))
            add("played", m, base, m["ts"])

    steps.sort(key=lambda s: (s["_ts"], 0 if s["kind"] == "pending" else 1))
    for s in steps:
        del s["_ts"]

    OUT.mkdir(parents=True, exist_ok=True)
    meta = {
        str(tid): dict(
            name=short(t["name"]),
            code=t.get("nameCode") or short(t["name"])[:3].upper(),
            primary=(t.get("teamColors") or {}).get("primary", "#444444"),
            secondary=(t.get("teamColors") or {}).get("secondary", "#ffffff"),
        )
        for tid, t in teams.items()
    }
    json.dump(dict(chacarita=CHACARITA_ID, last_round=last_round_played, teams=meta, steps=steps),
              open(OUT / "steps.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(steps)} pasos con datos completos (Chacarita jugo hasta la fecha {last_round_played}; {manual} partidos de Chacarita cargados a mano, {from_csv} del resto de la zona desde la planilla)")
    for r, d, n in skipped:
        print(f"  SIN GENERAR fecha {r} ({d}): faltan {n} resultados de otros partidos de la zona en la cache")
    for s in steps:
        print(f"  F{s['round']:>2} {s['date']} {s['kind']:<9} {meta[str(s['home'])]['name']} {s['hs']}-{s['as_']} {meta[str(s['away'])]['name']}  -> {s['chac_pos']}º {s['chac_pts']} pts")


if __name__ == "__main__":
    main()
