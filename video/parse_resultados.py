"""
Completa data/resultados_faltantes.csv a partir de texto pegado de una pagina de
resultados (formato "Sáb 12/9 / Final / Local / Visitante / goles / goles"). Guarda
el texto fuente en data/fuente_resultados_*.txt; este script lee TODOS los que haya.

- El marcador del texto es local-visitante (verificado con los partidos de Chacarita).
- Cruza por (local, visitante): cada cruce se juega una sola vez como local, asi que no
  hace falta saber la fecha del torneo. Pone tambien el dia real en que se jugo.
- Solo toca filas con los goles vacios; imprime lo que sigue sin resultado.

Uso:  python video/parse_resultados.py
"""
import csv
import glob
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = HERE / "data"

# nombre en la pagina -> nombre corto de build_data.SHORT (solo equipos de la Zona B)
ZONA_B = {
    "Agropecuario": "Agropecuario", "Almagro": "Almagro", "Atlanta": "Atlanta",
    "Atlético Rafaela": "Atlético Rafaela", "Chacarita Juniors": "Chacarita", "Colegiales": "Colegiales",
    "Deportivo Maipú": "Maipú", "Midland": "Midland", "Gimnasia Jujuy": "Gimnasia (J)",
    "Gimnasia y Tiro": "Gimnasia y Tiro", "Güemes": "Güemes", "Nueva Chicago": "Chicago",
    "Patronato": "Patronato", "Quilmes": "Quilmes", "San Martín San Juan": "San Martín",
    "San Martín Tucumán": "San Martín (T)", "Temperley": "Temperley", "Tristán Suárez": "Tristán Suárez",
}
DAY = re.compile(r"^(Lun|Mar|Mié|Jue|Vie|Sáb|Dom) (\d{1,2})/(\d{1,2})$")


def parse(text):
    """-> lista de (YYYY-MM-DD, local, visitante, goles_local, goles_visitante)"""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    out, day, i = [], None, 0
    while i < len(lines):
        m = DAY.match(lines[i])
        if m:
            day = f"2026-{int(m.group(3)):02d}-{int(m.group(2)):02d}"
            i += 1
        elif lines[i] == "Final" and i + 4 < len(lines) and lines[i + 3].isdigit() and lines[i + 4].isdigit():
            out.append((day, lines[i + 1], lines[i + 2], int(lines[i + 3]), int(lines[i + 4])))
            i += 5
        else:
            i += 1  # "Temporada", rangos "Vie 2/10 — Lun 5/10", etc.
    return out


def main():
    results = {}
    for f in sorted(glob.glob(str(DATA / "fuente_resultados_*.txt"))):
        for day, h, a, hs, as_ in parse(open(f, encoding="utf-8").read()):
            if h in ZONA_B and a in ZONA_B:
                results[(ZONA_B[h], ZONA_B[a])] = (day, hs, as_)
    print(f"{len(results)} partidos de Zona B en los textos fuente")

    # control cruzado: los 6 partidos de Chacarita que se cargaron aparte
    manual = json.load(open(DATA / "chacarita_f29_f34_manual.json", encoding="utf-8"))["matches"]
    bad = [m for m in manual if results.get((m["home"], m["away"]), (None, m["hs"], m["as"]))[1:] != (m["hs"], m["as"])]
    print("Chacarita vs carga manual:", "coincide en los 6" if not bad and len(manual) == 6 else f"DIFIEREN {bad}")

    path = DATA / "resultados_faltantes.csv"
    rows = list(csv.reader(open(path, encoding="utf-8-sig")))
    head, body = rows[0], rows[1:]
    filled = 0
    for r in body:
        if r[4] == "" and (r[2], r[3]) in results:
            day, hs, as_ = results[(r[2], r[3])]
            r[1], r[4], r[5] = day, str(hs), str(as_)
            filled += 1
    csv.writer(open(path, "w", encoding="utf-8-sig", newline="")).writerows([head] + body)
    left = [r for r in body if r[4] == ""]
    print(f"completadas {filled} filas; quedan {len(left)} sin resultado:")
    for r in left:
        print(f"  F{r[0]:>2}  {r[2]} - {r[3]}  ({r[1]}) {r[6]}")


if __name__ == "__main__":
    main()
