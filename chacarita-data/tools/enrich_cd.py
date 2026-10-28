"""Cruza las notas de Chacarita Digital (parse_cd.py) con la planilla y propone árbitro, DT, entradas, cancha y formaciones para celdas vacías.

Uso: python3 -I tools/enrich_cd.py <cd_matches.json> <salida.json>
Cruce: fecha exacta + marcador + condición (local/visitante). Además mide cuánto coincide con los datos que la planilla ya tenía.
"""
import collections, datetime, json, os, re, sys, unicodedata

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


def nrm(s):
    s = unicodedata.normalize("NFD", s or "")
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return " ".join(re.sub(r"[^a-z ]", " ", s).split())


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


def same_person(a, b):
    """¿Los dos nombres (árbitro / DT) son la misma persona? Compara apellido y nombre de pila con tolerancia."""
    ta, tb = nrm(a).split(), nrm(b).split()
    if not ta or not tb:
        return False
    if ta[-1] == tb[-1] or lev(ta[-1], tb[-1]) <= 1:
        return ta[0][0] == tb[0][0] or len(ta) == 1 or len(tb) == 1
    return set(ta) & set(tb) and len(set(ta) & set(tb)) >= 2


def player_key(full):
    """'Juan Carlos DE LA CRUZ' / 'PEDRO FERNÁNDEZ' / 'Eduardo Alterio' -> (nombre de pila, apellido)"""
    toks = full.replace(".", " ").split()
    if not toks:
        return None, None
    up = [t for t in toks if t.isupper() and len(t) > 1]
    if up and len(up) < len(toks):
        first = toks[0]
        sur = " ".join(t for t in toks if t.isupper())
    else:
        first, sur = toks[0], toks[-1] if len(toks) > 1 else toks[0]
    return first, sur


def main(cd_path, out):
    M = json.load(open(os.path.join(ROOT, "data/matches.json"), encoding="utf-8"))
    players = json.load(open(os.path.join(ROOT, "data/players.json"), encoding="utf-8"))
    lineups = json.load(open(os.path.join(ROOT, "data/lineups.json"), encoding="utf-8"))
    cd = json.load(open(cd_path, encoding="utf-8"))
    byday = collections.defaultdict(list)
    for m in M:
        byday[m["d"]].append(m)
    pk = collections.defaultdict(list)
    for p in players:
        base = re.sub(r"\s*\([^)]*\)", "", p)
        t = nrm(base).split()
        if len(t) >= 2:
            pk[(t[0], t[-1])].append(p)
        pk[("", t[-1] if t else "")].append(p)
    cd_known = {nrm(m["cd"]): m["cd"] for m in M if m.get("cd")}
    stats = collections.Counter()
    patch, lu, nuevos, sin = [], [], collections.Counter(), []
    seen = set()
    for x in cd:
        t0, t1 = x["teams"]
        side = 0 if t0["name"].upper().startswith("CHACARITA") else 1 if t1["name"].upper().startswith("CHACARITA") else None
        if side is None:
            stats["sin_chacarita"] += 1
            continue
        mine, rival = x["teams"][side], x["teams"][1 - side]
        gf, gc = mine["goals"], rival["goals"]
        d0 = datetime.date.fromisoformat(x["date"])
        cands = []
        for k in (0, 1, -1, 2, -2):
            for m in byday.get((d0 + datetime.timedelta(days=k)).isoformat(), []):
                if m["gf"] == gf and m["gc"] == gc and (m["c"] == "N" or (m["c"] == "L") == (side == 0)):
                    cands.append(m)
            if cands:
                break
        if len(cands) > 1:
            op = nrm(rival["name"])
            cands = [m for m in cands if lev(nrm(m["r"]), op) <= 6 or op.startswith(nrm(m["r"])[:5])] or cands
        if not cands:
            stats["sin_cruce"] += 1
            sin.append((x["date"], x["teams"][0]["name"], x["teams"][0]["goals"], x["teams"][1]["goals"], x["teams"][1]["name"], x["post"]))
            continue
        if len(cands) > 1 or x["url"] + x["date"] + str(gf) in seen:
            stats["ambiguo"] += 1
            continue
        seen.add(x["url"] + x["date"] + str(gf))
        m = cands[0]
        stats["cruzados"] += 1
        fuente = f"Chacarita Digital · {x['post']} ({x['url']})"
        base = {"id": m["id"], "fecha": m["d"], "partido": f"{m['l']} {m['gl']}-{m['gv']} {m['v']}", "fuente": fuente}
        ref = x.get("referee")
        if ref:
            if m.get("arb"):
                stats["arb_comparados"] += 1
                stats["arb_iguales"] += bool(same_person(m["arb"], ref))
                if not same_person(m["arb"], ref):
                    stats.setdefault("arb_dif", []).append((m["id"], m["arb"], ref)) if isinstance(stats.get("arb_dif"), list) else None
            else:
                patch.append({**base, "campo": "Árbitro", "valor": ref.strip().title() if ref.isupper() else ref.strip()})
                stats["arb_nuevos"] += 1
        dt = mine.get("dt")
        if dt:
            dtn = dt.strip().title() if dt.isupper() else dt.strip()
            if m.get("dt"):
                stats["dt_comparados"] += 1
                stats["dt_iguales"] += bool(same_person(m["dt"], dtn))
            else:
                patch.append({**base, "campo": "DT", "valor": dtn})
                stats["dt_nuevos"] += 1
        en = x.get("entradas")
        if en:
            if m.get("esp") is not None:
                stats["esp_comparados"] += 1
                stats["esp_iguales"] += (abs(int(m["esp"]) - en) <= max(5, 0.02 * en))
            else:
                patch.append({**base, "campo": "Espectadores", "valor": en})
                stats["esp_nuevos"] += 1
        cn = (x.get("cancha") or "").strip()
        if cn and not m.get("cd") and nrm(cn) in cd_known:
            patch.append({**base, "campo": "Cancha", "valor": cd_known[nrm(cn)]})
            stats["cancha_nuevos"] += 1
        elif cn and m.get("cd"):
            stats["cancha_comparados"] += 1
            stats["cancha_iguales"] += (nrm(cn) == nrm(m["cd"]) or nrm(cn).split("(")[0] == nrm(m["cd"]).split("(")[0] or nrm(m["cd"]) in nrm(cn))
        # formación
        if str(m["id"]) not in lineups:
            xi = [(n, mi, ent) for n, mi, ent in mine["players"]]
            if len(xi) >= 10:
                rows = []
                for n, mi, ent in xi:
                    rows.append({"cd": n, "rol": 0})
                    if ent:
                        rows.append({"cd": ent, "rol": 1})
                lu.append({**base, "jugadores": rows})
                stats["formaciones"] += 1
    json.dump({"stats": {k: v for k, v in stats.items() if not isinstance(v, list)}, "patch": patch, "formaciones": lu, "sin_cruce": sin[:400]}, open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)
    print({k: v for k, v in stats.items() if not isinstance(v, list)})


if __name__ == "__main__":
    main(*sys.argv[1:3])
