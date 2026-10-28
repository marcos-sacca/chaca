"""
Cruza las fichas de sitios de historia de clubes rivales con la planilla y propone árbitro, DT y formaciones para celdas vacías.

  python3 -I tools/enrich_rivals.py <museogranate.json> <lahistoriariver.json> <almagro.json> <salida.json>

Fuentes (todas con robots.txt permisivo):
  - Museo Granate (Lanús): árbitro, DT y XI de Chacarita con nombre completo.
  - La Historia River: árbitro, DT y XI de Chacarita (apellidos; se resuelven contra los jugadores de esa época).
  - El Sitio de Almagro: árbitro.
Solo propone cuando la celda de la planilla está vacía; cuando ya hay dato, mide si coincide.
"""
import collections
import datetime
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
MES = {m: i + 1 for i, m in enumerate("enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre diciembre".split())}


def nk(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z ]", " ", s).split()


def same_name(a, b):
    import difflib
    ta, tb = nk(a), nk(b)
    if not ta or not tb:
        return False
    sim = lambda x, y: x == y or difflib.SequenceMatcher(None, x, y).ratio() >= 0.8
    # mismo apellido (con tolerancia de tipeo), en cualquier posición del otro nombre
    return sim(ta[-1], tb[-1]) or any(sim(ta[-1], t) for t in tb) or any(sim(tb[-1], t) for t in ta)



def ref_fix(r):
    """'OLIVETO Luis' -> 'Luis Oliveto'"""
    toks = r.replace(",", " ").split()
    up = [t for t in toks if t.isupper() and len(t) > 1]
    if up and len(up) < len(toks):
        given = [t for t in toks if t not in up]
        return " ".join(given + [u.title() for u in up])
    return r.strip()


def main(mg_p, rv_p, al_p, out):
    M = json.load(open(os.path.join(ROOT, "data/matches.json"), encoding="utf-8"))
    players = json.load(open(os.path.join(ROOT, "data/players.json"), encoding="utf-8"))
    lineups = json.load(open(os.path.join(ROOT, "data/lineups.json"), encoding="utf-8"))
    byid = {m["id"]: m for m in M}
    byday = collections.defaultdict(list)
    for m in M:
        byday[m["d"]].append(m)
    # jugadores por año: apariciones en formaciones + goleadores
    pyear = collections.defaultdict(collections.Counter)
    for mid, rows in lineups.items():
        m = byid.get(int(mid))
        if m:
            for pid, _ in rows:
                pyear[int(m["d"][:4])][players[pid]] += 1
    for m in M:
        for g in m.get("g", []):
            if g["p"] and not g["ec"]:
                pyear[int(m["d"][:4])][g["p"]] += 1
    dts = collections.Counter(m["dt"] for m in M if m.get("dt"))

    def resolve_surname(txt, year):
        toks = nk(txt)
        if not toks:
            return None
        ini = toks[0][0] if len(toks) > 1 and len(toks[0]) == 1 else None
        sur = [t for t in toks if len(t) > 1]
        c = collections.Counter()
        for y in range(year - 2, year + 3):
            for p, n in pyear[y].items():
                pt = nk(p)
                if not pt:
                    continue
                if pt[-1] in sur or (len(sur) > 1 and " ".join(sur) in " ".join(pt)):
                    if ini and pt[0][0] != ini:
                        continue
                    c[p] += n
        if not c:
            return None
        best = c.most_common(2)
        if len(best) == 1 or best[0][1] >= 2 * best[1][1]:
            return best[0][0]
        return None

    def resolve_dt(txt):
        toks = nk(txt)
        if not toks:
            return None
        cand = [d for d in dts if nk(d) and nk(d)[-1] == toks[-1] and (len(toks) == 1 or nk(d)[0][0] == toks[0][0])]
        return cand[0] if len(cand) == 1 else None

    stats = collections.Counter()
    patch, lu, dif = [], [], []

    def put(m, campo, val, src):
        key = {"Árbitro": "arb", "DT": "dt", "Espectadores": "esp"}[campo]
        if val in (None, ""):
            return
        if m.get(key) in (None, ""):
            patch.append(dict(id=m["id"], fecha=m["d"], partido=f"{m['l']} {m['gl']}-{m['gv']} {m['v']}", campo=campo, valor=val, fuente=src))
            stats[f"{campo}_nuevo"] += 1
        else:
            stats[f"{campo}_ya_estaba"] += 1
            if key == "arb" or key == "dt":
                ok = same_name(str(m[key]), str(val))
                stats[f"{campo}_coincide" if ok else f"{campo}_difiere"] += 1
                if not ok:
                    dif.append(dict(id=m["id"], fecha=m["d"], campo=campo, planilla=m[key], fuente=val, sitio=src))

    def add_lineup(m, names, src, how):
        if str(m["id"]) in lineups or len(names) != 11:
            stats["formacion_omitida"] += 1
            return
        rows = []
        for n_ in names:
            full = n_ if how == "full" else resolve_surname(n_, int(m["d"][:4]))
            if full:
                rows.append({"n": full, "rol": 0})
        if len({r["n"] for r in rows}) >= 10:
            lu.append(dict(id=m["id"], fecha=m["d"], partido=f"{m['l']} {m['gl']}-{m['gv']} {m['v']}", jugadores=rows, fuente=src))
            stats["formaciones"] += 1
        else:
            stats["formacion_no_resuelta"] += 1

    # --- Museo Granate
    if os.path.exists(mg_p):
        for mid, d in json.load(open(mg_p, encoding="utf-8")).items():
            m = byid.get(int(mid))
            if not m:
                continue
            src = f"Museo Granate (Lanús) {d['url'].rsplit('/', 1)[-1]}"
            stats["museo_fichas"] += 1
            put(m, "Árbitro", d.get("arbitro"), src)
            ch = next((t for t in d.get("equipos", []) if "chacarita" in t["nombre"].lower()), None)
            if ch:
                dt = ch.get("dt")
                if dt and not re.match(r"^[A-Z]\.[a-z]", dt) and len(dt) > 5:
                    put(m, "DT", dt, src)
                add_lineup(m, ch["titulares"], src, "full")
    # --- La Historia River
    if os.path.exists(rv_p):
        for url, d in json.load(open(rv_p, encoding="utf-8")).items():
            mm = re.search(r"(\d+) de (\w+) de (\d{4})", d.get("fecha_txt", ""))
            if not mm:
                continue
            day = datetime.date(int(mm.group(3)), MES[mm.group(2)], int(mm.group(1))).isoformat()
            cands = [m for m in byday.get(day, []) if "River" in (m["r"] or "")]
            if len(cands) != 1:
                stats["river_sin_cruce"] += 1
                continue
            m = cands[0]
            src = f"La Historia River ({url.rsplit('/', 1)[-1]})"
            stats["river_fichas"] += 1
            put(m, "Árbitro", d.get("arbitro"), src)
            ch = next((t for k, t in d.get("equipos", {}).items() if "chacarita" in k.lower()), None)
            if ch:
                if ch.get("dt"):
                    dtn = resolve_dt(ch["dt"]) or (ch["dt"] if len(nk(ch["dt"])[0]) > 1 else None)
                    put(m, "DT", dtn, src)
                add_lineup(m, ch["xi"], src, "sur")
    # --- Almagro
    if os.path.exists(al_p):
        for mid, d in json.load(open(al_p, encoding="utf-8")).items():
            m = byid.get(int(mid))
            L = d["L"]
            if not m or int(m["d"][:4]) >= 2010:  # las fichas modernas de Almagro tienen otro formato
                continue
            ref = None
            for i, l in enumerate(L):
                if l == "Árbitros" or l.startswith("Árbitro"):
                    nxt = L[i + 1] if i + 1 < len(L) else ""
                    ref = nxt if nxt and not nxt.startswith("Árbitro") else (L[i + 2] if i + 2 < len(L) else None)
                    break
            if not ref:
                # el nombre aparece antes de "Alineación inicial"
                k = L.index("Alineación inicial") if "Alineación inicial" in L else None
                ref = L[k - 1] if k else None
            stats["almagro_fichas"] += 1
            if ref and not re.search(r"\d", ref):
                put(m, "Árbitro", ref_fix(ref), f"El Sitio de Almagro ({d['url'].split('/partido/')[1].strip('/')})")
    json.dump({"stats": stats, "patch": patch, "formaciones": lu, "diferencias": dif}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(dict(stats))
    for x in dif[:25]:
        print(x)


if __name__ == "__main__":
    main(*sys.argv[1:5])
