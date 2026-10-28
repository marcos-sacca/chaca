"""Arma la base histórica de la Primera B Nacional a partir de las crónicas de «Historia y Fútbol» (josecarluccio.blogspot.com).

Uso: python3 -I bn_build.py <cache_blog> <catalogo.json> <salida_dir>
Lee cada entrada de la B Nacional (1986/87 a 2018/19), la interpreta con jc_parse y escribe CSV con las mismas columnas
que la planilla «B Nacional histórica» (partidos, goleadores, reducidos, temporadas, equipos, estadios, control fuente, fuentes).
"""
import csv, collections, datetime, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from jc_parse import parse_matches, parse_tables, parse_sanciones, unwrap  # noqa: E402
import jc_fetch  # noqa: E402
from clubes import REG, R, nkk  # noqa: E402

PLAYOFF = re.compile(r"Reducido|Octogonal|Dodecagonal|Reválida|Reclasificatorio|Promoción|Triangular|Cuadrangular|Final por|Ronda Final|Desempate|Torneo por la Promoción|Torneo por el 2do|Torneo por la", re.I)
MESES = ["", "ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"]


def lev(a, b):
    if abs(len(a) - len(b)) > 3:
        return 9
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        p = d[:]
        d[0] = i
        for j, cb in enumerate(b, 1):
            d[j] = min(p[j] + 1, d[j - 1] + 1, p[j - 1] + (ca != cb))
    return d[-1]


def classify(title):
    """-> (season, fase, es_reducido, orden_del_torneo)"""
    t = title.replace("Argentina:", "").strip()
    m = re.search(r"(\d{4})/(\d{2,4})", t)
    ap = re.search(r"Apertura\s+(\d{4})", t)
    cl = re.search(r"Clausura\s+(\d{4})", t)
    tr = re.search(r"Transici[oó]n\s+(\d{4})", t)
    if m:
        season = f"{m.group(1)}/{m.group(2)[-2:]}"
    elif ap:
        y = int(ap.group(1))
        season = f"{y}/{(y + 1) % 100:02d}"
    elif cl:
        y = int(cl.group(1))
        season = f"{y - 1}/{y % 100:02d}"
    elif tr:
        season = f"Transición {tr.group(1)}"
    else:
        y = re.search(r"\b(20\d\d)\b", t)
        season = y.group(1) if y else "?"
    fase = re.sub(r".*?(\d{4}/\d{2,4}|\b20\d\d\b)\s*", "", t, count=1).strip(" -–")
    fase = re.sub(r"^(AFA|Torneo)\s*[-–]?\s*", "", fase).strip(" -–")
    if ap:
        fase = "Torneo Apertura" + (f" - {fase}" if fase and "Apertura" not in fase else "")
    if cl and "Clausura" not in fase:
        fase = "Torneo Clausura"
    if not fase or fase in ("AFA",):
        fase = "Fase regular"
    fase = re.sub(r"^Torneo (Apertura|Clausura) \d{4}\s*-?\s*", r"Torneo \1 ", fase).strip()
    return season, fase, bool(PLAYOFF.search(t)), t


def season_code(season):
    if season.startswith("Transición"):
        return "T" + season.split()[-1]
    a = season[:4]
    return a + season[5:7] if "/" in season else a


def parse_participants(text):
    t = unwrap(text)
    m = re.search(r"Participantes(.*?)(?:Posiciones|El Torneo|Nota:|\d+(?:ra|da|er|ta)\.? Fecha|\d{2}/\d{2}/\d{4} en)", t)
    if not m:
        return []
    return [(a.strip(), b.strip(), c.strip()) for a, b, c in re.findall(r"([^()]+?)\s*\(([^()–-]+?)\s*[–-]\s*([^()]+?)\)", m.group(1))]


ALIAS = {
    "estacion quequen de necochea": "Estación Quequén",
    "atletico concepcion de la banda del rio sali": "Atlético Concepción de Tucumán",
    "colon de santa": "Colón",
    "guarani antonio franco de misiones": "Guaraní Antonio Franco de Posadas",
    "quilmes ac": "Quilmes",
    "godoy cruz de mendoza": "Godoy Cruz Antonio Tomba",
    "godoy antonio tomba de mendoza": "Godoy Cruz Antonio Tomba",
    "olimpo de bahia": "Olimpo de Bahía Blanca",
    "arsenal": "Arsenal FC",
    "brown de arrecifes": "Almirante Brown de Arrecifes",
    "estudiantes de san luis": "Sportivo Estudiantes de San Luis",
    "juventud unida de san luis": "Juventud Unida Universitario de San Luis",
    "guillermo madryn de puerto madryn": "Guillermo Brown de Puerto Madryn",
    "tristan suarez": "Tristán Suárez",
    "san martin de san juan san martin de san juan": "San Martín de San Juan",
    "talleres de remedios de escalada": "Talleres de Remedios de Escalada",
}


class Resolver:
    """Convierte el nombre con que aparece un equipo en una línea de partido en un club canónico, usando la lista de participantes."""

    def __init__(self, participants, fallback):
        self.var = collections.defaultdict(set)
        for n, c, _ in participants:
            key = (nkk(n), nkk(c))
            club = REG.get(key)
            if not club:
                continue
            prov = re.sub(r"^Provincia de ", "", dict(zip([(a, b) for a, b, _ in participants], [z for _, _, z in participants]))[(n, c)])
            for v in {n, f"{n} de {c}", f"{n} de {prov}", f"{n} {c}", re.sub(r"\s+AC$", "", n), re.sub(r"\bAC\b", "", n).strip(), f"{n} de {c}".replace("Atlético de", "Atlético"), club[0]}:
                self.var[nkk(v)].add(club[0])
        self.fallback = fallback

    def __call__(self, name):
        k = nkk(re.sub(r"[.:)]+$", "", name))
        s = self.var.get(k)
        if s and len(s) == 1:
            return next(iter(s)), "ok"
        if s:
            return sorted(s)[0], "ambiguo"
        best = min(((lev(k, v), v) for v in self.var), default=(9, None))
        if best[0] <= 2 and best[1]:
            c = self.var[best[1]]
            if len(c) == 1:
                return next(iter(c)), "typo"
        if k in self.fallback:
            return self.fallback[k], "global"
        if k in ALIAS:
            return ALIAS[k], "alias"
        cand = [(lev(k, v), v) for v in self.fallback if len(v) > 5]
        cand.sort()
        if cand and cand[0][0] <= 2:
            return self.fallback[cand[0][1]], "typo_global"
        cand = [v for v in self.fallback if len(k) > 8 and (v.startswith(k) or k.startswith(v)) and abs(len(v) - len(k)) < 12]
        if len(cand) == 1:
            return self.fallback[cand[0]], "prefijo"
        return None, "desconocido"


def fix_year(season, iso):
    """Corrige años mal tipeados en la fuente (p. ej. 1966 por 1996): elige el año de la temporada con menos dígitos distintos."""
    mm = re.match(r"(?:Transición )?(\d{4})", season)
    y0 = int(mm.group(1))
    window = [y0, y0 + 1] if ("/" in season or season.startswith("Trans")) else [y0]
    y = int(iso[:4])
    if y in window:
        return iso
    best = min(window, key=lambda w: (sum(a != b for a, b in zip(str(w), str(y))), abs(w - y)))
    return f"{best:04d}{iso[4:]}"


def ymd(s):
    d, m, y = s.split("/")
    return f"{int(y):04d}-{int(m):02d}-{int(d):02d}"


def estado_y_cancha(m, home):
    notas = " ".join(m.get("notes", []))
    estado = "Jugado"
    if re.search(r"suspendid", notas, re.I):
        estado = "Suspendido (ver observaciones)"
    if re.search(r"dio por ganado|ganó por puntos|perdi[óo] los puntos|por reglamento|desde el escritorio", notas, re.I):
        estado = "Resuelto en el escritorio (ver observaciones)"
    cancha, origen = f"Cancha de {home}", "Asumida: cancha del local"
    mm = re.search(r"cancha de ([^.]+)", notas)
    if mm:
        cancha, origen = f"Cancha de {mm.group(1).strip()}", "Indicada en la fuente"
    else:
        mm = re.search(r"estadio\s+[“\"]?([^”\".]+)[”\"]?(?: de ([^.]+))?", notas, re.I)
        if mm:
            cancha = f"Estadio {mm.group(1).strip()}" + (f" ({mm.group(2).strip()})" if mm.group(2) else "")
            origen = "Indicada en la fuente"
    return estado, cancha, origen, notas


def main(cache, catalog, out, rs_dir=None, tm_json=None):
    os.makedirs(out, exist_ok=True)
    posts = json.load(open(catalog, encoding="utf-8"))
    posts = [p for p in posts if re.search(r'Nacional "B"|"B" Nacional|Nacional B', p["t"]) and "División AFA" not in p["t"]]
    posts.sort(key=lambda p: p["p"])
    # primera pasada: participantes por temporada
    byseason = collections.defaultdict(list)
    data = []
    for p in posts:
        f = os.path.join(cache, jc_fetch.key(p["u"]) + ".txt")
        if not os.path.exists(f):
            continue
        text = open(f, encoding="utf-8").read()
        season, fase, red, t = classify(p["t"])
        part = parse_participants(text)
        ms, loose = parse_matches(text)
        tabs = parse_tables(text)
        data.append(dict(sanc=parse_sanciones(text), p=p, season=season, fase=fase, red=red, title=t, part=part, ms=ms, tabs=tabs, loose=loose))
        byseason[season].extend(part)
    fallback = {}
    for (a, b), v in REG.items():
        fallback.setdefault(a, v[0])
        fallback.setdefault(nkk(v[0]), v[0])
    for k, v in list(fallback.items()):
        fallback[k] = v
    res = {s: Resolver(parts, fallback) for s, parts in byseason.items()}

    partidos, reducidos, control, fuentes, errores, sanciones, campeones = [], [], [], [], [], [], []
    seasons = collections.OrderedDict()
    counters = collections.Counter()
    for d in data:
        s, fase, red = d["season"], d["fase"], d["red"]
        code = season_code(s)
        sid = f"SRC-{code}-{len([f for f in fuentes if f[0].startswith('SRC-' + code)]) + 1:02d}"
        fuentes.append([sid, s, d["title"], d["p"]["u"], "José Carluccio — Historia y Fútbol", f"{len(d['ms'])} partidos leídos", "Bajado y leído por script (bn_build.py)", d["p"]["p"], "", "", ""])
        resolve_season = res[s]
        post_res = Resolver(d["part"], fallback) if d["part"] else None

        def resolve(name, _p=post_res, _s=resolve_season):
            if _p:
                n, st = _p(name)
                if n and st in ("ok", "typo", "alias", "global", "prefijo", "typo_global"):
                    return n, st
            return _s(name)
        part_set = {REG.get((nkk(a), nkk(b)), (None,))[0] for a, b, _ in d["part"]} - {None}
        ptsw = 2 if (s[:4].isdigit() and int(s[:4]) < 1995) else 3
        order = 0
        for m in d["ms"]:
            if "error" in m:
                errores.append([s, fase, d["p"]["u"], m["raw"][:200], m["error"]])
                continue
            h, hs = resolve(m["home"])
            a, as_ = resolve(m["away"])
            if not h or not a:
                errores.append([s, fase, d["p"]["u"], m["raw"][:200], f"equipo desconocido: {m['home'] if not h else m['away']}"])
                continue
            if hs != "ok" or as_ != "ok":
                counters["nombre_corregido_" + (hs if hs != "ok" else as_)] += 1
            try:
                iso = ymd(m["date"])
                datetime.date.fromisoformat(iso)
            except ValueError:
                errores.append([s, fase, d["p"]["u"], m["raw"][:200], "fecha inválida"])
                continue
            iso2 = fix_year(s, iso)
            if iso2 != iso:
                m.setdefault("notes", []).append(f"Fecha corregida: la fuente dice {m['date']}")
                iso = iso2
            estado, cancha, origen, notas = estado_y_cancha(m, R_short(h))
            red_ = red
            row = dict(season=s, code=code, fase=fase, red=red_, stage=m.get("stage"), leg=m.get("leg"), fecha_n=m["fecha_n"], date=iso, city=m["city"], cancha=cancha, origen=origen, home=h, away=a, hg=m["hg"], ag=m["ag"],
                       estado=estado, obs=notas, hsrc=m["home"], asrc=m["away"], src=sid, hs=m["hs"], as_=m["as_"], extra=m.get("extra", ""), ptsw=ptsw, post=d["p"]["u"])
            (reducidos if red_ else partidos).append(row)
        mc = re.search(r"Campe[óo]n:\s*([A-ZÁÉÍÓÚÑ0-9 .\-]{3,60}?)\s*\(", unwrap(open(os.path.join(cache, jc_fetch.key(d["p"]["u"]) + ".txt"), encoding="utf-8").read()))
        if mc:
            cn, _ = resolve(mc.group(1).title().replace(" De ", " de ").replace(" Del ", " del ").replace(" Y ", " y "))
            campeones.append(dict(season=s, fase=fase, team=cn or mc.group(1), src=sid))
        for sc in d["sanc"]:
            tn, st = resolve(sc["team"])
            sanciones.append(dict(season=s, team=tn or sc["team"], pts=sc["pts"], motivo=sc["motivo"], src=sid, post=d["p"]["u"], red=red, resuelto=bool(tn)))
        # partidos sueltos de equipos que casi no juegan en la entrada (cruces o desempates entre zonas): pasan a la lista de partidos extra
        if not red:
            cnt_t = collections.Counter(t for m in partidos if m["post"] == d["p"]["u"] for t in (m["home"], m["away"]))
            if len([t for t, n in cnt_t.items() if n >= 6]) >= 6:
                for m in [m for m in partidos if m["post"] == d["p"]["u"] and (cnt_t[m["home"]] <= 2 or cnt_t[m["away"]] <= 2)]:
                    partidos.remove(m)
                    m["red"] = True
                    m["estado"] = "Partido fuera de la zona (desempate o cruce)"
                    reducidos.append(m)
        if d["tabs"].get("pos"):
            control.append(dict(season=s, fase=fase, post=d["p"]["u"], src=sid, red=red, pos=d["tabs"]["pos"], prom=d["tabs"].get("prom", [])))
    # --- control: tablas calculadas vs. tablas publicadas en la misma crónica
    def table_info(c):
        ms = [m for m in partidos if m["post"] == c["post"]]
        ded = {x["team"]: x["pts"] for x in sanciones if x["post"] == c["post"]}
        resolve = res[c["season"]]
        pub, pos = {}, 1
        for raw, val in c["pos"]:
            ns = names_from(raw, resolve)
            for n in ns:
                pub[n] = (pos, val)
            pos += len(ns)
        tab = standings(ms, ded)
        # en los torneos con Apertura/Clausura (y etapas), la tabla de la segunda parte suele ser la acumulada de la temporada
        prev = [m for m in partidos if m["season"] == c["season"] and m["post"] != c["post"] and m["date"] < (min(x["date"] for x in ms) if ms else "")]
        tab2 = standings(prev + ms, ded) if prev else None

        def score(t):
            return sum(1 for team, (p_, v) in pub.items() if team in t and abs(t[team]["pts"] - v) <= 0.01)
        if tab2 and score(tab2) > score(tab):
            tab = tab2
        return pub, tab, score(tab)

    ctl = [c for c in control if not c["red"]]
    fixes = []
    if rs_dir:
        import crosscheck
        tmj = json.load(open(tm_json, encoding="utf-8")) if tm_json and os.path.exists(tm_json) else {}
        for season in sorted({c["season"] for c in ctl}):
            ext, srcname = crosscheck.ext_matches(season, rs_dir, tmj)
            if not ext:
                continue
            ms = [m for m in partidos if m["season"] == season]
            teams = sorted({m["home"] for m in ms} | {m["away"] for m in ms})
            cmp_ = crosscheck.compare(ms, ext, teams)
            cands = [("score", m, sc, x) for m, sc, x in cmp_["distintos"]] + [("add", None, (hg, ag), (h, a, x)) for h, a, hg, ag, x in cmp_["solo_otra"]]
            for c in [c for c in ctl if c["season"] == season]:
                pub, tab, sc0 = table_info(c)
                if sc0 >= len(pub) and len(pub) > 0 and all(t in pub for t in tab):
                    continue
                teams_c = set(pub) | set(tab)
                for _ in range(6):  # hasta 6 correcciones por tabla
                    best = None
                    for cd in list(cands):
                        kind, m, sc, x = cd
                        if kind == "score":
                            if m["post"] != c["post"]:
                                continue
                            old = (m["hg"], m["ag"])
                            m["hg"], m["ag"] = sc
                            _, _, s1 = table_info(c)
                            m["hg"], m["ag"] = old
                        else:
                            h, a, ext_m = x
                            if h not in teams_c or a not in teams_c:
                                continue
                            newm = dict(season=season, code=season_code(season), fase=c["fase"], red=False, fecha_n=None, date=ext_date(season, ext_m), city="", cancha=f"Cancha de {h}", origen="Asumida: cancha del local", home=h, away=a, hg=sc[0], ag=sc[1],
                                        estado="Jugado", obs=f"Partido agregado desde {srcname} (faltaba o estaba roto en la crónica)", hsrc=h, asrc=a, src=c["src"], hs=[], as_=[], extra="", ptsw=2 if int(season[:4]) < 1995 else 3, post=c["post"])
                            partidos.append(newm)
                            _, _, s1 = table_info(c)
                            partidos.pop()
                        if best is None or s1 > best[0]:
                            best = (s1, cd)
                    _, _, cur = table_info(c)
                    if not best or best[0] <= cur:
                        break
                    kind, m, sc, x = best[1]
                    if kind == "score":
                        fixes.append([season, "Marcador corregido", m["home"], m["away"], f"{m['hg']}-{m['ag']}", f"{sc[0]}-{sc[1]}", srcname, "La corrección hace coincidir los puntos con la tabla publicada", m["post"]])
                        m["hg"], m["ag"] = sc
                        m["obs"] = (m["obs"] + " " if m["obs"] else "") + f"Marcador corregido con {srcname}: la crónica decía {fixes[-1][4]}."
                    else:
                        h, a, ext_m = x
                        newm = dict(season=season, code=season_code(season), fase=c["fase"], red=False, fecha_n=None, date=ext_date(season, ext_m), city="", cancha=f"Cancha de {h}", origen="Asumida: cancha del local", home=h, away=a, hg=sc[0], ag=sc[1],
                                    estado="Jugado", obs=f"Partido agregado desde {srcname} (faltaba o estaba roto en la crónica); sin goleadores", hsrc=h, asrc=a, src=c["src"], hs=[], as_=[], extra="", ptsw=2 if int(season[:4]) < 1995 else 3, post=c["post"])
                        partidos.append(newm)
                        fixes.append([season, "Partido agregado", h, a, "", f"{sc[0]}-{sc[1]}", srcname, "Con el partido, los puntos coinciden con la tabla publicada", c["post"]])
                    cands.remove(best[1])
    # temporadas que la fuente de crónicas no tiene (2017/18 y desde 2019/20): solo resultados, tomados de Transfermarkt
    if tm_json and os.path.exists(tm_json):
        tmj = json.load(open(tm_json, encoding="utf-8"))
        allc = sorted({v[0] for v in R.values()})
        from names_ext import best_among
        for tid, label in TM_ONLY.items():
            if tid not in tmj:
                continue
            code = season_code(label)
            sid = f"SRC-{code}-TM"
            fuentes.append([sid, label, "Resultados (sin goleadores)", f"https://www.transfermarkt.com/primera-nacional/gesamtspielplan/wettbewerb/ARG2/saison_id/{tid}", "Transfermarkt", f"{len(tmj[tid]['matches'])} partidos", "Bajado por script (tm_league.py)", "", "", "La fecha local se estimó restando 1 día cuando la hora de Transfermarkt es de madrugada", ""])
            for x in tmj[tid]["matches"]:
                h, _ = best_among(x["home"], allc)
                a, _ = best_among(x["away"], allc)
                if not h or not a:
                    errores.append([label, "Fase regular", sid, f"{x['home']} - {x['away']}", f"equipo sin resolver ({x['home'] if not h else x['away']})"])
                    continue
                if x["hg"] is None:
                    continue
                partidos.append(dict(season=label, code=code, fase="Fase regular", red=False, stage=None, leg=None, fecha_n=int(re.match(r"(\d+)", x["round"]).group(1)) if re.match(r"(\d+)", x["round"]) else None, date=tm_local_date(x), city="", cancha=f"Cancha de {h}",
                                     origen="Asumida: cancha del local", home=h, away=a, hg=x["hg"], ag=x["ag"], estado="Jugado", obs="", hsrc=x["home"], asrc=x["away"], src=sid, hs=[], as_=[], extra="", ptsw=3, post=sid))
    rows_control = []
    for c in ctl:
        pub, tab, _ = table_info(c)
        for team, (pos, val) in pub.items():
            calc = tab.get(team)
            rows_control.append(dict(season=c["season"], fase=c["fase"], team=team, pub_pts=val, pos=pos, calc_pts=calc["pts"] if calc else None, calc_pj=calc["pj"] if calc else None, src=c["src"], post=c["post"]))
        for team in tab:
            if team not in pub:
                rows_control.append(dict(season=c["season"], fase=c["fase"], team=team, pub_pts=None, pos=None, calc_pts=tab[team]["pts"], calc_pj=tab[team]["pj"], src=c["src"], post=c["post"]))
    json.dump(dict(partidos=partidos, reducidos=reducidos, control=control, sanciones=sanciones, control_rows=rows_control, errores=errores, counters=counters, fuentes=fuentes, correcciones=fixes, campeones=campeones), open(os.path.join(out, "_crudo.json"), "w", encoding="utf-8"), ensure_ascii=False, default=list)
    bad = [r for r in rows_control if r["pub_pts"] is None or r["calc_pts"] is None or abs(r["pub_pts"] - r["calc_pts"]) > 0.01]
    print(len(partidos), "partidos de liga;", len(reducidos), "de reducidos/promociones;", len(errores), "líneas con problemas;", len(fixes), "correcciones con segunda fuente;", len(rows_control), "equipos controlados;", len(bad), "con diferencia de puntos")


TM_ONLY = {"2017": "2017/18", "2019": "2019/20", "2020": "2021", "2021": "2022", "2022": "2023", "2023": "2024", "2024": "2025", "2025": "2026"}


def tm_local_date(x):
    """Fecha local (Argentina) de un partido de Transfermarkt: si la hora europea es de madrugada, el partido fue la noche anterior."""
    d = x["date"]
    iso = f"20{d[6:8]}-{d[3:5]}-{d[0:2]}"
    t = x.get("time") or ""
    m = re.match(r"(\d{1,2}):(\d{2})\s*(AM|PM)", t)
    if m and m.group(3) == "AM" and int(m.group(1)) % 12 < 6:
        return (datetime.date.fromisoformat(iso) - datetime.timedelta(days=1)).isoformat()
    return iso


def ext_date(season, x):
    """Fecha ISO aproximada de un partido de otra fuente (TM: dd/mm/yy; RSSSF: 'Aug 9')."""
    d = x.get("date") or ""
    m = re.match(r"(\d{2})/(\d{2})/(\d{2})$", d)
    if m:
        return f"20{m.group(3)}-{m.group(2)}-{m.group(1)}"
    mm = re.match(r"([A-Z][a-z]{2}) (\d{1,2})(?: (\d{4}))?", d)
    if mm:
        mon = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"].index(mm.group(1)) + 1
        y0 = int(season[:4])
        y = int(mm.group(3)) if mm.group(3) else (y0 if (mon >= 7 or "/" not in season) else y0 + 1)
        return f"{y:04d}-{mon:02d}-{int(mm.group(2)):02d}"
    return f"{season[:4]}-07-01"


def names_from(raw, resolve):
    """Separa 'A, B y C' en equipos usando el resolvedor (hay equipos con ' y ' en el nombre, como Defensa y Justicia)."""
    out = []
    for part in [x.strip() for x in raw.split(",") if x.strip()]:
        n, st = resolve(part)
        if n:
            out.append(n)
            continue
        done = False
        for mm in re.finditer(r"\s+(?:y|e)\s+", part):
            l, r = part[: mm.start()], part[mm.end():]
            nl, _ = resolve(l)
            nr, _ = resolve(r)
            if nl and nr:
                out += [nl, nr]
                done = True
                break
        if not done:
            out.append(part)
    return out


def standings(ms, ded=None):
    t = collections.defaultdict(lambda: dict(pj=0, pg=0, pe=0, pp=0, gf=0, gc=0, pts=0))
    for m in ms:
        for team, gf, gc in ((m["home"], m["hg"], m["ag"]), (m["away"], m["ag"], m["hg"])):
            r = t[team]
            r["pj"] += 1
            r["gf"] += gf
            r["gc"] += gc
            if gf > gc:
                r["pg"] += 1
                r["pts"] += m["ptsw"]
            elif gf == gc:
                r["pe"] += 1
                r["pts"] += 1
            else:
                r["pp"] += 1
    for team, d in (ded or {}).items():
        if team in t:
            t[team]["pts"] -= d
    return t


def R_short(canon):
    for v in R.values():
        if v[0] == canon:
            return canon
    return canon


if __name__ == "__main__":
    main(*sys.argv[1:6])
