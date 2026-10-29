"""
Cruza las crónicas de Infobae (scrape_infobae.py) con la planilla de Chacarita: árbitro, DT y once inicial (apellidos resueltos
contra los jugadores de esa época) para celdas vacías.

  python3 -I tools/enrich_infobae.py <infobae.jsonl> [otro.jsonl ...] <salida.json>
"""
import collections
import datetime
import importlib.util
import json
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
spec = importlib.util.spec_from_file_location("er", os.path.join(HERE, "enrich_rivals.py"))
er = importlib.util.module_from_spec(spec)
spec.loader.exec_module(er)
nk = er.nk


def fix(s):  # el archivo de Infobae trae «·» donde iba una vocal con tilde
    return s.replace("·", "á")


def main(paths, out):
    M = json.load(open(os.path.join(ROOT, "data/matches.json"), encoding="utf-8"))
    players = json.load(open(os.path.join(ROOT, "data/players.json"), encoding="utf-8"))
    lineups = json.load(open(os.path.join(ROOT, "data/lineups.json"), encoding="utf-8"))
    byid = {m["id"]: m for m in M}
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
        sur = toks[-2:] if len(toks) >= 2 and toks[-2] in ("de", "del", "la") else toks[-1:]
        c = collections.Counter()
        for y in range(year - 2, year + 3):
            for p, n in pyear[y].items():
                pt = nk(p)
                if pt and (pt[-1] == sur[-1] or (len(pt) > 1 and pt[-2] == sur[-1])):
                    if len(toks) > 1 and pt[0][0] != toks[0][0]:
                        continue
                    c[p] += n
        best = c.most_common(2)
        if not best:
            return None
        return best[0][0] if len(best) == 1 or best[0][1] >= 2 * best[1][1] else None

    arts = []
    for p in paths:
        arts += [json.loads(l) for l in open(p, encoding="utf-8")]
    seen, stats = set(), collections.Counter()
    patch, lu, dif = [], [], []
    for a in arts:
        if a["url"] in seen:
            continue
        seen.add(a["url"])
        b = fix(a["cuerpo"])
        if "ntesis" not in b:
            continue
        mu = re.search(r"infobae\.com/(\d{4})/(\d\d)/(\d\d)/", a["url"])
        ad = datetime.date(int(mu.group(1)), int(mu.group(2)), int(mu.group(3)))
        cands = []
        for m in M:
            md = datetime.date.fromisoformat(m["d"])
            if 0 <= (ad - md).days <= 2:
                opp = nk(m["r"] or "")
                if opp and opp[0] in nk(b) and "hacarita" in b:
                    cands.append(m)
        if len(cands) != 1:
            stats["sin_cruce" if not cands else "ambiguo"] += 1
            continue
        m = cands[0]
        info = dict(id=m["id"], fecha=m["d"], partido=f"{m['l']} {m['gl']}-{m['gv']} {m['v']}")
        src = f"Infobae ({a['url'].split('/')[-2][:60]})"
        sy = b[b.find("ntesis"):]
        arb = re.search(r"Arbitro:\s*([^.:]+?)\s*(?:\.|$|Cancha|Estadio)", sy) or re.search(r"Árbitro:\s*([^.:]+?)\s*(?:\.|$)", sy)
        stats["articulos"] += 1
        if arb:
            v = arb.group(1).strip()
            if not m.get("arb"):
                patch.append({**info, "campo": "Árbitro", "valor": v, "fuente": src}); stats["arb"] += 1
            elif not er.same_name(m["arb"], v):
                dif.append({**info, "campo": "Árbitro", "planilla": m["arb"], "fuente": v, "sitio": src})
        mc = re.search(r"Chacarita(?: Juniors)?:\s*(.+?)\s*(?:DT:|Director t[eé]cnico:)\s*([^.]+?)(?:\.|(?=[A-Z][a-z]+(?: [A-Za-z]+)*:)|$)", sy)
        if mc:
            dt = mc.group(2).strip()
            dtn = next((d for d in dts if nk(d) and nk(dt) and nk(d)[-1] == nk(dt)[-1] and nk(d)[0][0] == nk(dt)[0][0]), None) or (dt if len(nk(dt)) >= 2 else None)
            if dtn:
                if not m.get("dt"):
                    patch.append({**info, "campo": "DT", "valor": dtn, "fuente": src}); stats["dt"] += 1
                elif not er.same_name(m["dt"], dtn):
                    dif.append({**info, "campo": "DT", "planilla": m["dt"], "fuente": dtn, "sitio": src})
            if str(m["id"]) not in lineups:
                names = [x.strip() for x in re.split(r"[;,]| y ", mc.group(1)) if x.strip()]
                if len(names) == 11:
                    rows = []
                    for n_ in names:
                        full = resolve_surname(n_, int(m["d"][:4]))
                        if full and full not in {r_["n"] for r_ in rows}:
                            rows.append({"n": full, "rol": 0})
                    if len(rows) >= 10:
                        lu.append({**info, "jugadores": rows, "fuente": src}); stats["formaciones"] += 1
                    else:
                        stats["formacion_no_resuelta"] += 1
    json.dump({"stats": stats, "patch": patch, "formaciones": lu, "diferencias": dif}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(dict(stats), "diferencias:", len(dif))
    for x in dif[:10]:
        print(x)


if __name__ == "__main__":
    main(sys.argv[1:-1], sys.argv[-1])
