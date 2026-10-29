"""Planteles de los clubes que ascendieron, armados con las formaciones de Solo Ascenso (2014 en adelante).
Para cada ascenso: DT más frecuente y, por jugador, partidos jugados, titularidades, goles, puesto y edad.

  python3 -I tools/build_planteles.py        # escribe data/planteles.json
"""
import collections, csv, datetime, gzip, json, os, re, sys, unicodedata
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(ROOT), "bnacional", "tools"))
from names_ext import best_among  # noqa: E402
from clubes import R  # noqa: E402

SA = os.path.join(os.path.dirname(ROOT), "ascenso", "data", "sintesis_solo_ascenso.jsonl.gz")
DATA = os.path.join(os.path.dirname(ROOT), "bnacional", "data")
slug = lambda s: re.sub(r"[^a-z0-9]+", "-", unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()).strip("-")
nk = lambda s: re.sub(r"[^a-z ]", "", unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()).strip()
POS = {"arquero": 0, "defensor": 1, "mediocampista": 2, "delantero": 3}


def main():
    allc = sorted({v[0] for v in R.values()})
    asc = list(csv.DictReader(open(os.path.join(DATA, "ascensos.csv"), encoding="utf-8-sig")))
    P = list(csv.DictReader(open(os.path.join(DATA, "partidos.csv"), encoding="utf-8-sig")))
    dates = collections.defaultdict(list)
    for p in P:
        dates[p["Temporada"]].append(p["Fecha calendario"])
    win = {}
    for s, ds in dates.items():
        ds.sort(); n = len(ds)
        lo = datetime.date.fromisoformat(ds[int(.03 * n)]) - datetime.timedelta(days=7)
        hi = datetime.date.fromisoformat(ds[min(n - 1, int(.97 * n))]) + datetime.timedelta(days=7)
        win[s] = (lo.isoformat(), hi.isoformat())
    rows = []
    for ln in gzip.open(SA, "rt", encoding="utf-8"):
        r = json.loads(ln)
        if r.get("cat") == "Primera Nacional" and not r.get("sin_resultado") and any(e["xi"] for e in r["eq"]):
            rows.append(r)
    cache = {}
    def canon(n):
        if n not in cache:
            cache[n] = best_among(n, allc)[0]
        return cache[n]
    out = {}
    for a in asc:
        s, club = a["Temporada"], a["Club"]
        if s not in win or win[s][0] < "2014-01-01":
            continue
        lo, hi = win[s]
        agg, dts = {}, collections.Counter()
        npj = 0
        for r in rows:
            if not (lo <= r["fecha"] <= hi):
                continue
            side = 0 if canon(r["local"]) == club else 1 if canon(r["visitante"]) == club else None
            if side is None:
                continue
            npj += 1
            eq = r["eq"][side]
            if eq.get("dt"):
                dts[eq["dt"]] += 1
            entered = set()
            for part in re.split(r",\s+(?=\d+')", r.get("cambios", "") or ""):
                m = re.match(r"\d+'(?:\(\+\d+\))?\s*(.+?)\s+x\s+(.+?)\s*\(([^()]*)\)\s*$", part.strip())
                if m:
                    entered.add(m.group(1))
            sup_names = {x[1] for x in eq["sup"]}
            for x in eq["xi"]:
                o = agg.setdefault(x[4], dict(name=x[1], pos=collections.Counter(), pj=0, tit=0, g=0, age=x[2]))
                o["pj"] += 1; o["tit"] += 1; o["pos"][x[3]] += 1
            for x in eq["sup"]:
                if x[1] in entered:
                    o = agg.setdefault(x[4], dict(name=x[1], pos=collections.Counter(), pj=0, tit=0, g=0, age=x[2]))
                    o["pj"] += 1
            byname = {o["name"]: o for o in agg.values()}
            for g in r.get("goles_lista", []):
                if g.get("side") == side and not g.get("ec") and g.get("player") in byname:
                    byname[g["player"]]["g"] += 1
        if not agg:
            continue
        jug = []
        for o in agg.values():
            pos = next((p for p, _ in o["pos"].most_common() if p in POS), None)
            jug.append([o["name"], pos, o["pj"], o["tit"], o["g"], o["age"]])
        jug.sort(key=lambda j: (POS.get(j[1], 4), -j[2]))
        out[f"{slug(s.replace('/', '-'))}|{slug(club)}"] = dict(dt=dts.most_common(1)[0][0] if dts else None, pj=npj, jug=jug)
    json.dump(out, open(os.path.join(ROOT, "data", "planteles.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    print(len(out), "planteles;", sum(len(v["jug"]) for v in out.values()), "jugadores")
    for k, v in list(out.items())[:3]:
        print(k, v["dt"], v["pj"], v["jug"][:4])


if __name__ == "__main__":
    main()
