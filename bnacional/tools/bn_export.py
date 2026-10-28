"""Convierte el resultado crudo de bn_build.py en las tablas finales (CSV + Excel).

Uso: python3 -I bn_export.py <crudo.json> <salida_dir> [correcciones.csv]
Salidas: partidos, goleadores, reducidos, sanciones, equipos, estadios, control_fuente, fuentes, errores,
tabla_general, tabla_temporada, temporadas_por_equipo, ranking_goleadores (CSV) y B_Nacional_historico.xlsx.
"""
import collections, csv, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from clubes import R, nkk  # noqa: E402

COLS_PARTIDOS = ["ID Partido", "Temporada", "Fase", "Fecha torneo", "Fecha calendario", "Ciudad", "Cancha", "Origen dato cancha", "Local", "Visitante", "Goles local", "Goles visitante", "Resultado (L/E/V)", "Pts local", "Pts visitante", "Estado", "Control goles", "Observaciones", "Local (nombre en fuente)", "Visitante (nombre en fuente)", "ID Fuente"]
COLS_GOLES = ["ID Gol", "ID Partido", "Temporada", "Fecha torneo", "Fecha calendario", "Equipo que suma el gol", "Jugador", "Equipo del jugador", "Tipo", "Nombre en fuente", "Detalle", "ID Fuente"]


def strip(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def tokens(name):
    return [t for t in re.sub(r"[^a-z ]", " ", strip(name)).split() if t]


class Players:
    """Unifica variantes de un mismo jugador dentro de un equipo (iniciales, tildes, apellido solo)."""

    def __init__(self):
        self.groups = collections.defaultdict(list)  # (equipo, apellido) -> [variantes canónicas]
        self.freq = collections.Counter()

    def key(self, team, name):
        t = tokens(name)
        full = [x for x in t if len(x) > 1]
        sur = full[-1] if full else (t[-1] if t else "")
        return sur

    def register(self, team, name):
        self.freq[(team, name)] += 1
        sur = self.key(team, name)
        lst = self.groups[(team, sur)]
        if name not in lst:
            lst.append(name)

    def compatible(self, a, b):
        ta, tb = tokens(a), tokens(b)
        fa, fb = ta[:-1], tb[:-1]
        if not fa or not fb:
            return True
        if ta[-1] != tb[-1] and not (len(ta) > 2 and ta[-1] != tb[-1]):
            pass
        # los nombres de pila / iniciales deben ser compatibles posición a posición (primer nombre)
        x, y = fa[0], fb[0]
        return x[0] == y[0] and (len(x) == 1 or len(y) == 1 or x == y or x.startswith(y) or y.startswith(x))

    def canon(self, team, name):
        sur = self.key(team, name)
        cands = [v for v in self.groups.get((team, sur), []) if self.compatible(name, v)]
        if not cands:
            return name
        # la variante más completa y más frecuente
        cands.sort(key=lambda v: (-len([x for x in tokens(v) if len(x) > 1]), -self.freq[(team, v)], len(v)))
        return cands[0]


def main(crudo, out, fixes_csv=None):
    os.makedirs(out, exist_ok=True)
    d = json.load(open(crudo, encoding="utf-8"))
    P, RED = d["partidos"], d["reducidos"]
    order = {}
    for i, m in enumerate(P):
        order[id(m)] = i
    # temporadas en orden cronológico
    def sort_key(m):
        return (m["code"] if not m["code"].startswith("T") else m["code"][1:] + "9", m["date"], d["partidos"].index(m) if False else order.get(id(m), 0))
    P.sort(key=lambda m: (m["date"], order[id(m)]))
    def skey(x):
        mm = re.match(r"(Transición )?(\d{4})", x)
        if mm.group(1):
            return {"2014": 2014.5, "2016": 2015.75}.get(mm.group(2), int(mm.group(2)) + 0.5)
        return int(mm.group(2)) + (0.0 if "/" in x else 0.25)
    seasons_order = sorted({m["season"] for m in P}, key=skey)
    cnt = collections.Counter()
    for m in P:
        cnt[m["code"]] += 1
        m["id"] = f"{m['code']}-{cnt[m['code']]:03d}"
    rc = collections.Counter()
    for m in sorted(RED, key=lambda x: x["date"]):
        rc[m["code"]] += 1
        m["id"] = f"RED-{m['code']}-{rc[m['code']]:02d}"
    # jugadores
    pl = Players()
    for m in P + RED:
        for side, team in (("hs", m["home"]), ("as_", m["away"])):
            for s in m[side]:
                if not s["ec"]:
                    pl.register(team, s["n"])
        # gol en contra: el jugador es del equipo contrario
        for side, other in (("hs", m["away"]), ("as_", m["home"])):
            for s in m[side]:
                if s["ec"]:
                    pl.register(other, s["n"])
    # CSV partidos y goles
    rows_p, rows_g = [], []
    for m in P:
        hg, ag = m["hg"], m["ag"]
        res = "L" if hg > ag else "V" if ag > hg else "E"
        w = m["ptsw"]
        pl_, pv_ = (w, 0) if res == "L" else (0, w) if res == "V" else (1, 1)
        n_h = sum(s["k"] for s in m["hs"] if not s["ec"]) + sum(s["k"] for s in m["as_"] if s["ec"])
        n_a = sum(s["k"] for s in m["as_"] if not s["ec"]) + sum(s["k"] for s in m["hs"] if s["ec"])
        ctrl = "OK" if (n_h, n_a) == (hg, ag) else ("Sin goleadores" if n_h + n_a == 0 and hg + ag > 0 else f"Revisar: la fuente lista {n_h}-{n_a} goleadores y el resultado es {hg}-{ag}")
        rows_p.append([m["id"], m["season"], m["fase"], m["fecha_n"], m["date"], m["city"], m["cancha"], m["origen"], m["home"], m["away"], hg, ag, res, pl_, pv_, m["estado"], ctrl, m["obs"], m["hsrc"], m["asrc"], m["src"]])
        seq = 0
        for side, team, rival in (("hs", m["home"], m["away"]), ("as_", m["away"], m["home"])):
            for s in m[side]:
                for i in range(s["k"]):
                    seq += 1
                    if s["ec"]:
                        tipo, jug, eq = "Gol en contra", pl.canon(rival, s["n"]), rival
                    else:
                        tipo = "Gol de penal" if i < s["pen"] else "Gol"
                        jug, eq = pl.canon(team, s["n"]), team
                    rows_g.append([f"G-{m['id']}-{seq:02d}", m["id"], m["season"], m["fecha_n"], m["date"], team, jug, eq, tipo, s["n"], "", m["src"]])
    rows_r = []
    for m in sorted(RED, key=lambda x: x["id"]):
        gl = "; ".join(f"{s['n']}" + (f" {s['k']}" if s["k"] > 1 else "") + (" (p)" if s["pen"] else "") + (" (e/c)" if s["ec"] else "") for s in m["hs"])
        gv = "; ".join(f"{s['n']}" + (f" {s['k']}" if s["k"] > 1 else "") + (" (p)" if s["pen"] else "") + (" (e/c)" if s["ec"] else "") for s in m["as_"])
        rows_r.append([m["id"], m["season"], m["fase"], m.get("stage") or "", m.get("leg") or "", m["date"], m["city"], m["cancha"], m["origen"], m["home"], m["away"], m["hg"], m["ag"], gl, gv, m["estado"], m["obs"], m["src"], m.get("extra", "")])
    wr = lambda name, head, rows: csv_write(os.path.join(out, name), head, rows)
    wr("partidos.csv", COLS_PARTIDOS, rows_p)
    wr("goleadores.csv", COLS_GOLES, rows_g)
    wr("reducidos.csv", ["ID Partido", "Temporada", "Torneo", "Instancia", "Partido (ida/vuelta)", "Fecha calendario", "Ciudad", "Cancha", "Origen dato cancha", "Local", "Visitante", "GL", "GV", "Goleadores local", "Goleadores visitante", "Estado", "Observaciones", "ID Fuente", "Texto extra de la fuente"], rows_r)
    # tablas
    tg = collections.defaultdict(lambda: dict(pj=0, pg=0, pe=0, pp=0, gf=0, gc=0, pts=0, pts3=0, temporadas=set()))
    ded = collections.defaultdict(int)
    for x in d["sanciones"]:
        if not x["red"]:
            ded[(x["season"], x["team"])] += x["pts"]
    ts = collections.defaultdict(lambda: collections.defaultdict(lambda: dict(pj=0, pg=0, pe=0, pp=0, gf=0, gc=0, pts=0, pts3=0)))
    for m in P:
        for team, gf, gc in ((m["home"], m["hg"], m["ag"]), (m["away"], m["ag"], m["hg"])):
            for t in (tg[team], ts[(m["season"], m["fase"])][team]):
                t["pj"] += 1
                t["gf"] += gf
                t["gc"] += gc
                if gf > gc:
                    t["pg"] += 1
                    t["pts"] += m["ptsw"]
                    t["pts3"] += 3
                elif gf == gc:
                    t["pe"] += 1
                    t["pts"] += 1
                    t["pts3"] += 1
                else:
                    t["pp"] += 1
            tg[team]["temporadas"].add(m["season"])
    for (s, team), v in ded.items():
        if team in tg:
            tg[team]["pts"] -= v
            tg[team]["pts3"] -= v
    rows = sorted(tg.items(), key=lambda kv: (-kv[1]["pts3"], -(kv[1]["gf"] - kv[1]["gc"]), -kv[1]["gf"], kv[0]))
    wr("tabla_general.csv", ["Pos.", "Equipo", "Temporadas", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "Descuento", "Pts", "Pts (3 x victoria)"],
       [[i + 1, t, len(v["temporadas"]), v["pj"], v["pg"], v["pe"], v["pp"], v["gf"], v["gc"], v["gf"] - v["gc"], sum(x for (s, tm), x in ded.items() if tm == t), v["pts"], v["pts3"]] for i, (t, v) in enumerate(rows)])
    rows_t = []
    for (s, fase), tab in sorted(ts.items(), key=lambda kv: (seasons_order.index(kv[0][0]), kv[0][1])):
        lst = sorted(tab.items(), key=lambda kv: (-(kv[1]["pts"] - ded.get((s, kv[0]), 0)), -(kv[1]["gf"] - kv[1]["gc"]), -kv[1]["gf"], kv[0]))
        for i, (t, v) in enumerate(lst):
            dd = ded.get((s, t), 0)
            rows_t.append([s, fase, i + 1, t, v["pj"], v["pg"], v["pe"], v["pp"], v["gf"], v["gc"], v["gf"] - v["gc"], dd, v["pts"] - dd])
    wr("tabla_temporada.csv", ["Temporada", "Fase", "Pos.", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "Descuento", "Pts"], rows_t)
    # ranking goleadores
    rk = collections.Counter(), collections.Counter()
    for g in rows_g:
        if g[8] != "Gol en contra":
            rk[0][(g[6], g[7])] += 1
            if g[8] == "Gol de penal":
                rk[1][(g[6], g[7])] += 1
    rr = sorted(rk[0].items(), key=lambda kv: (-kv[1], kv[0]))
    wr("ranking_goleadores.csv", ["Pos.", "Jugador", "Equipo", "Goles", "De penal"], [[i + 1, p, e, n, rk[1][(p, e)]] for i, ((p, e), n) in enumerate(rr)])
    # control, sanciones, fuentes, errores
    wr("control_fuente.csv", ["Temporada", "Fase", "Equipo", "Posición (fuente)", "Pts (fuente)", "Pts calculados", "PJ calculados", "Diferencia", "Estado", "ID Fuente"],
       [[r["season"], r["fase"], r["team"], r["pos"], r["pub_pts"], r["calc_pts"], r["calc_pj"], (None if r["pub_pts"] is None or r["calc_pts"] is None else round(r["calc_pts"] - r["pub_pts"], 2)),
         "OK" if (r["pub_pts"] is not None and r["calc_pts"] is not None and abs(r["calc_pts"] - r["pub_pts"]) < 0.01) else "Revisar", r["src"]] for r in d["control_rows"]])
    wr("sanciones.csv", ["Temporada", "Equipo", "Puntos descontados", "Motivo", "ID Fuente", "Estado"], [[x["season"], x["team"], x["pts"], x["motivo"], x["src"], "Indicado en la fuente" if x["resuelto"] else "Equipo sin resolver"] for x in d["sanciones"] if not x["red"]])
    wr("correcciones_aplicadas.csv", ["Temporada", "Tipo", "Local", "Visitante", "Marcador en la crónica", "Marcador correcto", "Fuente que lo corrige", "Por qué se aplicó", "URL de la crónica"], d.get("correcciones", []))
    wr("fuentes.csv", ["ID Fuente", "Temporada", "Tipo", "URL", "Autor / sitio", "Cobertura", "Obtenido vía", "Publicado", "Escrito en", "Cambios tras la obtención", "Notas"], d["fuentes"])
    wr("errores_de_lectura.csv", ["Temporada", "Fase", "URL", "Línea de la fuente", "Problema"], d["errores"])
    # temporadas
    byseason = collections.defaultdict(list)
    for m in P:
        byseason[m["season"]].append(m)
    champs = collections.defaultdict(list)
    for c in d.get("campeones", []):
        champs[c["season"]].append(f"{c['team']} ({c['fase']})" if len({x["fase"] for x in d["campeones"] if x["season"] == c["season"]}) > 1 else c["team"])
    for s_ in seasons_order:
        if s_ not in champs:
            single = [r for r in rows_t if r[0] == s_ and r[1] == "Fase regular" and r[2] == 1]
            if single:
                champs[s_].append(single[0][3] + " (1.º de la tabla)")
    srcs = collections.defaultdict(list)
    for f in d["fuentes"]:
        srcs[f[1]].append(f[0])
    wr("temporadas.csv", ["Temporada", "Fases / torneos cargados", "Equipos", "Partidos de fase regular", "Partidos de reducido / promoción / extra", "Campeón (según la crónica o 1.º de la tabla)", "Puntos por victoria", "ID Fuente", "Notas (completar a mano: ascensos, descensos, formato)"],
       [[s_, " | ".join(sorted({m["fase"] for m in ms})), len({m["home"] for m in ms} | {m["away"] for m in ms}), len(ms), sum(1 for r in RED if r["season"] == s_), "; ".join(champs.get(s_, [])), ms[0]["ptsw"], "; ".join(srcs.get(s_, [])), ""] for s_, ms in ((x, byseason[x]) for x in seasons_order)])
    # equipos y estadios
    teams = {}
    for (a, b), v in R.items():
        teams.setdefault(v[0], v)
    first = {}
    for m in P:
        for t in (m["home"], m["away"]):
            first.setdefault(t, m["season"])
    wr("equipos.csv", ["Equipo", "Nombre corto", "Provincia", "Primera temporada en la base", "Temporadas en la base"], [[t, teams.get(t, (t, t, ""))[1], teams.get(t, (t, t, ""))[2], first.get(t, ""), len(tg[t]["temporadas"]) if t in tg else 0] for t in sorted(teams) if t in first])
    st = collections.Counter((m["cancha"], m["origen"]) for m in P + RED)
    wr("estadios.csv", ["Cancha (como figura en Partidos)", "Origen del dato", "Partidos en la base"], [[c, o, n] for (c, o), n in sorted(st.items())])
    return dict(partidos=len(rows_p), goles=len(rows_g), reducidos=len(rows_r), equipos=len(tg), temporadas=len(seasons_order))


def csv_write(path, head, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


if __name__ == "__main__":
    print(main(*sys.argv[1:4]))
