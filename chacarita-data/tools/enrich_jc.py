"""Completa goleadores de Chacarita con las crónicas de «Historia y Fútbol» (josecarluccio.blogspot.com).

Uso: python3 -I tools/enrich_jc.py <cache_dir_blog> <catalogo_seleccionado.json> <salida.json>
Solo propone datos para partidos donde la planilla no tiene goleadores (o tiene menos de los que marca el resultado).
Cruce: fecha (±3 días) + marcador + lado de Chacarita; si hay más de un candidato, gana la fecha exacta.
"""
import collections, datetime, json, os, re, sys, unicodedata
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "bnacional", "tools"))
from jc_parse import parse_matches  # noqa: E402
import jc_fetch  # noqa: E402

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def norm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9 ]", " ", s).split()


def norm_s(name):
    t = [x for x in norm(name) if len(x) > 1]
    return t[-1] if t else ""


def lev(a, b):
    if abs(len(a) - len(b)) > 2:
        return 9
    d = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        p = d[:]
        d[0] = i
        for j, cb in enumerate(b, 1):
            d[j] = min(p[j] + 1, d[j - 1] + 1, p[j - 1] + (ca != cb))
    return d[-1]


def near_same(a, b):
    xa, xb = sorted(a.elements()), sorted(b.elements())
    if len(xa) != len(xb):
        return False
    rest = xb[:]
    for x in xa:
        for y in rest:
            if lev(x, y) <= 1:
                rest.remove(y)
                break
        else:
            return False
    return True


def dt(s):
    return datetime.datetime.strptime(s, "%d/%m/%Y").date()


def main(cache, selected, out):
    M = json.load(open(os.path.join(ROOT, "data/matches.json"), encoding="utf-8"))
    players = json.load(open(os.path.join(ROOT, "data/players.json"), encoding="utf-8"))
    byday = collections.defaultdict(list)
    for m in M:
        byday[m["d"]].append(m)
    # nombres conocidos por temporada (goles y formaciones) para resolver apellidos sueltos
    known = collections.defaultdict(set)
    for m in M:
        for g in m.get("g", []) or []:
            if g.get("p"):
                known[int(m["d"][:4])].add(g["p"])
    for mid, arr in json.load(open(os.path.join(ROOT, "data/lineups.json"), encoding="utf-8")).items():
        y = None
    allnames = set(players)
    for y in list(known):
        pass
    sel = json.load(open(selected, encoding="utf-8"))
    found, stats = [], collections.Counter()
    for p in sel:
        f = os.path.join(cache, jc_fetch.key(p["u"]) + ".txt")
        if not os.path.exists(f):
            continue
        text = open(f, encoding="utf-8").read()
        ms, _ = parse_matches(text)
        for x in ms:
            if "error" in x or "Chacarita" not in (x["home"] + x["away"]):
                continue
            home = x["home"].startswith("Chacarita")
            gf, gc = (x["hg"], x["ag"]) if home else (x["ag"], x["hg"])
            try:
                d0 = dt(x["date"])
            except ValueError:
                stats["fecha_invalida"] += 1
                continue
            cands = []
            for k in range(-3, 4):
                for m in byday.get((d0 + datetime.timedelta(days=k)).isoformat(), []):
                    if m["gf"] == gf and m["gc"] == gc and (m["c"] == "L") == home and m["c"] != "N":
                        cands.append((abs(k), m))
            if not cands:
                stats["sin_cruce"] += 1
                continue
            cands.sort(key=lambda z: z[0])
            if len(cands) > 1 and cands[0][0] == cands[1][0]:
                stats["ambiguo"] += 1
                continue
            m = cands[0][1]
            mine = x["hs"] if home else x["as_"]
            rival = x["as_"] if home else x["hs"]
            goals = []
            # en la fuente, «e/c» marca un gol en contra: el jugador es del equipo contrario al que suma el gol
            for s in mine:
                for i in range(s["k"]):
                    goals.append({"n": s["n"], "pen": 1 if (i < s["pen"] and not s["ec"]) else 0, "ec": 1 if s["ec"] else 0})
            found.append({"id": m["id"], "d": m["d"], "partido": f"{m['l']} {m['gl']}-{m['gv']} {m['v']}", "fuente": p["u"], "fuente_titulo": p["t"].replace("Argentina: ", ""),
                          "ciudad": x["city"], "notas": x.get("notes", []), "goles": goals, "gf": gf, "ya_tiene": len(m.get("g") or []), "dias": cands[0][0]})
            stats["cruzados"] += 1
    ec_patch, hallazgos = [], []
    Mi = {m["id"]: m for m in M}
    for it in found:
        m = Mi[it["id"]]
        have = m.get("g") or []
        # 1) nombres de goles en contra: la planilla dice «Gol en contra (rival)» y la crónica nombra al jugador rival
        gen = [g for g in have if g.get("ec")]
        names = [g["n"] for g in it["goles"] if g["ec"]]
        if gen and names and len(gen) == len(names) and all(re.search(r"gol en contra", g.get("p") or "", re.I) for g in gen):
            ec_patch.append({"id": it["id"], "fecha": it["d"], "partido": it["partido"], "nombres": names, "fuente": it["fuente"]})
        # 2) diferencias de goleadores entre la planilla y la crónica (para revisar a mano)
        a = collections.Counter(norm_s(g["p"]) for g in have if not g.get("ec") and g.get("p"))
        b = collections.Counter(norm_s(g["n"]) for g in it["goles"] if not g["ec"])
        if m["gf"] and have and not near_same(a, b):
            hallazgos.append({"id": it["id"], "fecha": it["d"], "partido": it["partido"], "planilla": "; ".join(g["p"] for g in have if g.get("p")), "cronica": "; ".join(g["n"] + (" (e/c)" if g["ec"] else "") for g in it["goles"]), "fuente": it["fuente"]})
    json.dump({"stats": stats, "items": found, "goles_en_contra": ec_patch, "hallazgos": hallazgos}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(stats, "nombres de goles en contra:", len(ec_patch), "· diferencias para revisar:", len(hallazgos))


if __name__ == "__main__":
    main(*sys.argv[1:4])
