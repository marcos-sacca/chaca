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


# orden cronológico real: por la fecha del primer partido (la Transición 2016 va antes que 2016/17, etc.)
_first = {}
for p in P:
    if p["Fecha calendario"] and (p["Temporada"] not in _first or p["Fecha calendario"] < _first[p["Temporada"]]):
        _first[p["Temporada"]] = p["Fecha calendario"]
seasons = sorted(set(seasons) | {p["Temporada"] for p in P}, key=lambda s: (_first.get(s, "9999"), skey(s)))
six = {s: i for i, s in enumerate(seasons)}

# --- partidos compactos: [temporada, fase, fechaN, fecha ISO, local, visitante, gl, gv]
phases = []
pix = {}
mlist = []
_mrow = []  # partido de partidos.csv de cada fila de mlist (para data/partidos_info.json)
for p in P:
    ph = p["Fase"]
    if ph not in pix:
        pix[ph] = len(phases); phases.append(ph)
    mlist.append([six[p["Temporada"]], pix[ph], num(p["Fecha torneo"], 0), p["Fecha calendario"], tix[p["Local"]], tix[p["Visitante"]], num(p["Goles local"]), num(p["Goles visitante"])] + ([1] if "aproximada" in p["Observaciones"].lower() else []))  # 9.º valor = fecha aproximada: la pantalla no la muestra
    _mrow.append(p)
_ord = sorted(range(len(mlist)), key=lambda i: (mlist[i][0], mlist[i][3], mlist[i][2]))
mlist = [mlist[i] for i in _ord]
_mrow = [_mrow[i] for i in _ord]

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
_PEN = re.compile(r"penales,? gan[óo] (.+?) (\d+)\s*[-a]\s*(\d+)", re.I)


def _team_in(txt, cands):
    """club de cands nombrado en txt (el nombre más largo que aparezca)"""
    t = txt.lower()
    hits = [c for c in cands if c is not None and (names[c].lower() in t or (EQ.get(names[c], {}).get("Nombre corto") or "").lower() in t or t in names[c].lower())]
    return max(hits, key=lambda c: len(names[c])) if hits else None


for r in RED:
    a_, b_ = tix.get(r["Local"]), tix.get(r["Visitante"])
    txt = (r["Observaciones"] or "") + " " + (r["Texto extra de la fuente"] or "")
    m = _PEN.search(txt)
    pen = [_team_in(m.group(1), [a_, b_]), f"{m.group(2)}-{m.group(3)}"] if m else None
    # [torneo, instancia, ida/vuelta, fecha, local, visitante, gl, gv, [ganador por penales, resultado] | null, alargue]
    reds[r["Temporada"]].append([r["Torneo"], r["Instancia"], r["Partido (ida/vuelta)"], r["Fecha calendario"], a_, b_, num(r["GL"]), num(r["GV"]), pen, 1 if re.search(r"tiempo suplementario|alargue", txt, re.I) else 0])

sdata = []
for s in seasons:
    t = next((x for x in TEMP if x["Temporada"] == s), {})
    sdata.append(dict(id=sid(s), label=s, teams=num(t.get("Equipos")), played=num(t.get("Partidos de fase regular")), ptsw=num(t.get("Puntos por victoria"), 3),
                      champion=champ.get(s), promoted=asc.get(s, []), tables=[dict(fase=f, rows=rows) for f, rows in tables.get(s, {}).items()],
                      sanciones=sanc.get(s, []), reducidos=reds.get(s, [])))

# --- zonas: la base no guarda a qué zona pertenecía cada club; se reconstruyen con los partidos (los de una misma
#     zona se enfrentan todos entre sí; con la otra, como mucho en la fecha interzonal). Cada club suma en su zona todos
#     sus partidos de fase regular, como en las tablas oficiales.
ZONA_A = {"2026": "Ferro Carril Oeste"}  # club conocido de la Zona A oficial, para nombrar bien las zonas


def _zones(ms):
    N = collections.defaultdict(set)
    for m in ms:
        N[m[4]].add(m[5]); N[m[5]].add(m[4])
    left, out = set(N), []
    while left:
        t = max(left, key=lambda x: (len(N[x]), -x))
        z = {u for u in left if u == t or len(N[t] & N[u]) >= .5 * min(len(N[t]), len(N[u]))}
        out.append(z); left -= z
    return out


for si, sd in enumerate(sdata):
    if len(sd["tables"]) != 1:
        continue
    ms = [m for m in mlist if m[0] == si]
    zs = _zones(ms)
    if len(zs) < 2 or min(len(z) for z in zs) < 4:
        continue
    anchor = tix.get(ZONA_A.get(sd["label"], ""))
    zs.sort(key=lambda z: (anchor not in z, min(names[t] for t in z)))
    letters = "ABCDEFGH" if anchor is not None else "12345678"
    ded = {x["club"]: x["pts"] for x in sd["sanciones"] if x.get("club") is not None}
    w = sd["ptsw"] or 3
    tabs = []
    for k, z in enumerate(zs):
        st = {t: [0, 0, 0, 0, 0, 0] for t in z}  # pj pg pe pp gf gc
        for m in ms:
            for t, gf, gc in ((m[4], m[6], m[7]), (m[5], m[7], m[6])):
                if t in st:
                    r = st[t]; r[0] += 1; r[4] += gf; r[5] += gc
                    r[1 if gf > gc else 2 if gf == gc else 3] += 1
        rows = sorted(([t, *r, r[4] - r[5], ded.get(t, 0), r[1] * w + r[2] - ded.get(t, 0)] for t, r in st.items()), key=lambda x: (-x[9], -x[7], -x[5], names[x[0]]))
        tabs.append(dict(fase=f"Zona {letters[k]}", zona=True, rows=[[i + 1, *r] for i, r in enumerate(rows)]))
    sd["tables"] = tabs + [dict(fase="General (las dos zonas juntas)" if len(zs) == 2 else "General (todas las zonas)", rows=sd["tables"][0]["rows"])]
    sd["zonas_reconstruidas"] = 1 if anchor is None else 2

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

# --- partidos de titular por jugador y club (formaciones confirmadas de Solo Ascenso, Primera Nacional desde 2014; para los juegos)
import gzip, sys as _sys
_sys.path.insert(0, str(ROOT.parent / "bnacional" / "tools"))
SA = ROOT.parent / "ascenso" / "data" / "sintesis_solo_ascenso.jsonl.gz"
titulares = {"p": []}
if SA.exists():
    from names_ext import best_among
    import datetime as _dt
    tmap, pj, pname = {"Talleres (R.E)": "Talleres de Remedios de Escalada"}, collections.defaultdict(collections.Counter), {}
    ppos = collections.defaultdict(collections.Counter)
    # solo formaciones de partidos que están en la base (misma fecha ±2 días y mismos equipos): deja afuera
    # los partidos de otras categorías mal rotulados en la fuente y el reducido
    known = set()
    for p in P:
        if p["Fecha calendario"] >= "2014":
            d0 = _dt.date.fromisoformat(p["Fecha calendario"])
            for k in range(-2, 3):
                known.add(((d0 + _dt.timedelta(days=k)).isoformat(), p["Local"], p["Visitante"]))
    with gzip.open(SA, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("cat") != "Primera Nacional" or "Confirmadas" not in r.get("head", ""):
                continue
            for team in (r["local"], r["visitante"]):
                if team not in tmap:
                    tmap[team] = best_among(team, names)[0]
            if (r["fecha"], tmap[r["local"]], tmap[r["visitante"]]) not in known:
                continue
            for side, team in ((0, r["local"]), (1, r["visitante"])):
                t = tmap[team]
                for x in r["eq"][side]["xi"]:
                    if len(x) > 4 and x[4]:
                        pj[x[4]][tix[t]] += 1
                        pname[x[4]] = x[1]
                        if len(x) > 3 and x[3]:
                            ppos[x[4]][x[3]] += 1
    for pid, c in pj.items():
        if len(c) >= 2 and sum(c.values()) >= 30:
            pos = ppos[pid].most_common(1)[0][0] if ppos[pid] else ""
            titulares["p"].append([pname[pid], sorted(([t, n] for t, n in c.items()), key=lambda x: -x[1]), pos])
    titulares["p"].sort(key=lambda x: x[0])
    titulares["nota"] = "Partidos como titular en la Primera Nacional desde 2014 (formaciones confirmadas de Solo Ascenso)."

# --- ficha de cada partido (se carga recién cuando alguien toca un partido): cancha, observaciones, goles y, desde 2014,
#     árbitro, minutos y link a la síntesis de Solo Ascenso. Una fila por partido, en el mismo orden que matches.json.
info = {"canchas": [], "arbitros": [], "p": []}
_cx, _ax = {}, {}
def _ix(tbl, idx, v):
    if not v:
        return -1
    if v not in idx:
        idx[v] = len(info[tbl]); info[tbl].append(v)
    return idx[v]
_gby = collections.defaultdict(list)
for g in G:
    _gby[g["ID Partido"]].append(g)
_sa = {}
if SA.exists():
    from names_ext import best_among as _ba
    _tm = {"Talleres (R.E)": "Talleres de Remedios de Escalada"}
    with gzip.open(SA, "rt", encoding="utf-8") as f:
        for line in f:
            r = json.loads(line)
            if r.get("cat") != "Primera Nacional" or not r.get("fecha"):
                continue
            for t in (r["local"], r["visitante"]):
                if t not in _tm:
                    _tm[t] = _ba(t, names)[0]
            _sa[(r["fecha"], _tm[r["local"]], _tm[r["visitante"]])] = r
import datetime as _dt
for p in _mrow:
    hg, ag = num(p["Goles local"]), num(p["Goles visitante"])
    sa = None
    if p["Fecha calendario"] >= "2014":
        d0 = _dt.date.fromisoformat(p["Fecha calendario"])
        for k in (0, -1, 1, -2, 2):
            sa = _sa.get(((d0 + _dt.timedelta(days=k)).isoformat(), p["Local"], p["Visitante"]))
            if sa:
                break
    goals = []
    if sa and sa.get("goles_lista") and sum(1 for x in sa["goles_lista"] if x.get("side") == 0) == hg and sum(1 for x in sa["goles_lista"] if x.get("side") == 1) == ag:
        for x in sa["goles_lista"]:
            goals.append([x["side"], x["player"], 2 if x.get("ec") else 1 if x.get("pen") else 0, x.get("min") or 0])
    else:
        for g in _gby.get(p["ID Partido"], []):
            side = 0 if g["Equipo que suma el gol"] == p["Local"] else 1
            goals.append([side, g["Jugador"], 2 if g["Tipo"] == "Gol en contra" else 1 if g["Tipo"] == "Gol de penal" else 0, 0])
    obs = re.sub(r"\s*(Pasado desde|Agregado por control|Interzonal pasado)[^.]*\.?", "", p["Observaciones"]).strip()
    info["p"].append([_ix("canchas", _cx, p["Cancha"]), _ix("arbitros", _ax, (sa or {}).get("arbitro") or ""), obs, goals, (sa or {}).get("id") or 0])

meta = dict(temporadas=len(seasons), clubes=len(names), partidos=len(P), goles=len(G), ascensos=len(ASC), ultimo=max(p["Fecha calendario"] for p in P), generado=__import__("datetime").date.today().isoformat())
for name, obj in (("meta", meta), ("teams", teams), ("seasons", sdata), ("phases", phases), ("players", players), ("matches", mlist), ("scorers", scorers), ("general", general), ("titulares", titulares), ("partidos_info", info)):
    (OUT / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(name, (OUT / f"{name}.json").stat().st_size // 1024, "KB")
print(meta)
