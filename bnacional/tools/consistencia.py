"""Control de consistencia sobre los CSV ya armados: corrige lo que se puede corregir con una fuente y recalcula las tablas.

Uso: python3 -I consistencia.py <data_dir> [tm_primera_nacional.json] [sintesis_solo_ascenso.jsonl.gz]
Corre después de bn_export.py y crosscheck.py (run.py ya lo llama). Se puede correr más de una vez: lo ya corregido no se vuelve a tocar.

Reglas
  1. Nombres por temporada: un nombre de la fuente que en cierta temporada es otro club (RENOMBRES).
  2. Partidos repetidos o faltantes en la crónica (temporadas con segunda fuente): dentro de una fase, si un cruce
     aparece más veces de lo que corresponde y la segunda fuente no lo tiene («Solo en la crónica»), se saca; si un
     cruce aparece menos y la segunda fuente sí lo tiene («Solo en la otra fuente»), se agrega con el marcador y la
     fecha de esa fuente. Solo se aplica si después de corregir todos los cruces de la fase quedan parejos.
  3. Desde 2017/18 (Solo Ascenso numera todo como «Fecha N»): los partidos posteriores a la última fecha de la fase
     regular pasan a reducidos.csv (reducido y finales) o se descartan si un equipo no jugaba la categoría.
Salidas: reescribe partidos, goleadores, reducidos, tabla_temporada, tabla_general, control_fuente (columnas
calculadas), temporadas, equipos y ranking_goleadores; escribe correcciones_consistencia.csv (cada cambio) y
pendientes_consistencia.csv (lo que sigue desparejo, con explicación si es del formato del torneo).
"""
import collections, csv, gzip, json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from names_ext import best_among  # noqa: E402

# 1. (temporada, nombre en la fuente) -> club correcto
RENOMBRES = {
    ("1993/94", "Talleres"): "Talleres de Remedios de Escalada",  # la crónica distingue «Talleres» y «Talleres de Córdoba»; jugaron los dos
}
# nombres de la fuente que siempre son otro club (sin importar la temporada)
RENOMBRES_SIEMPRE = {
    "Talleres (R.E)": "Talleres de Remedios de Escalada",  # Solo Ascenso 2024 y 2025; se asignaba a Talleres de Córdoba
}
# partidos que faltan en la crónica, verificados a mano contra otra fuente (se agregan si no están)
AGREGAR = [
    dict(Temporada="2002/03", Fase="Torneo Clausura", Local="Instituto de Córdoba", Visitante="Belgrano de Córdoba", gl=0, gv=0, fecha="2003-03-09", fecha_torneo="6",
         fuente="RSSSF (rsssf.org/tablesa/arg2-03.html), fecha 6 del Clausura; con este partido Instituto suma 60 como en la tabla publicada. Fecha calendario aproximada"),
]
# diferencias con la tabla publicada ya revisadas a mano (quedan explicadas en pendientes)
NOTAS = {
    ("1998/99", "Instituto de Córdoba"): "La crónica y RSSSF tienen los mismos 30 resultados (16-7-7, 55 pts, 57-31), pero la tabla publicada dice 17-6-7, 57 pts, 57-30: un empate se le habrá dado ganado 1-0 en escritorio. Sin saber cuál, no se cambia.",
}
# 3. última fecha de la fase regular (Solo Ascenso sigue la numeración en el reducido y las finales)
ULTIMA_FECHA = {"2017/18": 25, "2019/20": 21, "Transición 2020": 7, "2021": 34, "2022": 37, "2023": 38, "2024": 38, "2025": 34}
TORNEO_EXTRA = {"Transición 2020": "Fase final (Transición 2020)"}  # no es un reducido: segunda fase por zonas
# formatos con zonas de distinto tamaño o partidos que nunca se jugaron (para explicar lo que queda desparejo)
FORMATO = {
    "2019/20": "Torneo suspendido por la pandemia: algunos partidos no se jugaron.",
    "2021": "Dos zonas de 18 y 17 equipos: 34 y 32 partidos.",
    "2023": "Dos zonas de 19 y 18 equipos: 36 y 34 partidos.",
    "Transición 2014": "Dos zonas de 11 equipos más una fecha interzonal y desempates.",
}
TM_SEASON = {f"{y}/{(y + 1) % 100:02d}": str(y) for y in range(2008, 2026)}
TM_SEASON.update({"Transición 2014": "2014", "2015": "2015", "Transición 2016": "2016"})


def rd(path):
    with open(path, encoding="utf-8-sig") as f:
        r = csv.DictReader(f)
        return r.fieldnames, list(r)


def wr(path, head, rows):
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(head)
        w.writerows(rows)


def num(x, d=0):
    try:
        return int(float(x))
    except (TypeError, ValueError):
        return d


def season_key(seasons_first):
    return lambda s: seasons_first.get(s, "9999")


def ext_index(season, teams, tm, sa):
    """Partidos de las otras fuentes para la temporada: (local, visitante, gl, gv) -> [fechas ISO]"""
    out = collections.defaultdict(list)
    if tm and season in TM_SEASON and TM_SEASON[season] in tm:
        for x in tm[TM_SEASON[season]]["matches"]:
            if x.get("hg") is None or not x.get("date") or x["date"].count("/") != 2:
                continue
            h, _ = best_among(x["home"], teams)
            a, _ = best_among(x["away"], teams)
            if h and a:
                dd, mm, yy = x["date"].split("/")
                out[(h, a, x["hg"], x["ag"])].append(f"20{yy}-{mm}-{dd}")
    for r in sa.get(season, []):
        h, _ = best_among(r["local"], teams)
        a, _ = best_among(r["visitante"], teams)
        if h and a:
            out[(h, a, num(r["gl"]), num(r["gv"]))].append(r["fecha"])
    return out


MAX_CARRERA = 14  # años entre el primer y el último gol para aceptar que dos variantes son la misma persona
NO_UNIFICAR = set()  # pares (variante, destino) que se revisaron y son personas distintas
# apellidos muy comunes: con o sin inicial puede ser otra persona -> no se unifican solos, quedan en pendientes
COMUNES = set("""gomez gonzalez rodriguez lopez fernandez martinez diaz perez sanchez garcia romero sosa benitez torres ruiz ramirez
flores acosta medina herrera suarez aguirre gimenez jimenez alvarez molina castro ortiz silva nunez luna juarez cabrera rios morales godoy
ferreyra vera ledesma peralta rojas gutierrez blanco ramos vazquez villalba ojeda campos paz caceres ibanez figueroa correa maldonado leiva
coronel ponce dominguez navarro quiroga barrios carrizo arias moreno alonso cardozo cabral sotelo franco miranda vargas mendez rivero
aguero bustos ayala galvan escobar arce islas""".split())


def unify_players(G, first):
    """-> [(variante, nombre elegido, motivo)]. Reglas:
    a) iguales salvo tildes y mayúsculas;
    b) mismas palabras completas y las iniciales de una son el comienzo de las de la otra («Silvio Carrario» y
       «Silvio R. Carrario»), si hay una sola variante compatible más completa y toda la carrera entra en MAX_CARRERA años.
    Iniciales distintas («Luis E. Sosa» y «Luis N. Sosa») son personas distintas y no se tocan."""
    import unicodedata
    strip = lambda x: "".join(c for c in unicodedata.normalize("NFD", x) if unicodedata.category(c) != "Mn").lower()
    toks = lambda x: re.sub(r"[^a-z ]", " ", strip(x)).split()
    year = lambda s: int(re.search(r"\d{4}", s).group())
    info = collections.defaultdict(lambda: dict(g=0, y=set()))
    for g in G:
        info[g["Jugador"]]["g"] += 1
        info[g["Jugador"]]["y"].add(year(g["Temporada"]))
    out, alias, dudas = [], {}, []
    # a) tildes
    by = collections.defaultdict(list)
    for nm in info:
        by[" ".join(toks(nm))].append(nm)
    for v in by.values():
        if len(v) > 1:
            tgt = max(v, key=lambda x: (info[x]["g"], x))
            for x in v:
                if x != tgt and (x, tgt) not in NO_UNIFICAR:
                    alias[x] = tgt
                    out.append((x, tgt, "Mismo nombre con otra tilde o mayúscula"))
    names = [x for x in info if x not in alias]
    # b) iniciales del medio
    key = lambda x: tuple(t for t in toks(x) if len(t) > 1)
    ini = lambda x: [t for t in toks(x) if len(t) == 1]
    grp = collections.defaultdict(list)
    for nm in names:
        if len(key(nm)) >= 2:
            grp[key(nm)].append(nm)
    for k, v in grp.items():
        if len(v) < 2:
            continue
        for x in sorted(v, key=lambda x: len(ini(x))):
            comp = [y for y in v if y != x and len(ini(y)) > len(ini(x)) and ini(y)[:len(ini(x))] == ini(x)]
            maxi = [y for y in comp if not any(z != y and len(ini(z)) > len(ini(y)) and ini(z)[:len(ini(y))] == ini(y) for z in comp)]
            if len(maxi) != 1:
                continue  # ninguna o varias variantes posibles: no se puede decidir
            tgt = maxi[0]
            ys = info[x]["y"] | info[tgt]["y"]
            if max(ys) - min(ys) > MAX_CARRERA or (x, tgt) in NO_UNIFICAR:
                continue
            if k[-1] in COMUNES:
                dudas.append((x, tgt, f"Posible duplicado (apellido común, {min(ys)}-{max(ys)}): revisar a mano y, si es la misma persona, sacar el apellido de COMUNES o agregar el par"))
                continue
            out.append((x, tgt, f"Misma persona con y sin inicial del medio ({min(ys)}-{max(ys)})"))
    return out, dudas


def main(data, tm_json=None, sa_path=None):
    J = lambda n: os.path.join(data, n)
    HP, P = rd(J("partidos.csv"))
    HG, G = rd(J("goleadores.csv"))
    HR, R = rd(J("reducidos.csv"))
    _, TEMP = rd(J("temporadas.csv"))
    _, SAN = rd(J("sanciones.csv"))
    _, DIF = rd(J("diferencias_entre_fuentes.csv")) if os.path.exists(J("diferencias_entre_fuentes.csv")) else ([], [])
    tm = json.load(open(tm_json, encoding="utf-8")) if tm_json and os.path.exists(tm_json) else {}
    ptsw = {t["Temporada"]: num(t["Puntos por victoria"], 3) for t in TEMP}
    log, pend = [], []
    gol_by = collections.defaultdict(list)
    for g in G:
        gol_by[g["ID Partido"]].append(g)

    def zone_of(rows):
        """(temporada, etapa, club) -> fase de la zona donde jugó la mayoría de sus partidos de esa etapa"""
        c = collections.defaultdict(collections.Counter)
        for p in rows:
            if " - Zona" in p["Fase"]:
                base = p["Fase"].split(" - Zona")[0]
                for t in (p["Local"], p["Visitante"]):
                    c[(p["Temporada"], base, t)][p["Fase"]] += 1
        return {k: v.most_common(1)[0][0] for k, v in c.items()}

    def fase_for(p, team, zones):
        if p["Fase"].endswith(" - Interzonal"):
            return zones.get((p["Temporada"], p["Fase"][: -len(" - Interzonal")], team), p["Fase"])
        return p["Fase"]

    def phase_tab(rows):
        t = collections.defaultdict(lambda: [0, 0])  # (temporada, fase, equipo) -> [pts, pj]
        zones = zone_of(rows)
        for p in rows:
            w = ptsw.get(p["Temporada"], 3)
            hg, ag = num(p["Goles local"]), num(p["Goles visitante"])
            for team, gf, gc in ((p["Local"], hg, ag), (p["Visitante"], ag, hg)):
                k = (p["Temporada"], fase_for(p, team, zones), team)
                t[k][1] += 1
                t[k][0] += w if gf > gc else 1 if gf == gc else 0
        return t
    before = phase_tab(P)
    # equipos cuya tabla publicada ya coincide con los partidos cargados: ningún cambio puede moverles los puntos
    _, C0 = rd(J("control_fuente.csv"))
    ctrl_ok = {(c["Temporada"], c["Fase"], c["Equipo"]) for c in C0 if c["Estado"] == "OK"}
    mpts = lambda m, team: (lambda hg, ag, w: (w if hg > ag else 1 if hg == ag else 0) if team == m["Local"] else (w if ag > hg else 1 if hg == ag else 0))(num(m["Goles local"] if "Goles local" in m else m["gl"]), num(m["Goles visitante"] if "Goles visitante" in m else m["gv"]), ptsw.get(m.get("Temporada", ""), 3))
    renamed = collections.defaultdict(set)  # (temporada, club nuevo) -> club viejo
    renamed_siempre = collections.defaultdict(set)  # idem, solo los de RENOMBRES_SIEMPRE (valen para toda la temporada)

    # --- 1. renombres por temporada
    for p in P:
        for side, src in (("Local", "Local (nombre en fuente)"), ("Visitante", "Visitante (nombre en fuente)")):
            new = RENOMBRES.get((p["Temporada"], p[src])) or RENOMBRES_SIEMPRE.get(p[src])
            if new and p[side] != new:
                old = p[side]
                p[side] = new
                renamed[(p["Temporada"], new)].add(old)
                if p[src] in RENOMBRES_SIEMPRE:
                    renamed_siempre[(p["Temporada"], new)].add(old)
                for g in gol_by[p["ID Partido"]]:
                    for k in ("Equipo que suma el gol", "Equipo del jugador"):
                        if g[k] == old:
                            g[k] = new
                log.append([p["Temporada"], "Club mal asignado", p["ID Partido"], p["Local"], p["Visitante"], f"{p['Goles local']}-{p['Goles visitante']}", p["Fecha calendario"], f"«{p[src]}» es {new}, no {old}", "Crónica (nombre en la fuente)"])

    for r in R:  # reducidos con nombre de la fuente mal asignado (si ya se habían pasado antes del renombre)
        for side in ("Local", "Visitante"):
            for (s_, n_), olds in list(renamed_siempre.items()):
                if r["Temporada"] == s_ and r[side] in olds:
                    r[side] = n_

    # Solo Ascenso por temporada (para fechas de partidos que faltan)
    sa = collections.defaultdict(list)
    first = {}
    for p in P:
        if p["Fecha calendario"] and (p["Temporada"] not in first or p["Fecha calendario"] < first[p["Temporada"]]):
            first[p["Temporada"]] = p["Fecha calendario"]
    if sa_path and os.path.exists(sa_path):
        win = {}
        for s in first:
            ds = sorted(p["Fecha calendario"] for p in P if p["Temporada"] == s and p["Fecha calendario"])
            if ds and ds[0] >= "2014-01-01":
                win[s] = (ds[int(.03 * len(ds))], ds[min(len(ds) - 1, int(.97 * len(ds)))])
        with gzip.open(sa_path, "rt", encoding="utf-8") as f:
            for line in f:
                r = json.loads(line)
                if r.get("cat") != "Primera Nacional" or not r.get("fecha"):
                    continue
                for s, (lo, hi) in win.items():
                    if lo <= r["fecha"] <= hi:
                        sa[s].append(r)

    # --- 2a. desempates cargados como fase regular: partidos entre equipos con partidos de más, posteriores
    #         al último partido de todos los demás equipos de la fase -> reducidos.csv
    gol_by = collections.defaultdict(list)
    for g in G:
        gol_by[g["ID Partido"]].append(g)
    rcount = collections.Counter(r["ID Partido"].rsplit("-", 1)[0] for r in R)

    def to_red(p, torneo, instancia):
        def scorers(team):
            c = collections.Counter()
            for g in gol_by[p["ID Partido"]]:
                if g["Equipo que suma el gol"] == team:
                    c[(g["Jugador"], g["Tipo"])] += 1
            return "; ".join(j + (f" {k}" if k > 1 else "") + (" (p)" if t == "Gol de penal" else " (e/c)" if t == "Gol en contra" else "") for (j, t), k in c.items())
        code = "RED-" + p["ID Partido"].rsplit("-", 1)[0]
        rcount[code] += 1
        R.append({"ID Partido": f"{code}-{rcount[code]:02d}", "Temporada": p["Temporada"], "Torneo": torneo, "Instancia": instancia, "Partido (ida/vuelta)": "",
                  "Fecha calendario": p["Fecha calendario"], "Ciudad": p["Ciudad"], "Cancha": p["Cancha"], "Origen dato cancha": p["Origen dato cancha"], "Local": p["Local"], "Visitante": p["Visitante"], "GL": p["Goles local"], "GV": p["Goles visitante"],
                  "Goleadores local": scorers(p["Local"]), "Goleadores visitante": scorers(p["Visitante"]), "Estado": p["Estado"], "Observaciones": (p["Observaciones"] + " " if p["Observaciones"] else "") + f"Pasado desde partidos.csv ({p['ID Partido']}) por control de consistencia.", "ID Fuente": p["ID Fuente"], "Texto extra de la fuente": ""})

    moved = set()
    fases = collections.defaultdict(list)
    for p in P:
        fases[(p["Temporada"], p["Fase"])].append(p)
    for (s, fase), ms in fases.items():
        if s in ULTIMA_FECHA:
            continue
        c = collections.Counter()
        for m in ms:
            c[m["Local"]] += 1; c[m["Visitante"]] += 1
        mode = collections.Counter(c.values()).most_common(1)[0][0]
        over = {t for t, v in c.items() if v > mode}
        if not over:
            continue
        last = max((m["Fecha calendario"] for m in ms if m["Local"] not in over and m["Visitante"] not in over and m["Fecha calendario"]), default="")
        late = [m for m in ms if m["Local"] in over and m["Visitante"] in over and m["Fecha calendario"] > last]
        need = collections.Counter({t: c[t] - mode for t in over})
        for m in sorted(late, key=lambda m: m["Fecha calendario"], reverse=True):
            if any((s, fase, t) in ctrl_ok and mpts(m, t) for t in (m["Local"], m["Visitante"])):
                continue  # la tabla publicada cuenta este partido
            if need[m["Local"]] > 0 and need[m["Visitante"]] > 0:
                need[m["Local"]] -= 1; need[m["Visitante"]] -= 1
                moved.add(m["ID Partido"])
                to_red(m, "Desempate", "Desempate (fuera de la fase regular)")
                log.append([s, "Desempate cargado como fase regular (pasa a reducidos)", m["ID Partido"], m["Local"], m["Visitante"], f"{m['Goles local']}-{m['Goles visitante']}", m["Fecha calendario"], f"Los dos tenían partidos de más en {fase} y se jugó después del último partido del resto", m["ID Fuente"]])
    P = [p for p in P if p["ID Partido"] not in moved]
    G = [g for g in G if g["ID Partido"] not in moved]

    # --- 2. cruces repetidos o faltantes, con segunda fuente
    dif = collections.defaultdict(list)
    for d in DIF:
        dif[(d["Temporada"], d["Tipo"])].append(d)
    nid = collections.Counter()
    fases = collections.defaultdict(list)
    for p in P:
        fases[(p["Temporada"], p["Fase"])].append(p)
    drop = set()
    add = []
    for (s, fase), ms in fases.items():
        if s in ULTIMA_FECHA or int(re.search(r"\d{4}", s).group()) >= 2019:  # sin segunda fuente
            continue
        teams = sorted({m["Local"] for m in ms} | {m["Visitante"] for m in ms})
        pair = collections.Counter(frozenset((m["Local"], m["Visitante"])) for m in ms)
        exp = collections.Counter(pair.values()).most_common(1)[0][0]
        over = {k for k, v in pair.items() if v > exp}
        under = {frozenset((a, b)) for i, a in enumerate(teams) for b in teams[i + 1:] if pair.get(frozenset((a, b)), 0) < exp}
        if not over and not under:
            continue
        rm, ad = [], []
        for d in dif[(s, "Solo en la crónica")]:
            k = frozenset((d["Local"], d["Visitante"]))
            if k in over:
                cand = [m for m in ms if m["Local"] == d["Local"] and m["Visitante"] == d["Visitante"] and f"{m['Goles local']}-{m['Goles visitante']}" == d["Marcador en la crónica"] and m["Fecha calendario"] == d["Fecha (crónica)"] and m["ID Partido"] not in drop and m not in rm]
                if cand:
                    rm.append(cand[0])
        for d in dif[(s, "Solo en la otra fuente")]:
            k = frozenset((d["Local"], d["Visitante"]))
            if k in under:
                gl, gv = (num(x) for x in d["Marcador en la otra fuente"].split("-"))
                ad.append(dict(Local=d["Local"], Visitante=d["Visitante"], gl=gl, gv=gv, src=d["Otra fuente"]))
        # simulación: ¿queda pareja la fase?
        sim = pair.copy()
        for m in rm:
            sim[frozenset((m["Local"], m["Visitante"]))] -= 1
        for a in ad:
            sim[frozenset((a["Local"], a["Visitante"]))] += 1
        ok_pairs = all(sim.get(frozenset((a, b)), 0) == exp for i, a in enumerate(teams) for b in teams[i + 1:])
        if not (rm or ad):
            continue
        dpts = collections.Counter()
        for m in rm:
            for t in (m["Local"], m["Visitante"]):
                dpts[t] -= mpts(m, t)
        for a in ad:
            for t in (a["Local"], a["Visitante"]):
                dpts[t] += mpts(dict(a, Temporada=s), t)
        if any(v and (s, fase, t) in ctrl_ok for t, v in dpts.items()):
            pend.append([s, fase, "", "", "La segunda fuente propone cambios, pero la tabla publicada coincide con la crónica: " + ", ".join(f"{m['Local']} {m['Goles local']}-{m['Goles visitante']} {m['Visitante']}" for m in rm), ""])
            continue
        if not ok_pairs:
            pend.append([s, fase, "", "", "La segunda fuente no alcanza para emparejar los cruces: " + ", ".join(f"{' vs '.join(sorted(k))} ({pair.get(k, 0)})" for k in sorted(over | under, key=sorted)), ""])
            continue
        ext = ext_index(s, teams, tm, sa)
        for m in rm:
            if not any({m["Local"], m["Visitante"]} & {a["Local"], a["Visitante"]} for a in ad):
                # sin un faltante relacionado: es un partido extra real (desempate), no un error de carga
                to_red(m, "Desempate", "Desempate (fuera de la fase regular)")
                drop.add(m["ID Partido"])
                log.append([s, "Desempate cargado como fase regular (pasa a reducidos)", m["ID Partido"], m["Local"], m["Visitante"], f"{m['Goles local']}-{m['Goles visitante']}", m["Fecha calendario"], f"Tercer cruce en {fase}, sin partido faltante relacionado y sin figurar en la tabla de la segunda fuente", m["ID Fuente"]])
                continue
            drop.add(m["ID Partido"])
            log.append([s, "Partido repetido o mal asignado (se saca)", m["ID Partido"], m["Local"], m["Visitante"], f"{m['Goles local']}-{m['Goles visitante']}", m["Fecha calendario"], f"El cruce figuraba {pair[frozenset((m['Local'], m['Visitante']))]} veces en {fase}; la segunda fuente no tiene este partido", m["ID Fuente"]])
        for a in ad:
            dates = ext.get((a["Local"], a["Visitante"], a["gl"], a["gv"]), [])
            sib = [m for m in rm if a["Local"] in (m["Local"], m["Visitante"]) or a["Visitante"] in (m["Local"], m["Visitante"])]
            date = dates[0] if dates else (sib[0]["Fecha calendario"] if sib else max(m["Fecha calendario"] for m in ms))
            code = s.replace("/", "").replace("Transición ", "T")
            nid[code] += 1
            mid = f"{code}-X{nid[code]:02d}"
            w = ptsw.get(s, 3)
            res = "L" if a["gl"] > a["gv"] else "V" if a["gv"] > a["gl"] else "E"
            pl_, pv_ = (w, 0) if res == "L" else (0, w) if res == "V" else (1, 1)
            note = f"Agregado por control de consistencia: faltaba en la crónica; marcador de {a['src']}" + ("" if dates else "; fecha aproximada")
            fuente_id = next((m["ID Fuente"] for m in ms), "")
            add.append({"ID Partido": mid, "Temporada": s, "Fase": fase, "Fecha torneo": "", "Fecha calendario": date, "Ciudad": "", "Cancha": "", "Origen dato cancha": "Sin dato", "Local": a["Local"], "Visitante": a["Visitante"],
                        "Goles local": a["gl"], "Goles visitante": a["gv"], "Resultado (L/E/V)": res, "Pts local": pl_, "Pts visitante": pv_, "Estado": "Jugado", "Control goles": "Sin goleadores" if a["gl"] + a["gv"] else "OK",
                        "Observaciones": note, "Local (nombre en fuente)": a["Local"], "Visitante (nombre en fuente)": a["Visitante"], "ID Fuente": fuente_id})
            log.append([s, "Partido faltante (se agrega)", mid, a["Local"], a["Visitante"], f"{a['gl']}-{a['gv']}", date, note, a["src"]])
    P = [p for p in P if p["ID Partido"] not in drop] + add
    G = [g for g in G if g["ID Partido"] not in drop]

    # --- 2b. partidos faltantes verificados a mano
    for a in AGREGAR:
        if any(p["Temporada"] == a["Temporada"] and p["Fase"] == a["Fase"] and p["Local"] == a["Local"] and p["Visitante"] == a["Visitante"] for p in P):
            continue
        code = a["Temporada"].replace("/", "").replace("Transición ", "T")
        nid[code] += 1
        mid = f"{code}-M{nid[code]:02d}"
        w = ptsw.get(a["Temporada"], 3)
        res = "L" if a["gl"] > a["gv"] else "V" if a["gv"] > a["gl"] else "E"
        pl_, pv_ = (w, 0) if res == "L" else (0, w) if res == "V" else (1, 1)
        P.append({"ID Partido": mid, "Temporada": a["Temporada"], "Fase": a["Fase"], "Fecha torneo": a["fecha_torneo"], "Fecha calendario": a["fecha"], "Ciudad": "", "Cancha": "", "Origen dato cancha": "Sin dato", "Local": a["Local"], "Visitante": a["Visitante"],
                  "Goles local": a["gl"], "Goles visitante": a["gv"], "Resultado (L/E/V)": res, "Pts local": pl_, "Pts visitante": pv_, "Estado": "Jugado", "Control goles": "OK" if a["gl"] + a["gv"] == 0 else "Sin goleadores",
                  "Observaciones": "Agregado a mano: " + a["fuente"], "Local (nombre en fuente)": a["Local"], "Visitante (nombre en fuente)": a["Visitante"], "ID Fuente": ""})
        log.append([a["Temporada"], "Partido faltante (agregado a mano)", mid, a["Local"], a["Visitante"], f"{a['gl']}-{a['gv']}", a["fecha"], a["fuente"], "Revisión manual"])

    # --- 3. reducido y finales cargados como fase regular (Solo Ascenso)
    regular = collections.defaultdict(set)
    for p in P:
        s = p["Temporada"]
        if s in ULTIMA_FECHA and 0 < num(p["Fecha torneo"]) <= ULTIMA_FECHA[s]:
            regular[s] |= {p["Local"], p["Visitante"]}
    keep = []
    moved = set()
    for p in P:
        s = p["Temporada"]
        if s in ULTIMA_FECHA and num(p["Fecha torneo"]) > ULTIMA_FECHA[s]:
            moved.add(p["ID Partido"])
            if p["Local"] not in regular[s] or p["Visitante"] not in regular[s]:
                log.append([s, "Partido de otra categoría (se descarta)", p["ID Partido"], p["Local"], p["Visitante"], f"{p['Goles local']}-{p['Goles visitante']}", p["Fecha calendario"], "Un equipo no jugó la fase regular de la categoría esa temporada", p["ID Fuente"]])
                continue
            to_red(p, TORNEO_EXTRA.get(s, "Reducido y finales por el ascenso"), f"Fecha {p['Fecha torneo']} (Solo Ascenso)")
            log.append([s, "Reducido o final cargado como fase regular (pasa a reducidos)", p["ID Partido"], p["Local"], p["Visitante"], f"{p['Goles local']}-{p['Goles visitante']}", p["Fecha calendario"], f"Fecha {p['Fecha torneo']}: después de la última fecha de la fase regular ({ULTIMA_FECHA[s]})", p["ID Fuente"]])
            continue
        keep.append(p)
    P = keep
    G = [g for g in G if g["ID Partido"] not in moved]

    # --- 4. jugadores con el mismo nombre escrito distinto en distintos clubes (el armado los unifica solo dentro de cada club)
    merges, dudas = unify_players(G, first)
    for old, new, why in merges:
        for g in G:
            if g["Jugador"] == old:
                g["Jugador"] = new
        log.append(["", "Jugador unificado", "", old, new, "", "", why, "Goleadores"])
    for (s_, t_), nota in NOTAS.items():
        pend.append([s_, "", t_, "", "Diferencia con la tabla publicada (revisada)", nota])
    for old, new, why in dudas:
        pend.append(["", "Jugadores", f"{old} / {new}", "", why, ""])

    # --- 5. reducidos repetidos (mismo partido cargado en dos zonas o torneos) y reducidos que son en realidad un
    #        partido de la fase regular con un club mal asignado (ej.: «Independiente» en 2008/09 era Independiente Rivadavia)
    import datetime as _dt
    inseason = collections.defaultdict(set)
    reg_by = collections.defaultdict(list)
    for p in P:
        inseason[p["Temporada"]] |= {p["Local"], p["Visitante"]}
        if p["Fecha calendario"]:
            reg_by[(p["Temporada"], p["Goles local"], p["Goles visitante"])].append(p)
    def regular_twin(r):
        if not r["Fecha calendario"]:
            return None
        d = _dt.date.fromisoformat(r["Fecha calendario"])
        for p in reg_by[(r["Temporada"], r["GL"], r["GV"])]:
            if abs((_dt.date.fromisoformat(p["Fecha calendario"]) - d).days) > 1:
                continue
            if (r["Local"], r["Visitante"]) == (p["Local"], p["Visitante"]):
                return p  # el mismo partido ya está en la fase regular
            if r["Local"] == p["Local"] and r["Visitante"] not in inseason[r["Temporada"]] or r["Visitante"] == p["Visitante"] and r["Local"] not in inseason[r["Temporada"]]:
                return p
        for q in keepr:  # el mismo partido ya guardado en reducidos con el club bien escrito
            if q["Temporada"] == r["Temporada"] and q["Fecha calendario"] == r["Fecha calendario"] and (q["GL"], q["GV"]) == (r["GL"], r["GV"]):
                if r["Local"] == q["Local"] and r["Visitante"] not in inseason[r["Temporada"]] or r["Visitante"] == q["Visitante"] and r["Local"] not in inseason[r["Temporada"]]:
                    return {"ID Partido": q["ID Partido"], "Local": q["Local"], "Visitante": q["Visitante"], "Goles local": q["GL"], "Goles visitante": q["GV"]}
        return None
    keepr = []
    seenr = {}
    for r in R:
        k = (r["Temporada"], r["Fecha calendario"], r["Local"], r["Visitante"], r["GL"], r["GV"])
        if r["Fecha calendario"] and k in seenr:
            log.append([r["Temporada"], "Reducido repetido (se saca)", r["ID Partido"], r["Local"], r["Visitante"], f"{r['GL']}-{r['GV']}", r["Fecha calendario"], f"Ya figuraba como {seenr[k]['ID Partido']} ({seenr[k]['Torneo']})", r["ID Fuente"]])
            continue
        tw = regular_twin(r)
        if tw:
            log.append([r["Temporada"], "Reducido que era un partido de fase regular con el club mal asignado (se saca)", r["ID Partido"], r["Local"], r["Visitante"], f"{r['GL']}-{r['GV']}", r["Fecha calendario"], f"Es {tw['ID Partido']}: {tw['Local']} {tw['Goles local']}-{tw['Goles visitante']} {tw['Visitante']}", r["ID Fuente"]])
            continue
        seenr[k] = r
        keepr.append(r)
    R = keepr

    # --- 6. interzonales de una etapa por zonas guardados como reducidos (1996/97): son partidos del torneo y
    #        las tablas publicadas los cuentan -> fase «<etapa> - Interzonal», que suma en la zona de cada club
    keepr = []
    for r in R:
        m_ = re.match(r"(Etapa Clasificatoria) - Zona", r["Torneo"])
        zone_ok = lambda t: any(k[0] == r["Temporada"] and k[2] == t and k[1].startswith(m_.group(1)) for k in ctrl_ok) if m_ else False
        gain = lambda t: mpts({"Local": r["Local"], "Visitante": r["Visitante"], "Goles local": r["GL"], "Goles visitante": r["GV"], "Temporada": r["Temporada"]}, t)
        if m_ and any(zone_ok(t) and gain(t) for t in (r["Local"], r["Visitante"])):
            keepr.append(r)  # la tabla publicada de esa zona ya cierra sin este partido
            continue
        if m_ and r["Local"] in inseason[r["Temporada"]] and r["Visitante"] in inseason[r["Temporada"]]:
            code = r["Temporada"].replace("/", "").replace("Transición ", "T")
            nid[code] += 1
            mid = f"{code}-I{nid[code]:02d}"
            gl, gv, w = num(r["GL"]), num(r["GV"]), ptsw.get(r["Temporada"], 3)
            res = "L" if gl > gv else "V" if gv > gl else "E"
            pl_, pv_ = (w, 0) if res == "L" else (0, w) if res == "V" else (1, 1)
            P.append({"ID Partido": mid, "Temporada": r["Temporada"], "Fase": m_.group(1) + " - Interzonal", "Fecha torneo": "", "Fecha calendario": r["Fecha calendario"], "Ciudad": r["Ciudad"], "Cancha": r["Cancha"], "Origen dato cancha": r["Origen dato cancha"],
                      "Local": r["Local"], "Visitante": r["Visitante"], "Goles local": gl, "Goles visitante": gv, "Resultado (L/E/V)": res, "Pts local": pl_, "Pts visitante": pv_, "Estado": r["Estado"], "Control goles": "",
                      "Observaciones": (r["Observaciones"] + " " if r["Observaciones"] else "") + f"Interzonal pasado desde reducidos.csv ({r['ID Partido']}) por control de consistencia.", "Local (nombre en fuente)": r["Local"], "Visitante (nombre en fuente)": r["Visitante"], "ID Fuente": r["ID Fuente"]})
            seq = 0
            for team, rival, txt in ((r["Local"], r["Visitante"], r["Goleadores local"]), (r["Visitante"], r["Local"], r["Goleadores visitante"])):
                for item in [x.strip() for x in (txt or "").split(";") if x.strip()]:
                    mm = re.match(r"(.*?)(?: (\d+))?((?: \((?:p|e/c)\))*)$", item)
                    name, k, flags = mm.group(1), int(mm.group(2) or 1), mm.group(3)
                    for i in range(k):
                        seq += 1
                        ec = "(e/c)" in flags
                        G.append({"ID Gol": f"G-{mid}-{seq:02d}", "ID Partido": mid, "Temporada": r["Temporada"], "Fecha torneo": "", "Fecha calendario": r["Fecha calendario"], "Equipo que suma el gol": team, "Jugador": name,
                                  "Equipo del jugador": rival if ec else team, "Tipo": "Gol en contra" if ec else "Gol de penal" if "(p)" in flags else "Gol", "Nombre en fuente": name, "Detalle": "", "ID Fuente": r["ID Fuente"]})
            log.append([r["Temporada"], "Interzonal guardado como reducido (pasa a la fase regular)", mid, r["Local"], r["Visitante"], f"{r['GL']}-{r['GV']}", r["Fecha calendario"], f"Era {r['ID Partido']} ({r['Torneo']}); las tablas publicadas de cada zona lo cuentan", r["ID Fuente"]])
            continue
        keepr.append(r)
    R = keepr

    # --- recalcular tablas
    first = {}
    for p in P:
        if p["Fecha calendario"] and (p["Temporada"] not in first or p["Fecha calendario"] < first[p["Temporada"]]):
            first[p["Temporada"]] = p["Fecha calendario"]
    P.sort(key=lambda p: (first.get(p["Temporada"], "9999"), p["Fecha calendario"] or "9999", p["ID Partido"]))
    order = sorted(first, key=season_key(first))
    ded = collections.defaultdict(int)
    for x in SAN:
        ded[(x["Temporada"], x["Equipo"])] += num(x["Puntos descontados"])
    blank = lambda: dict(pj=0, pg=0, pe=0, pp=0, gf=0, gc=0, pts=0, pts3=0)
    tg = collections.defaultdict(lambda: dict(blank(), temporadas=set()))
    ts = collections.defaultdict(lambda: collections.defaultdict(blank))
    zones = zone_of(P)
    for p in P:
        w = ptsw.get(p["Temporada"], 3)
        hg, ag = num(p["Goles local"]), num(p["Goles visitante"])
        for team, gf, gc in ((p["Local"], hg, ag), (p["Visitante"], ag, hg)):
            for t in (tg[team], ts[(p["Temporada"], fase_for(p, team, zones))][team]):
                t["pj"] += 1; t["gf"] += gf; t["gc"] += gc
                if gf > gc:
                    t["pg"] += 1; t["pts"] += w; t["pts3"] += 3
                elif gf == gc:
                    t["pe"] += 1; t["pts"] += 1; t["pts3"] += 1
                else:
                    t["pp"] += 1
            tg[team]["temporadas"].add(p["Temporada"])
    for (s, team), v in ded.items():
        if team in tg:
            tg[team]["pts"] -= v; tg[team]["pts3"] -= v
    rows = sorted(tg.items(), key=lambda kv: (-kv[1]["pts3"], -(kv[1]["gf"] - kv[1]["gc"]), -kv[1]["gf"], kv[0]))
    wr(J("tabla_general.csv"), ["Pos.", "Equipo", "Temporadas", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "Descuento", "Pts", "Pts (3 x victoria)"],
       [[i + 1, t, len(v["temporadas"]), v["pj"], v["pg"], v["pe"], v["pp"], v["gf"], v["gc"], v["gf"] - v["gc"], sum(x for (s, tm_), x in ded.items() if tm_ == t), v["pts"], v["pts3"]] for i, (t, v) in enumerate(rows)])
    rows_t = []
    for (s, fase), tab in sorted(ts.items(), key=lambda kv: (order.index(kv[0][0]), kv[0][1])):
        lst = sorted(tab.items(), key=lambda kv: (-(kv[1]["pts"] - ded.get((s, kv[0]), 0)), -(kv[1]["gf"] - kv[1]["gc"]), -kv[1]["gf"], kv[0]))
        for i, (t, v) in enumerate(lst):
            dd = ded.get((s, t), 0)
            rows_t.append([s, fase, i + 1, t, v["pj"], v["pg"], v["pe"], v["pp"], v["gf"], v["gc"], v["gf"] - v["gc"], dd, v["pts"] - dd])
    wr(J("tabla_temporada.csv"), ["Temporada", "Fase", "Pos.", "Equipo", "PJ", "PG", "PE", "PP", "GF", "GC", "DG", "Descuento", "Pts"], rows_t)
    # control contra la tabla publicada: al valor calculado original se le suma solo lo que cambió por estas
    # correcciones (así se respetan sanciones y tablas acumuladas entre torneos, como el Clausura 1996)
    HC, C = rd(J("control_fuente.csv"))
    after = phase_tab(P)
    dkeys = {k for k in set(before) | set(after) if before.get(k, [0, 0]) != after.get(k, [0, 0])}
    dseason = collections.defaultdict(lambda: [0, 0])
    for k in dkeys:
        b_, a_ = before.get(k, [0, 0]), after.get(k, [0, 0])
        dseason[(k[0], k[2])][0] += a_[0] - b_[0]
        dseason[(k[0], k[2])][1] += a_[1] - b_[1]
    for c in C:
        s_, f_, t_ = c["Temporada"], c["Fase"], c["Equipo"]
        if (s_, t_) in {(s2, o) for (s2, n2), olds in renamed.items() for o in olds}:
            continue  # club renombrado en esa temporada: la tabla de la fuente no se puede asignar sola
        if c["Pts calculados"] in ("", None):
            continue
        k = (s_, f_, t_)
        cum = num(c["PJ calculados"]) != before.get(k, [0, 0])[1]
        dp, dj = dseason[(s_, t_)] if cum else [after.get(k, [0, 0])[0] - before.get(k, [0, 0])[0], after.get(k, [0, 0])[1] - before.get(k, [0, 0])[1]]
        if not dp and not dj:
            continue
        c["Pts calculados"] = num(c["Pts calculados"]) + dp
        c["PJ calculados"] = num(c["PJ calculados"]) + dj
        if c["Pts (fuente)"] not in ("", None):
            diff = round(float(c["Pts calculados"]) - float(c["Pts (fuente)"]), 2)
            c["Diferencia"], c["Estado"] = diff, "OK" if abs(diff) < .01 else "Revisar"
    wr(J("control_fuente.csv"), HC, [[c[h] for h in HC] for c in C])
    # temporadas
    _, TEMP = rd(J("temporadas.csv"))
    HT = list(TEMP[0].keys())
    for t in TEMP:
        ms = [p for p in P if p["Temporada"] == t["Temporada"]]
        t["Equipos"] = len({p["Local"] for p in ms} | {p["Visitante"] for p in ms})
        t["Partidos de fase regular"] = len(ms)
        t["Partidos de reducido / promoción / extra"] = sum(1 for r in R if r["Temporada"] == t["Temporada"])
    wr(J("temporadas.csv"), HT, [[t[h] for h in HT] for t in TEMP])
    # equipos
    HE, E = rd(J("equipos.csv"))
    fs = {}
    for p in P:
        for t in (p["Local"], p["Visitante"]):
            fs.setdefault(t, p["Temporada"])
    for e in E:
        e["Primera temporada en la base"] = fs.get(e["Equipo"], e["Primera temporada en la base"])
        e["Temporadas en la base"] = len(tg[e["Equipo"]]["temporadas"]) if e["Equipo"] in tg else 0
    wr(J("equipos.csv"), HE, [[e[h] for h in HE] for e in E])
    # goleadores
    rk, pen = collections.Counter(), collections.Counter()
    for g in G:
        if g["Tipo"] != "Gol en contra":
            rk[(g["Jugador"], g["Equipo del jugador"])] += 1
            if g["Tipo"] == "Gol de penal":
                pen[(g["Jugador"], g["Equipo del jugador"])] += 1
    wr(J("ranking_goleadores.csv"), ["Pos.", "Jugador", "Equipo", "Goles", "De penal"], [[i + 1, p, e, k, pen[(p, e)]] for i, ((p, e), k) in enumerate(sorted(rk.items(), key=lambda kv: (-kv[1], kv[0])))])
    wr(J("partidos.csv"), HP, [[p[h] for h in HP] for p in P])
    wr(J("goleadores.csv"), HG, [[g[h] for h in HG] for g in G])
    wr(J("reducidos.csv"), HR, [[r[h] for h in HR] for r in R])

    # --- pendientes: lo que sigue desparejo
    pj = collections.defaultdict(collections.Counter)
    for p in P:
        pj[(p["Temporada"], p["Fase"])][p["Local"]] += 1
        pj[(p["Temporada"], p["Fase"])][p["Visitante"]] += 1
    for (s, fase), c in sorted(pj.items(), key=lambda kv: (order.index(kv[0][0]), kv[0][1])):
        mode = collections.Counter(c.values()).most_common(1)[0][0]
        for t, v in sorted(c.items()):
            if v != mode:
                pend.append([s, fase, t, v, f"La mayoría jugó {mode}", FORMATO.get(s, "")])
    # el log se acumula entre corridas (lo ya aplicado no se repite)
    old = rd(J("correcciones_consistencia.csv"))[1] if os.path.exists(J("correcciones_consistencia.csv")) else []
    HL = ["Temporada", "Tipo", "ID Partido", "Local", "Visitante", "Marcador", "Fecha", "Motivo", "Fuente"]
    prev = [[o[h] for h in HL] for o in old]
    seen = {tuple(map(str, r)) for r in prev}
    wr(J("correcciones_consistencia.csv"), HL, prev + [r for r in log if tuple(map(str, r)) not in seen])
    wr(J("pendientes_consistencia.csv"), ["Temporada", "Fase", "Equipo", "PJ", "Problema", "Explicación (si es del formato)"], pend)
    print(f"consistencia: {len(log)} cambios nuevos, {len(pend)} pendientes")
    return len(log)


if __name__ == "__main__":
    for _ in range(4):  # algunas correcciones habilitan otras (ej.: un interzonal recuperado deja ver su duplicado)
        if not main(*sys.argv[1:4]):
            break
