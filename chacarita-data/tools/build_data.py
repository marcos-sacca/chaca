"""
Convierte el Excel "DATACHACA Máster" en los JSON que usa la página (chacarita-data/data/*.json).

  python3 tools/build_data.py <excel.xlsx> [parche.json ...]

- Lee solo las hojas base: PARTIDOS, GOLES, APARICIONES, TORNEOS, JUGADORES, ESTADIOS.
- Las hojas "para publicar" del Excel son tableros calculados por fórmula; la página los recalcula en vivo
  y esos resultados se verifican contra el Excel en tools/verify_vs_excel.py.
- Los parches (datos completados desde otras fuentes) solo llenan celdas VACÍAS y quedan marcados en cada partido
  (campo "enr") para que la página lo indique.
"""
import json
import re
import sys
import unicodedata
import warnings
from datetime import datetime
from pathlib import Path

import pandas as pd

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "data"
OUT.mkdir(exist_ok=True)


def norm(s):
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", "", s).strip()


def clean(v):
    if v is None or (isinstance(v, float) and pd.isna(v)) or v is pd.NaT:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v or None
    return v


def num(v):
    v = clean(v)
    if v is None:
        return None
    m = re.match(r"^\s*(\d+)", str(v))
    return int(m.group(1)) if m else None


def main(xlsx, patches):
    P = pd.read_excel(xlsx, sheet_name="PARTIDOS")
    P = P[P["ID"].notna()].copy()
    G = pd.read_excel(xlsx, sheet_name="GOLES")
    G = G[G["ID Partido"].notna()].copy()
    A = pd.read_excel(xlsx, sheet_name="APARICIONES").iloc[:, :4]
    A.columns = ["id", "jug", "rol", "fuente"]
    A = A[A["id"].notna()].copy()
    T = pd.read_excel(xlsx, sheet_name="TORNEOS")
    T = T[T["Torneo"].notna()].copy()
    J = pd.read_excel(xlsx, sheet_name="JUGADORES")
    J = J[J["Clave (normalizada)"].notna()].copy()
    E = pd.read_excel(xlsx, sheet_name="ESTADIOS")
    E = E[E["Club (rival oficial)"].notna()].copy()

    # ---- parches (celdas vacías completadas desde otras fuentes)
    patch, tpatch = {}, {}
    for pf in patches:
        for x in json.loads(Path(pf).read_text(encoding="utf-8"))["patch"]:
            if "torneo" in x:
                tpatch.setdefault(x["torneo"], (x["valor"], x["fuente"]))
            else:
                patch.setdefault(int(x["id"]), {}).setdefault(x["campo"], (x["valor"], x["fuente"]))

    # ---- torneos
    torneos = []
    tindex = {}
    for _, r in T.iterrows():
        name = str(r["Torneo"]).strip()
        tindex[name] = len(torneos)
        pos, pos_enr = clean(r["Posición final"]), None
        if pos is None and name in tpatch:
            pos, pos_enr = tpatch[name][0], tpatch[name][1]
        torneos.append(dict(
            n=name, s=num(r["Temporada"]), div=clean(r["División"]), tipo=clean(r["Tipo"]),
            pos=pos, pos_fuente=pos_enr, nota=clean(r["Notas"]),
            sd=str(clean(r["Temporada deportiva"]) or ""),
            desde=str(r["Desde"])[:10] if clean(r["Desde"]) is not None else None,
            hasta=str(r["Hasta"])[:10] if clean(r["Hasta"]) is not None else None,
        ))

    # ---- goles por partido
    goals = {}
    for _, r in G.iterrows():
        mid = int(r["ID Partido"])
        name = clean(r["Jugador oficial"]) or clean(r["Jugador (como figura)"])
        goals.setdefault(mid, []).append(dict(
            p=name, m=num(r["Minuto"]), pen=1 if clean(r["Penal"]) else 0, ec=1 if clean(r["En contra"]) else 0))

    # ---- partidos
    matches = []
    for _, r in P.sort_values(["Fecha", "ID"]).iterrows():
        mid = int(r["ID"])
        gl_raw, gv_raw = clean(r["G.L"]), clean(r["G.V"])
        gl, gv = num(gl_raw), num(gv_raw)
        pen = None
        m1, m2 = re.search(r"\((\d+)\)", str(gl_raw)), re.search(r"\((\d+)\)", str(gv_raw))
        if m1 and m2:
            pen = [int(m1.group(1)), int(m2.group(1))]
        cond = {"Local": "L", "Visitante": "V", "Neutral": "N"}[r["Condición"]]
        res = {"Ganó": "G", "Empató": "E", "Perdió": "P"}[r["Resultado"]]
        item = dict(
            id=mid, d=str(r["Fecha"])[:10], t=tindex[str(r["Torneo"]).strip()], j=clean(r["Jornada / Instancia"]),
            l=r["Local"], v=r["Visitante"], gl=gl, gv=gv, r=r["Rival oficial"], c=cond, res=res,
            gf=num(r["GF"]), gc=num(r["GC"]), pt=num(r["Puntos"]),
            e=clean(r["Estadio (nombre actual)"]), cd=clean(r["Cancha (club dueño)"]),
            dt=clean(r["DT"]), arb=clean(r["Árbitro"]), esp=num(r["Espectadores"]), nt=clean(r["Notas"]),
        )
        if pen:
            item["pen"] = pen
        enr = []
        for campo, key in (("Árbitro", "arb"), ("Espectadores", "esp"), ("DT", "dt")):
            if item[key] is None and mid in patch and campo in patch[mid]:
                item[key] = patch[mid][campo][0]
                enr.append(key)
        if enr:
            item["enr"] = enr
        if mid in goals:
            item["g"] = goals[mid]
        matches.append(item)

    # ---- jugadores y formaciones
    clave2of = {norm(r["Clave (normalizada)"]): clean(r["Jugador oficial"]) for _, r in J.iterrows()}
    players, pidx = [], {}

    def pid(name):
        if name not in pidx:
            pidx[name] = len(players)
            players.append(name)
        return pidx[name]

    lineups = {}
    for _, r in A.iterrows():
        nm = clave2of.get(norm(r["jug"])) or str(r["jug"]).strip()
        lineups.setdefault(str(int(r["id"])), []).append([pid(nm), 0 if r["rol"] == "Titular" else 1])
    for g in goals.values():
        for x in g:
            if x["p"]:
                pid(x["p"])

    # ---- estadios
    estadios = [dict(club=r["Club (rival oficial)"], estadio=clean(r["Estadio habitual"]), ciudad=clean(r["Ciudad"]), nota=clean(r["Notas"]))
                for _, r in E.iterrows()]

    meta = dict(
        generado=datetime.now().strftime("%Y-%m-%d"), partidos=len(matches),
        ultimo_partido=max(m["d"] for m in matches), primer_partido=min(m["d"] for m in matches),
        goles=int(len(G)), formaciones=int(len(A)), partidos_con_formacion=len(lineups),
        enriquecidos={k: sum(1 for m in matches if k in m.get("enr", [])) for k in ("arb", "esp", "dt")},
        posiciones_completadas=sum(1 for t in torneos if t.get("pos_fuente")),
    )
    for name, obj in (("matches", matches), ("torneos", torneos), ("players", players), ("lineups", lineups),
                      ("estadios", estadios), ("meta", meta)):
        (OUT / f"{name}.json").write_text(json.dumps(obj, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
        print(f"{name}.json  {(OUT / f'{name}.json').stat().st_size / 1024:.0f} KB")
    print(meta)


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2:])
