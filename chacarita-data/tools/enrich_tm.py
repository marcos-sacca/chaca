"""Cruza lo bajado de Transfermarkt (scrape_tm.py) con la planilla y propone árbitro, DT, formaciones y espectadores para celdas vacías.

Uso: python3 -I tools/enrich_tm.py <tm_chacarita.json> <salida.json>
Cruce: fecha (±1 día; el sitio muestra horario europeo), marcador y condición (local/visitante). Solo si hay un único candidato.
"""
import collections, datetime, json, os, re, sys, unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def nk(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z ]", " ", s).split()


def main(tm_path, out):
    M = json.load(open(os.path.join(ROOT, "data/matches.json"), encoding="utf-8"))
    players = json.load(open(os.path.join(ROOT, "data/players.json"), encoding="utf-8"))
    lineups = json.load(open(os.path.join(ROOT, "data/lineups.json"), encoding="utf-8"))
    tm = json.load(open(tm_path, encoding="utf-8"))["matches"]
    byday = collections.defaultdict(list)
    for m in M:
        byday[m["d"]].append(m)
    full = {" ".join(nk(p)): p for p in players}
    # índice por apellido + inicial de jugadores de Chacarita (para completar nombres)
    bysur = collections.defaultdict(list)
    for p in players:
        t = nk(p)
        if t:
            bysur[t[-1]].append(p)
    stats = collections.Counter()
    patch, lu, unmatched = [], [], []
    for rid, x in tm.items():
        rep = x.get("rep")
        if not rep or x.get("res") is None:
            stats["sin_ficha"] += 1
            continue
        d, mth, y = x["date"].split("/")
        d0 = datetime.date(int(y), int(mth), int(d))
        a, b = x["res"]
        home = x["ha"] == "H"
        gf, gc = (a, b) if home else (b, a)
        cands = []
        for k in (0, -1, 1):
            for m in byday.get((d0 + datetime.timedelta(days=k)).isoformat(), []):
                if m["gf"] == gf and m["gc"] == gc and (m["c"] == "L") == home and m["c"] != "N":
                    cands.append((abs(k), m))
        if not cands:
            stats["sin_cruce"] += 1
            unmatched.append((rid, x["date"], x["opp"], x["res"], x["ha"]))
            continue
        cands.sort(key=lambda z: z[0])
        if len(cands) > 1 and cands[0][0] == cands[1][0]:
            stats["ambiguo"] += 1
            continue
        m = cands[0][1]
        stats["cruzados"] += 1
        src = f"Transfermarkt (ficha {rid})"
        if not m.get("arb") and rep.get("referee"):
            patch.append({"id": m["id"], "fecha": m["d"], "partido": f"{m['l']} {m['gl']}-{m['gv']} {m['v']}", "campo": "Árbitro", "valor": rep["referee"], "fuente": src})
            stats["arb"] += 1
        mg = rep.get("managers") or []
        if not m.get("dt") and len(mg) == 2:
            patch.append({"id": m["id"], "fecha": m["d"], "partido": f"{m['l']} {m['gl']}-{m['gv']} {m['v']}", "campo": "DT", "valor": mg[0] if home else mg[1], "fuente": src})
            stats["dt"] += 1
        if m.get("esp") is None and rep.get("attendance"):
            patch.append({"id": m["id"], "fecha": m["d"], "partido": f"{m['l']} {m['gl']}-{m['gv']} {m['v']}", "campo": "Espectadores", "valor": rep["attendance"], "fuente": src})
            stats["esp"] += 1
        # formación de Chacarita
        if str(m["id"]) not in lineups and rep.get("lineups") and len(rep["lineups"]) == 2:
            side = rep["lineups"][0 if home else 1]
            xi = side.get("xi", [])
            if len(xi) == 11:
                names = []
                sub_in = [s["in"] for s in rep.get("subs_in", []) if s.get("in")]
                # los cambios de la ficha traen ambos equipos: se conservan los que figuran en el banco de Chacarita
                bench = {s["full"] for s in side.get("bench", [])}
                for p in xi:
                    names.append((p["full"], p["n"], 0))
                for s in sub_in:
                    if s in bench:
                        names.append((s, s.split()[-1], 1))
                lu.append({"id": m["id"], "fecha": m["d"], "partido": f"{m['l']} {m['gl']}-{m['gv']} {m['v']}", "jugadores": [{"tm": f, "corto": n_, "rol": r} for f, n_, r in names], "fuente": src})
                stats["formaciones"] += 1
    json.dump({"stats": stats, "patch": patch, "formaciones": lu, "sin_cruce": unmatched}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print(dict(stats))


if __name__ == "__main__":
    main(*sys.argv[1:3])
