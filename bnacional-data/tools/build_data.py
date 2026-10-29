"""Genera los JSON del sitio bnacional-data a partir de los CSV de bnacional/data.

  python3 -I tools/build_data.py            # lee ../bnacional/data y escribe data/*.json
Opcional: data/fotos.json y data/videos.json (curados aparte) se copian tal cual.
"""
import csv, json, os, re, unicodedata, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT.parent / "bnacional" / "data"
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)


def rd(name):
    return list(csv.DictReader(open(SRC / name, encoding="utf-8-sig")))


def slug(s):
    s = unicodedata.normalize("NFD", s).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-")


def sid(season):  # id de temporada para la dirección: 1996/97 -> 1996-97
    return slug(season.replace("/", "-"))


def num(x, d=0):
    try:
        return int(float(x))
    except Exception:
        return d


P = rd("partidos.csv")
G = rd("goleadores.csv")
TS = rd("tabla_temporada.csv")
TG = rd("tabla_general.csv")
EQ = {e["Equipo"]: e for e in rd("equipos.csv")}
TEMP = rd("temporadas.csv")
ASC = rd("ascensos.csv")
RED = rd("reducidos.csv")

# --- clubes
names = sorted({p["Local"] for p in P} | {p["Visitante"] for p in P} | {r["Equipo"] for r in TG})
tix = {n: i for i, n in enumerate(names)}
slugs = {}
for n in names:
    s = slug(n)
    while s in slugs.values():
        s += "-x"
    slugs[n] = s
seasons = []
for t in TEMP:
    seasons.append(t["Temporada"])


def skey(s):
    m = re.match(r"(\d{4})", s)
    if s.startswith("Transición"):
        return (int(s.split()[-1]), 0.5)
    return (int(m.group(1)), 0 if "/" in s else 1)


seasons = sorted(set(seasons) | {p["Temporada"] for p in P}, key=skey)
six = {s: i for i, s in enumerate(seasons)}

# --- partidos compactos: [temporada, fase, fechaN, fecha ISO, local, visitante, gl, gv]
phases = []
pix = {}
mlist = []
for p in P:
    ph = p["Fase"]
    if ph not in pix:
        pix[ph] = len(phases); phases.append(ph)
    mlist.append([six[p["Temporada"]], pix[ph], num(p["Fecha torneo"], 0), p["Fecha calendario"], tix[p["Local"]], tix[p["Visitante"]], num(p["Goles local"]), num(p["Goles visitante"])])
mlist.sort(key=lambda m: (m[0], m[3], m[2]))

# --- goleadores por temporada / jugador / equipo
agg = collections.defaultdict(lambda: [0, 0])
for g in G:
    if g["Tipo"] == "Gol en contra":
        continue
    k = (g["Temporada"], g["Jugador"], g["Equipo del jugador"])
    agg[k][0] += 1
    agg[k][1] += 1 if g["Tipo"] == "Gol de penal" else 0
players = []
pxi = {}
scorers = []
for (s, j, t), (n, pen) in sorted(agg.items(), key=lambda kv: (six[kv[0][0]], -kv[1][0])):
    if j not in pxi:
        pxi[j] = len(players); players.append(j)
    scorers.append([six[s], pxi[j], tix[t], n, pen])

# --- tablas por temporada y fase
tables = collections.defaultdict(lambda: collections.OrderedDict())
for r in TS:
    tables[r["Temporada"]].setdefault(r["Fase"], []).append([num(r["Pos."]), tix[r["Equipo"]], num(r["PJ"]), num(r["PG"]), num(r["PE"]), num(r["PP"]), num(r["GF"]), num(r["GC"]), num(r["DG"]), num(r["Descuento"]), num(r["Pts"])])

# --- ascensos
asc = collections.defaultdict(list)
for a in ASC:
    asc[a["Temporada"]].append([tix[a["Club"]], a["Cómo ascendió"]])
champ = {s: next((c for c, h in v if h == "Campeón"), None) for s, v in asc.items()}

# --- reducidos y sanciones
sanc = collections.defaultdict(list)
for x in rd("sanciones.csv"):
    sanc[x["Temporada"]].append({"club": tix.get(x["Equipo"]), "pts": num(x["Puntos descontados"]), "motivo": x["Motivo"]})
reds = collections.defaultdict(list)
for r in RED:
    reds[r["Temporada"]].append([r["Torneo"], r["Instancia"], r["Partido (ida/vuelta)"], r["Fecha calendario"], tix.get(r["Local"]), tix.get(r["Visitante"]), num(r["GL"]), num(r["GV"])])

sdata = []
for s in seasons:
    t = next((x for x in TEMP if x["Temporada"] == s), {})
    sdata.append(dict(id=sid(s), label=s, teams=num(t.get("Equipos")), played=num(t.get("Partidos de fase regular")), ptsw=num(t.get("Puntos por victoria"), 3),
                      champion=champ.get(s), promoted=asc.get(s, []), tables=[dict(fase=f, rows=rows) for f, rows in tables.get(s, {}).items()],
                      sanciones=sanc.get(s, []), reducidos=reds.get(s, [])))

# --- descensos (clubes que estaban en la temporada, no ascendieron y ya no figuran en la siguiente) y reducidos
import re as _re
inseason = collections.defaultdict(set)
for m in mlist:
    inseason[m[0]].add(m[4]); inseason[m[0]].add(m[5])
RED_ASC = _re.compile(r"Reducido|Octogonal|Dodecagonal|Cuadrangular|Ronda Final|por el (?:1er|2do)\.? ?Ascenso", _re.I)
RED_PROMO = _re.compile(r"Promoci|Reválida|Descenso", _re.I)
for si, sd in enumerate(sdata):
    prom = {c for c, _ in sd["promoted"]}
    sd["desc"] = sorted(inseason[si] - inseason[si + 1] - prom) if (si + 1) in inseason else []
    red, pro = set(), set()
    for r in sd["reducidos"]:
        for c in (r[4], r[5]):
            if c is None:
                continue
            if RED_PROMO.search(r[0]):
                pro.add(c)
            elif RED_ASC.search(r[0]):
                red.add(c)
    sd["red"], sd["promo"] = sorted(red), sorted(pro)

teams = []
for n in names:
    e = EQ.get(n, {})
    teams.append(dict(n=n, s=slugs[n], short=e.get("Nombre corto") or n, prov=e.get("Provincia", ""), first=e.get("Primera temporada en la base", "")))
general = [[num(r["Pos."]), tix[r["Equipo"]], num(r["Temporadas"]), num(r["PJ"]), num(r["PG"]), num(r["PE"]), num(r["PP"]), num(r["GF"]), num(r["GC"]), num(r["DG"]), num(r["Descuento"]), num(r["Pts"]), num(r["Pts (3 x victoria)"])] for r in TG]
ranking = [[r["Jugador"], r["Equipo"], num(r["Goles"]), num(r["De penal"])] for r in rd("ranking_goleadores.csv")]

meta = dict(temporadas=len(seasons), clubes=len(names), partidos=len(P), goles=len(G), ascensos=len(ASC), ultimo=max(p["Fecha calendario"] for p in P), generado=__import__("datetime").date.today().isoformat())
for name, obj in (("meta", meta), ("teams", teams), ("seasons", sdata), ("phases", phases), ("players", players), ("matches", mlist), ("scorers", scorers), ("general", general)):
    (OUT / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(name, (OUT / f"{name}.json").stat().st_size // 1024, "KB")
print(meta)
