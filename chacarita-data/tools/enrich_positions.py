"""
Completa "Posición final" de TORNEOS (Primera División 1931-1985) con las tablas finales de RSSSF:

  https://rsssf.org/tablesa/arghist-pro1930s.html ... arghist-pro1980s.html

Método
- Se parten las páginas en tablas (bloques de filas "pos. equipo PJ G E P GF:GC Pts") y se toma la fila de Chacarita
  (en RSSSF los campeones van en MAYÚSCULAS, por eso la comparación ignora mayúsculas).
- Cada tabla se asigna a un torneo del Excel por orden cronológico y por cantidad de partidos (PJ de la tabla = Partidos del torneo).
- VALIDACIÓN: antes de completar nada se comprueba que el método reproduce las posiciones que el Excel YA tiene.
  Si una tabla no se puede asignar con seguridad, se deja sin completar.
- Solo se completan celdas vacías.

Uso: python3 tools/enrich_positions.py <excel.xlsx> <carpeta_rsssf> <salida.json>
"""
import html
import json
import re
import sys
from pathlib import Path

import pandas as pd

ROW = re.compile(r"^\s*(\d{1,2})?\.?\s+([^\d].*?)\s{2,}(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,2})\s+(\d{1,3}):?\s*-?\s*(\d{1,3})\s+(\d{1,3})\b")


def read_tables(path):
    txt = Path(path).read_text(encoding="latin-1")
    txt = html.unescape(re.sub(r"<[^>]+>", "", txt))
    tables, cur, last_pos, ctx = [], [], None, ""
    for line in txt.splitlines():
        # "Primera División 1963  1. INDEPENDIENTE ..." (encabezado pegado a la 1.ª fila)
        m_head = re.match(r"^(.*?\b(?:19\d\d))\s+(\d{1,2}\.\s+\S.*)$", line)
        if m_head and "Primera" in m_head.group(1):
            ctx, line = m_head.group(1).strip(), m_head.group(2)
        m = ROW.match(line)
        if m and int(m.group(3)) == int(m.group(4)) + int(m.group(5)) + int(m.group(6)):
            pos = m.group(1)
            if pos:
                last_pos = int(pos)
            cur.append(dict(pos=last_pos, team=m.group(2).strip(), pj=int(m.group(3))))
        else:
            if cur and not line.strip().startswith("---"):
                if len(cur) >= 3:
                    tables.append(dict(rows=cur, ctx=ctx))
                cur = []
            if re.match(r"^(Primera División|Campeonato|Metropolitano|Nacional|Torneo|Copa)", line.strip()):
                ctx = line.strip()
    if len(cur) >= 3:
        tables.append(dict(rows=cur, ctx=ctx))
    return tables


def main(xlsx, rsssf_dir, out_json):
    T = pd.read_excel(xlsx, sheet_name="TORNEOS")
    T = T[T["Torneo"].notna()].copy()
    out = dict(validacion=[], patch=[], sin_asignar=[])
    found = []  # (decada, orden, tabla_de_chacarita)
    for dec in range(1930, 1990, 10):
        for t in read_tables(Path(rsssf_dir) / f"arghist-pro{dec}s.html"):
            ch = [r for r in t["rows"] if "chacarita" in r["team"].lower()]
            if ch:
                found.append(dict(dec=dec, ctx=t["ctx"], pj=ch[0]["pj"], pos=ch[0]["pos"], n=len(t["rows"]),
                                  tied=sum(1 for r in t["rows"] if r["pos"] == ch[0]["pos"]) > 1))
    # asignación por orden: recorremos torneos de Primera 1931-1985 y consumimos tablas con el mismo PJ
    prim = T[(T["División"] == "Primera División") & (T["Temporada"].between(1931, 1985))].copy()
    prim = prim[~prim["Torneo"].str.contains("Copa|Petit", regex=True)]
    k, asignados = 0, {}
    for _, r in prim.iterrows():
        pj_excel = int(r["Partidos"])
        for j in range(k, min(k + 3, len(found))):
            f = found[j]
            if f["pj"] == pj_excel or (r["Torneo"].startswith("Campeonato 1934") and f["pj"] == 34):
                asignados[r["Torneo"]] = f
                k = j + 1
                break
    # validación contra lo que el Excel ya tenía
    ok = bad = 0
    for _, r in T.iterrows():
        f = asignados.get(r["Torneo"])
        actual = r["Posición final"]
        if f is None or pd.isna(actual):
            continue
        m = re.match(r"^\s*(\d+)", str(actual))
        if not m:
            continue
        coincide = int(m.group(1)) == f["pos"]
        ok += coincide
        bad += (not coincide)
        out["validacion"].append(dict(torneo=r["Torneo"], excel=str(actual), rsssf=f["pos"], coincide=bool(coincide)))
    out["resumen_validacion"] = dict(coinciden=int(ok), difieren=int(bad))
    # Solo se completan torneos con asignación firme:
    #  - 1931-1935 y 1942: la tabla de RSSSF lleva el año en su título.
    #  - 1971-1978: tablas sin título pero en orden cronológico y con PJ igual al del Excel; el mismo método reproduce
    #    exactamente las posiciones ya cargadas de 1973 y 1974.
    #  Quedan afuera 1936-1940 (tablas "Copa de Oro/Plata"), 1967-1970 (Nacional/Metropolitano en otro orden),
    #  1979 y 1984-86 (el Excel ya difiere de RSSSF).
    def firme(tn, temporada):
        return (1931 <= temporada <= 1935 or temporada == 1942 or 1971 <= temporada <= 1978)
    for _, r in prim.iterrows():
        f = asignados.get(r["Torneo"])
        actual = r["Posición final"]
        if f is None:
            out["sin_asignar"].append(r["Torneo"])
            continue
        if pd.isna(actual) and firme(r["Torneo"], int(r["Temporada"])):
            ties = " (compartido)" if f["tied"] else ""
            de = f" de {f['n']}" if not (f["n"] < 15 and int(r["Temporada"]) < 1940) else ""  # la tabla de 1934 viene cortada en RSSSF
            out["patch"].append(dict(torneo=r["Torneo"], campo="Posición final", valor=f"{f['pos']}°{de}{ties}",
                                     fuente=f"RSSSF arghist-pro{f['dec']}s.html"))
    Path(out_json).write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
    print("validación:", out["resumen_validacion"], "| nuevas:", len(out["patch"]), "| sin asignar:", len(out["sin_asignar"]))
    for v in out["validacion"]:
        if not v["coincide"]:
            print("  DIFIERE", v)
    for p in out["patch"][:80]:
        print("  +", p["torneo"], "->", p["valor"])


if __name__ == "__main__":
    main(*sys.argv[1:4])
