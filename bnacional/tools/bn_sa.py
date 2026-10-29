"""Partidos de la Primera Nacional desde las síntesis de Solo Ascenso (ascenso/tools), con goleadores, árbitro y cancha.

Reemplaza a Transfermarkt como fuente principal en las temporadas que la crónica de Historia y Fútbol no cubre; Transfermarkt queda para el control cruzado.
"""
import collections
import gzip
import json
import re

# ventana de fechas de cada temporada (la Primera Nacional 2019/20 se cortó en marzo de 2020 por la pandemia)
VENTANAS = {
    "2017/18": ("2017-08-01", "2018-07-31"),
    "2019/20": ("2019-08-01", "2020-07-31"),
    "Transición 2020": ("2020-10-01", "2021-02-28"),
    "2021": ("2021-03-01", "2021-12-31"),
    "2022": ("2022-01-01", "2022-12-31"),
    "2023": ("2023-01-01", "2023-12-31"),
    "2024": ("2024-01-01", "2024-12-31"),
    "2025": ("2025-01-01", "2025-12-31"),
    "2026": ("2026-01-01", "2026-12-31"),
}


def cargar(path):
    rows = []
    with gzip.open(path, "rt", encoding="utf-8") as f:
        for ln in f:
            r = json.loads(ln)
            if r.get("cat") == "Primera Nacional" and not r.get("sin_resultado"):
                # fecha sin jugar cargada como 0-0 (sin formaciones ni goles): no es un resultado
                if r["gl"] == "0" and r["gv"] == "0" and not any(e["xi"] for e in r["eq"]):
                    continue
                rows.append(r)
    return rows


def goles(r):
    """-> (hs, as_) en el formato de jc_parse: [{'n','k','pen','ec'}], con el gol en contra del lado que lo suma"""
    out = ([], [])
    cnt = [collections.OrderedDict(), collections.OrderedDict()]
    incompleto = 0
    for g in r.get("goles_lista", []):
        if g.get("side") not in (0, 1) or not g.get("player"):
            incompleto += 1
            continue
        k = (g["player"], bool(g.get("ec")))
        e = cnt[g["side"]].setdefault(k, dict(n=g["player"], k=0, pen=0, ec=bool(g.get("ec"))))
        e["k"] += 1
        e["pen"] += 1 if g.get("pen") else 0
    return list(cnt[0].values()), list(cnt[1].values()), incompleto


def partidos(rows, label, code, resolve, errores, fuentes_id, season_code):
    d0, d1 = VENTANAS[label]
    out = []
    for r in rows:
        if not (d0 <= r["fecha"] <= d1):
            continue
        h, a = resolve(r["local"]), resolve(r["visitante"])
        if not h or not a:
            errores.append([label, "Fase regular", fuentes_id, f"{r['local']} - {r['visitante']}", f"equipo sin resolver ({r['local'] if not h else r['visitante']})"])
            continue
        hs, as_, inc = goles(r)
        mt = re.match(r"Fecha (\d+)", r.get("ronda") or "")
        est = r.get("estadio") or ""
        est = "" if est in ("", "()") else est
        out.append(dict(season=label, code=code, fase="Fase regular", red=False, stage=None, leg=None, fecha_n=int(mt.group(1)) if mt else None, date=r["fecha"], city="",
                        cancha=est or f"Cancha de {h}", origen="Indicada en la fuente" if est else "Asumida: cancha del local", home=h, away=a, hg=int(r["gl"]), ag=int(r["gv"]), estado="Jugado",
                        obs=("Goleadores incompletos en la fuente." if inc else ""), hsrc=r["local"], asrc=r["visitante"], src=fuentes_id, hs=hs, as_=as_, extra="", ptsw=3, post=fuentes_id,
                        arbitro=r.get("arbitro") or "", sa_id=r["id"]))
    return out
