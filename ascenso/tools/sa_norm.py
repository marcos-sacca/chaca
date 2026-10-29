"""
Normaliza lo bajado de Solo Ascenso (sa_scrape.py): un registro por partido con goles asignados a cada lado.

  python3 -I sa_norm.py <carpeta_con_jsonl> <salida.jsonl.gz>

Goles: "70' Ángel Prudencio (TAL)", "90'(+2) Fulano -p- (REA)" (penal), "69' Fulano (e/c) (MUÑ)" (en contra).
El lado que suma el gol se decide por la formación (a qué equipo pertenece el jugador); si no está, por la abreviatura.
"""
import glob
import gzip
import json
import re
import sys
import unicodedata

CATS = ["Primera Nacional", "Primera B", "Primera C", "Promocional Amateur", "Federal A", "Regional Amateur", "Copa Argentina", "Torneo Federal A", "Primera División"]
GOAL = re.compile(r"(\d+)'(?:\(\+(\d+)\))?\s*(.*?)\s*\(([^()]*)\)\s*$")


def nk(s):
    s = unicodedata.normalize("NFD", s or "")
    return re.sub(r"[^a-z ]", "", "".join(c for c in s if unicodedata.category(c) != "Mn").lower()).strip()


def parse_goals(txt):
    out = []
    for part in re.split(r",\s+(?=\d+')", txt or ""):
        part = part.strip()
        if not part:
            continue
        ec = "(e/c)" in part
        pen = "-p-" in part
        part2 = re.sub(r"\s+", " ", part.replace("(e/c)", "").replace("-p-", "")).strip()
        m = GOAL.match(part2)
        if not m:
            out.append(dict(raw=part))
            continue
        out.append(dict(min=int(m.group(1)), extra=int(m.group(2)) if m.group(2) else None, player=m.group(3).strip() or None, abbr=m.group(4).strip(), pen=pen, ec=ec))
    return out


def assign(d):
    names = [{nk(x[1]) for x in e["xi"] + e["sup"]} for e in d["eq"]]
    gl, gv = int(d["gl"]), int(d["gv"])
    gs = parse_goals(d.get("goles", ""))
    for g in gs:
        if "raw" in g or not g.get("player"):
            continue
        own = [i for i in (0, 1) if nk(g["player"]) in names[i]]
        if len(own) == 1:
            g["side"] = (1 - own[0]) if g["ec"] else own[0]
    ab = {}
    for g in gs:
        if g.get("side") is not None and "abbr" in g and not g["ec"]:
            ab.setdefault(g["abbr"], g["side"])
    for g in gs:
        if "raw" in g or g.get("side") is not None:
            continue
        if g["abbr"] in ab:
            s = ab[g["abbr"]]
            g["side"] = (1 - s) if g["ec"] else s
    cl = sum(1 for g in gs if g.get("side") == 0)
    cv = sum(1 for g in gs if g.get("side") == 1)
    d["goles_lista"] = gs
    d["goles_ok"] = (cl == gl and cv == gv)
    return d


def main(src, out):
    rows = {}
    for f in sorted(glob.glob(src + "/*.jsonl")):
        for ln in open(f, encoding="utf-8"):
            try:
                r = json.loads(ln)
            except Exception:
                continue
            if "head" in r:
                rows[r["id"]] = r
    res = []
    for r in sorted(rows.values(), key=lambda x: x["id"]):
        head = [x.strip() for x in r["head"].split("|")]
        r["cat"] = next((x for x in head[1:] if x in CATS), None)
        r["ronda"] = next((x for x in head[2:3] if x not in CATS and not x.startswith(("Estadio", "Árbitro"))), None)
        if not (r["gl"].isdigit() and r["gv"].isdigit()):
            r["sin_resultado"] = 1
            res.append(r)
            continue
        res.append(assign(r))
    with gzip.open(out, "wt", encoding="utf-8") as f:
        for r in res:
            f.write(json.dumps(r, ensure_ascii=False, separators=(",", ":")) + "\n")
    ok = [r for r in res if "goles_ok" in r]
    print(len(res), "partidos;", sum(1 for r in ok if r["goles_ok"]), "de", len(ok), "con goles que cierran con el marcador")


if __name__ == "__main__":
    main(*sys.argv[1:3])
