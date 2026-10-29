"""Compara los resultados de las crónicas (bn_build) con una segunda fuente (RSSSF hasta 2007/08, Transfermarkt desde 2008/09).

Uso: python3 -I crosscheck.py <crudo.json> <rsssf_dir> <tm_arg2.json> <salida_dir>
Escribe diferencias_entre_fuentes.csv y resumen_control_cruzado.csv.
"""
import collections, csv, json, os, re, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rs_parse  # noqa: E402
from names_ext import best_among  # noqa: E402

RS_FILE = {"1986/87": "87", "1987/88": "88", "1988/89": "89", "1989/90": "90", "1990/91": "91", "1991/92": "92", "1992/93": "93", "1993/94": "94", "1994/95": "95", "1995/96": "96", "1996/97": "97", "1997/98": "98",
           "1998/99": "99", "1999/00": "00", "2000/01": "01", "2001/02": "02", "2002/03": "03", "2003/04": "04", "2004/05": "05", "2005/06": "06", "2006/07": "07", "2007/08": "08"}
TM_SEASON = {f"{y}/{(y + 1) % 100:02d}": str(y) for y in range(2008, 2026)}


def seq_compare(blog, ext):
    """blog, ext: dict (local, visitante) -> [(hg, ag), ...] en orden cronológico. -> (iguales, solo_blog, solo_ext, distintos)"""
    same = 0
    only_blog, only_ext, diff = [], [], []
    for k in set(blog) | set(ext):
        b, e = blog.get(k, []), ext.get(k, [])
        n = min(len(b), len(e))
        for i in range(n):
            if b[i][:2] == e[i][:2]:
                same += 1
            else:
                diff.append((k, b[i], e[i]))
        only_blog += [(k, x) for x in b[n:]]
        only_ext += [(k, x) for x in e[n:]]
    return same, only_blog, only_ext, diff


def ext_matches(season, rs_dir, tm):
    """Partidos de la segunda fuente para esa temporada -> (lista, nombre_fuente)"""
    if season in RS_FILE:
        path = os.path.join(rs_dir, f"arg2-{RS_FILE[season]}.html")
        if os.path.exists(path):
            return [dict(home=x["home"], away=x["away"], hg=x["hg"], ag=x["ag"], tag=x["round"], date=x["date"]) for x in rs_parse.parse(path)], "RSSSF"
    elif season in TM_SEASON and TM_SEASON[season] in tm:
        return [dict(home=x["home"], away=x["away"], hg=x["hg"], ag=x["ag"], tag=x["round"], date=x["date"]) for x in tm[TM_SEASON[season]]["matches"] if x["hg"] is not None], "Transfermarkt"
    return [], None


def compare(ms, ext, teams):
    """Compara los partidos de la crónica (ms) con los de otra fuente (ext). Cada par (local, visitante) se recorre en orden cronológico.
    -> dict(distintos=[(partido_crónica, (hg, ag) otra fuente)], solo_otra=[(local, visitante, hg, ag)], solo_cronica=[partido], iguales=n, sin_resolver=Counter)"""
    unresolved = collections.Counter()
    extd = collections.defaultdict(list)
    for x in ext:
        h, _ = best_among(x["home"], teams)
        a, _ = best_among(x["away"], teams)
        if not h or not a:
            unresolved[x["home"] if not h else x["away"]] += 1
            continue
        extd[(h, a)].append(x)
    blog = collections.defaultdict(list)
    for m in sorted(ms, key=lambda m: m["date"]):
        blog[(m["home"], m["away"])].append(m)
    res = dict(distintos=[], solo_otra=[], solo_cronica=[], iguales=0, sin_resolver=unresolved)
    for k in set(blog) | set(extd):
        b, e = blog.get(k, []), extd.get(k, [])
        # alineación: primero los que coinciden exactamente, después el resto por orden
        e_left = e[:]
        b_left = []
        for m in b:
            hit = next((x for x in e_left if (x["hg"], x["ag"]) == (m["hg"], m["ag"])), None)
            if hit:
                e_left.remove(hit)
                res["iguales"] += 1
            else:
                b_left.append(m)
        n = min(len(b_left), len(e_left))
        for i in range(n):
            res["distintos"].append((b_left[i], (e_left[i]["hg"], e_left[i]["ag"]), e_left[i]))
        res["solo_cronica"] += b_left[n:]
        res["solo_otra"] += [(k[0], k[1], x["hg"], x["ag"], x) for x in e_left[n:]]
    return res


def sa_by_season(sa_rows, ms):
    """Partidos de Solo Ascenso dentro de las fechas de la temporada (con 15 días de margen)."""
    ds = sorted(m["date"] for m in ms if m.get("date"))
    if not ds or ds[0] < "2014-01-01":
        return []
    import datetime
    n = len(ds)  # percentiles 3 y 97: unas pocas fechas mal tipeadas en la crónica no deben ensanchar la ventana
    lo = (datetime.date.fromisoformat(ds[int(0.03 * n)]) - datetime.timedelta(days=7)).isoformat()
    hi = (datetime.date.fromisoformat(ds[min(n - 1, int(0.97 * n))]) + datetime.timedelta(days=7)).isoformat()
    return [dict(home=r["local"], away=r["visitante"], hg=int(r["gl"]), ag=int(r["gv"]), tag=r.get("ronda")) for r in sa_rows if lo <= r["fecha"] <= hi]


def main(crudo, rs_dir, tm_json, out, sa_norm=None):
    os.makedirs(out, exist_ok=True)
    d = json.load(open(crudo, encoding="utf-8"))
    tm = json.load(open(tm_json, encoding="utf-8")) if os.path.exists(tm_json) else {}
    bys = collections.defaultdict(list)
    for m in d["partidos"] + d["reducidos"]:
        bys[m["season"]].append(m)
    rows, summary, unresolved = [], [], collections.Counter()
    sa_rows = []
    if sa_norm and os.path.exists(sa_norm):
        import gzip
        for ln in gzip.open(sa_norm, "rt", encoding="utf-8"):
            r = json.loads(ln)
            if r.get("cat") == "Primera Nacional" and not r.get("sin_resultado") and (any(e["xi"] for e in r["eq"]) or r["gl"] != "0" or r["gv"] != "0"):
                sa_rows.append(r)
    for season, ms in sorted(bys.items()):
        teams = sorted({m["home"] for m in ms} | {m["away"] for m in ms})
        ext, src = [], None
        if season in RS_FILE:
            path = os.path.join(rs_dir, f"arg2-{RS_FILE[season]}.html")
            if os.path.exists(path):
                ext = [dict(home=x["home"], away=x["away"], hg=x["hg"], ag=x["ag"], tag=x["round"]) for x in rs_parse.parse(path)]
                src = "RSSSF"
        elif season in TM_SEASON and TM_SEASON[season] in tm:
            ext = [dict(home=x["home"], away=x["away"], hg=x["hg"], ag=x["ag"], tag=x["round"]) for x in tm[TM_SEASON[season]]["matches"] if x["hg"] is not None]
            src = "Transfermarkt"
        srcs = [(ext, src)] if ext else []
        # Solo Ascenso como segunda fuente para las temporadas de la crónica que cubre (desde 2014)
        sa = sa_by_season(sa_rows, ms) if sa_rows and src != "SA" and not any(m["src"].endswith(("-SA", "-TM")) for m in ms) else []
        if sa:
            srcs.append((sa, "Solo Ascenso"))
        for ext, src in srcs:
            mapped = []
            for x in ext:
                h, hs = best_among(x["home"], teams)
                a, as_ = best_among(x["away"], teams)
                if not h or not a:
                    unresolved[(season, x["home"] if not h else x["away"])] += 1
                    continue
                mapped.append((h, a, x["hg"], x["ag"]))
            blog = collections.defaultdict(list)
            for m in sorted(ms, key=lambda m: m["date"]):
                blog[(m["home"], m["away"])].append((m["hg"], m["ag"], m["date"], m["post"]))
            extd = collections.defaultdict(list)
            for h, a, hg, ag in mapped:
                extd[(h, a)].append((hg, ag))
            same, ob, oe, df = seq_compare(blog, extd)
            summary.append([season, src, len(ms), len(mapped), same, len(df), len(ob), len(oe)])
            for k, b, e in df:
                rows.append([season, src, "Marcador distinto", k[0], k[1], f"{b[0]}-{b[1]}", f"{e[0]}-{e[1]}", b[2], b[3]])
            for k, b in ob:
                rows.append([season, src, "Solo en la crónica", k[0], k[1], f"{b[0]}-{b[1]}", "", b[2], b[3]])
            for k, e in oe:
                rows.append([season, src, "Solo en la otra fuente", k[0], k[1], "", f"{e[0]}-{e[1]}", "", ""])
    with open(os.path.join(out, "diferencias_entre_fuentes.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Temporada", "Otra fuente", "Tipo", "Local", "Visitante", "Marcador en la crónica", "Marcador en la otra fuente", "Fecha (crónica)", "URL de la crónica"])
        w.writerows(rows)
    with open(os.path.join(out, "resumen_control_cruzado.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["Temporada", "Otra fuente", "Partidos en la crónica", "Partidos leídos de la otra fuente", "Coinciden", "Marcador distinto", "Solo en la crónica", "Solo en la otra fuente"])
        w.writerows(summary)
    print(len(rows), "diferencias;", sum(1 for _ in unresolved), "nombres sin resolver")
    for (s, n), c in unresolved.most_common(25):
        print("  sin resolver", s, n, c)
    return summary


if __name__ == "__main__":
    main(*sys.argv[1:6])
