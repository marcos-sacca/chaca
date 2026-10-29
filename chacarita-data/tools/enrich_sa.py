"""
Cruza las síntesis de Solo Ascenso (ascenso/tools/sa_norm.py) con la planilla de Chacarita y propone árbitro, DT y formaciones
(titulares + suplentes que entraron) para celdas vacías. Informa dónde el árbitro/DT de la planilla difieren.

  python3 -I tools/enrich_sa.py <norm.jsonl.gz> <salida.json>
Cruce: fecha exacta, marcador y condición (local/visitante) de Chacarita. Solo si hay un único candidato.
"""
import collections
import datetime
import gzip
import json
import os
import re
import sys
import unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def nk(s):
    s = unicodedata.normalize("NFD", s or "")
    return re.sub(r"[^a-z ]", "", "".join(c for c in s if unicodedata.category(c) != "Mn").lower()).split()


def same(a, b):
    ta, tb = nk(a), nk(b)
    import difflib
    sim = lambda x, y: x == y or difflib.SequenceMatcher(None, x, y).ratio() >= 0.85
    return bool(ta and tb and (sim(ta[-1], tb[-1]) or any(sim(ta[-1], t) for t in tb) or any(sim(tb[-1], t) for t in ta)))


def main(src, out):
    M = json.load(open(os.path.join(ROOT, "data/matches.json"), encoding="utf-8"))
    lineups = json.load(open(os.path.join(ROOT, "data/lineups.json"), encoding="utf-8"))
    byday = collections.defaultdict(list)
    for m in M:
        byday[m["d"]].append(m)
    stats = collections.Counter()
    patch, lu, dif, sin, gdif = [], [], [], [], []
    for ln in gzip.open(src, "rt", encoding="utf-8"):
        r = json.loads(ln)
        if r.get("sin_resultado") or "Chacarita" not in r["local"] + r["visitante"]:
            continue
        if "Chacarita" in r["local"] and "Chacarita" in r["visitante"]:
            continue
        home = "Chacarita" in r["local"]
        gl, gv = int(r["gl"]), int(r["gv"])
        gf, gc = (gl, gv) if home else (gv, gl)
        d0 = datetime.date.fromisoformat(r["fecha"])
        cands = []
        for k in (0, -1, 1):  # el sitio a veces fecha el partido nocturno un día antes o después
            for m in byday.get((d0 + datetime.timedelta(days=k)).isoformat(), []):
                if m["gf"] == gf and m["gc"] == gc and (m["c"] == "L") == home and m["c"] != "N":
                    cands.append((abs(k), m))
        cands.sort(key=lambda z: z[0])
        if len(cands) > 1 and cands[0][0] == cands[1][0]:
            cands = cands[:2]
        else:
            cands = cands[:1]
        cands = [m for _, m in cands]
        if len(cands) != 1:
            stats["sin_cruce" if not cands else "ambiguo"] += 1
            if not cands and not r.get("sin_resultado"):
                sin.append(dict(sitio_id=r["id"], fecha=r["fecha"], categoria=r.get("cat"), partido=f"{r['local']} {gl}-{gv} {r['visitante']}"))
            continue
        m = cands[0]
        stats["cruzados"] += 1
        src_ = f"Solo Ascenso (síntesis {r['id']})"
        info = dict(id=m["id"], fecha=m["d"], partido=f"{m['l']} {m['gl']}-{m['gv']} {m['v']}")
        arb = r.get("arbitro")
        if arb:
            if not m.get("arb"):
                patch.append({**info, "campo": "Árbitro", "valor": arb, "fuente": src_}); stats["arb"] += 1
            elif not same(m["arb"], arb):
                dif.append({**info, "campo": "Árbitro", "planilla": m["arb"], "fuente": arb, "sitio": src_})
        # goleadores de Chacarita: planilla vs. síntesis
        mine_ = sorted(nk(g["p"])[-1] for g in m.get("g", []) if g["p"] and not g["ec"] and nk(g["p"]))
        sa_ = sorted(nk(g["player"])[-1] for g in r.get("goles_lista", []) if g.get("player") and nk(g["player"]) and g.get("side") == (0 if home else 1) and not g.get("ec"))
        if r.get("goles_ok") and mine_ != sa_ and len(m.get("g", [])) >= 1:
            gdif.append({**info, "planilla": "; ".join(g["p"] or "?" for g in m.get("g", []) if not g["ec"]), "solo_ascenso": "; ".join(g["player"] for g in r["goles_lista"] if g.get("side") == (0 if home else 1) and not g.get("ec")), "sitio": src_})
        eq = r["eq"][0 if home else 1]
        if eq.get("dt"):
            if not m.get("dt"):
                patch.append({**info, "campo": "DT", "valor": eq["dt"], "fuente": src_}); stats["dt"] += 1
            elif not same(m["dt"], eq["dt"]):
                dif.append({**info, "campo": "DT", "planilla": m["dt"], "fuente": eq["dt"], "sitio": src_})
        if str(m["id"]) not in lineups and len(eq["xi"]) == 11:
            jug = [{"n": x[1], "rol": 0} for x in eq["xi"]]
            sup = {x[1] for x in eq["sup"]}
            seen = set()
            for part in re.split(r",\s+(?=\d+')", r.get("cambios", "") or ""):
                mm = re.match(r"\d+'(?:\(\+\d+\))?\s*(.+?)\s+x\s+(.+?)\s*\(([^()]*)\)\s*$", part.strip())
                if mm and mm.group(1) in sup and mm.group(1) not in seen:
                    seen.add(mm.group(1)); jug.append({"n": mm.group(1), "rol": 1})
            lu.append({**info, "jugadores": jug, "fuente": src_}); stats["formaciones"] += 1
    json.dump({"stats": stats, "patch": patch, "formaciones": lu, "diferencias": dif, "sin_cruce": sin, "goleadores_distintos": gdif}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(dict(stats), "diferencias:", len(dif), "goleadores distintos:", len(gdif))
    for x in dif[:15]:
        print(x)


if __name__ == "__main__":
    main(*sys.argv[1:3])
