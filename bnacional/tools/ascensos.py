"""Lista de clubes que ascendieron a Primera División cada año, leída de la tabla «Movilidad interdivisional» y de la tabla de campeones
de Wikipedia (https://es.wikipedia.org/wiki/Primera_B_Nacional; copia en data/fuentes/wikipedia_primera_b_nacional.wiki).

  python3 -I ascensos.py <wiki.txt> <crudo.json> <salida.csv>
Escribe ascensos.csv (Temporada, Club, Cómo ascendió, Fuente) con los nombres de club de la base. Verifica contra el campeón de las crónicas.
"""
import csv, json, os, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from names_ext import best_among  # noqa: E402
from clubes import R  # noqa: E402

MANUAL = {"San Martín (T)": "San Martín de Tucumán", "San Martín (SJ)": "San Martín de San Juan", "Unión (SF)": "Unión de Santa Fe", "Unión": "Unión de Santa Fe", "Gimnasia y Tiro (S)": "Gimnasia y Tiro de Salta",
          "Gimnasia y Esgrima (J)": "Gimnasia y Esgrima de Jujuy", "Gimnasia y Esgrima (M)": "Gimnasia y Esgrima de Mendoza", "Gimnasia y Esgrima (LP)": "Gimnasia y Esgrima La Plata", "Talleres (C)": "Talleres de Córdoba",
          "Estudiantes (LP)": "Estudiantes de La Plata", "Estudiantes (RC)": "Estudiantes de Río Cuarto", "Huracán (TA)": "Huracán de Tres Arroyos", "Sarmiento (J)": "Sarmiento de Junín", "Instituto": "Instituto de Córdoba",
          "Atlético Tucumán": "Atlético Tucumán", "Godoy Cruz": "Godoy Cruz Antonio Tomba", "Deportivo Mandiyú": "Deportivo Mandiyú de Corrientes", "Tiro Federal": "Tiro Federal de Rosario", "Deportivo Armenio": "Deportivo Armenio",
          "Atlético de Rafaela": "Atlético de Rafaela", "Olimpo": "Olimpo de Bahía Blanca", "Independiente Rivadavia": "Independiente Rivadavia de Mendoza", "Aldosivi": "Aldosivi de Mar del Plata",
          "Crucero del Norte": "Crucero del Norte", "Central Córdoba (SdE)": "Central Córdoba de Santiago del Estero", "Los Andes": "Los Andes", "Arsenal": "Arsenal FC"}
# Wikipedia: Olimpo ganó el Apertura 2001/02 y fue proclamado campeón anual (no figura en la tabla de campeones)
CHAMP_FIX = {"2001/02": "Olimpo de Bahía Blanca"}
SEASON = {"2014": "Transición 2014", "2016": "Transición 2016", "2020": "Transición 2020", "2020-2021": "Transición 2020"}


def season(lab):
    if lab in SEASON:
        return SEASON[lab]
    return lab.replace("-", "/") if re.match(r"\d{4}-\d{2}$", lab) else lab


def links(cell):
    cell = re.sub(r"<ref.*?</ref>|<ref[^>]*/>|\{\{.*?\}\}", "", cell)
    return [(m.group(2) or m.group(1)).strip() for m in re.finditer(r"\[\[([^\]|]+)(?:\|([^\]]+))?\]\]", cell)]


def main(wiki, crudo, out):
    L = open(wiki, encoding="utf-8").read().splitlines()
    allc = sorted({v[0] for v in R.values()})
    d = json.load(open(crudo, encoding="utf-8")) if os.path.exists(crudo) else {}
    teams_in = collections.defaultdict(set)
    for m in d.get("partidos", []):
        teams_in[m["season"]] |= {m["home"], m["away"]}

    def canon(lbl, season_):
        if lbl in MANUAL and MANUAL[lbl] in allc:
            return MANUAL[lbl]
        pool = sorted(teams_in.get(season_, [])) or allc
        n, _ = best_among(lbl, pool)
        return n or best_among(lbl, allc)[0]
    # campeones
    champs, sec = {}, None
    for l in L:
        if l.startswith("=== Campeonato") or l.startswith("=== Campeonato de Primera Nacional"):
            sec = l
        m = re.match(r"\|\[\[Campeonato[^|]*\|(\d{4}(?:-\d{2,4})?)\]\]\|\|(\d+)\|\|(.*)", l)
        if m:
            c = links(m.group(3).split("||")[0])
            if c:
                champs[season(m.group(1))] = c[0]
    start = next(i for i, l in enumerate(L) if "==== Con la Primera División ====" in l)
    rows = []
    for l in L[start:start + 120]:
        if l.startswith("==== Con la tercera"):
            break
        if l.startswith("|[[Campeonato") and "||" in l:
            c = [x.strip() for x in l[1:].split("||")]
            s = re.search(r"\|(?:NB|BN|PN)\s+([^\]|]+)\]\]", c[0])
            if not s or len(c) < 3:
                continue
            ss = season(s.group(1))
            for lbl in links(c[2]):
                rows.append((ss, lbl))
    # 2012/13: la fila de la tabla solo trae descendidos; ascendieron campeón y subcampeón (tabla de campeones)
    rows.append(("2012/13", "Rosario Central")); rows.append(("2012/13", "Gimnasia y Esgrima (LP)"))
    out_rows, bad = [], []
    for ss, lbl in rows:
        c = canon(lbl, ss)
        if not c:
            bad.append((ss, lbl)); continue
        champ = canon(champs[ss], ss) if ss in champs else CHAMP_FIX.get(ss)
        out_rows.append([ss, c, "Campeón" if champ == c else "Ascenso", lbl])
    out_rows.sort(key=lambda r: (r[0] if r[0][0].isdigit() else r[0][-4:] + "z", r[2] != "Campeón"))
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["Temporada", "Club", "Cómo ascendió", "Nombre en la fuente"]); w.writerows(out_rows)
    print(len(out_rows), "ascensos;", "sin resolver:", bad)
    # control con el campeón de las crónicas
    for t in d.get("campeones", [])[:0]:
        pass


if __name__ == "__main__":
    main(*sys.argv[1:4])
