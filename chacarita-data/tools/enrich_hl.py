"""
Completa árbitro, público (solo "ENTRADAS") y DT de los partidos de Primera División 1932-1984
usando los PDF de Historical-Lineups ("Fútbol Argentino: Crónicas y Estadísticas").

  https://www.historical-lineups.com/wp-content/uploads/2019/11/<AÑO>.pdf

Reglas:
- Solo se completan celdas VACÍAS del Excel. Nunca se pisa un dato existente.
- Un partido del PDF se empareja con una fila de PARTIDOS por (año, quién es local, marcador).
  Si hay más de una fila posible, se descarta (no se adivina).
- Donde el Excel ya tenía dato, se compara con el del PDF para medir qué tan confiable es la fuente.

Uso:  python3 tools/enrich_hl.py <excel.xlsx> <carpeta_con_pdfs> <salida.json>
"""
import json
import re
import subprocess
import sys
import unicodedata
from collections import defaultdict
from pathlib import Path

import pandas as pd

TEAM = re.compile(r"^([A-ZÁÉÍÓÚÑ][A-ZÁÉÍÓÚÑ’'\.\(\) y]+?)\s{2,}(\d+)$")
REF = re.compile(r"ARBITRO:\s*(.+?)\.?\s*(?:\s{2,}|$)(?:RECAUDACION|ENTRADAS|CANCHA)?")
REF2 = re.compile(r"ARBITRO:\s*([^\n]*?)(?:\.\s|\.$|\s{2,}|$)")
ENT = re.compile(r"ENTRADAS:\s*([\d\.]+)")
DT = re.compile(r"DT\.?:\s*([A-ZÁÉÍÓÚÑ][^\n]*?)\.(?:\s|$)")


def norm(s):
    s = unicodedata.normalize("NFD", str(s)).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z0-9 ]", "", s).strip()


def page_count(pdf):
    out = subprocess.run(["pdfinfo", str(pdf)], capture_output=True, text=True).stdout
    return int(re.search(r"Pages:\s+(\d+)", out).group(1))


def stream(pdf):
    """Líneas en orden de lectura: columna izquierda y luego derecha de cada página."""
    lines = []
    for p in range(1, page_count(pdf) + 1):
        for x, w in ((0, 297), (297, 298)):
            t = subprocess.run(["pdftotext", "-f", str(p), "-l", str(p), "-x", str(x), "-y", "0", "-W", str(w), "-H", "842", "-layout", str(pdf), "-"],
                               capture_output=True, text=True).stdout
            lines += [(p, l.strip()) for l in t.splitlines() if l.strip()]
    return lines


def parse_pdf(pdf):
    s = stream(pdf)
    teams = [(k, p, m.group(1).strip(), int(m.group(2))) for k, (p, l) in enumerate(s)
             if (m := TEAM.match(l)) and not l.startswith("ARBITRO")]
    out, j = [], 0
    while j + 1 < len(teams):
        (k1, p1, a, na), (k2, _, b, nb) = teams[j], teams[j + 1]
        end = teams[j + 2][0] if j + 2 < len(teams) else len(s)
        lineup_a = " ".join(l for _, l in s[k1 + 1:k2])
        tail = s[k2 + 1:end]
        ref_i = next((i for i, (_, l) in enumerate(tail) if l.startswith("ARBITRO")), None)
        lineup_b = " ".join(l for _, l in tail[:ref_i]) if ref_i is not None else " ".join(l for _, l in tail[:6])
        ref = ent = None
        if ref_i is not None:
            line = tail[ref_i][1]
            m = REF2.search(line)
            ref = m.group(1).strip().rstrip(".") if m else None
            m = ENT.search(line)
            ent = int(m.group(1).replace(".", "")) if m else None
        dta, dtb = DT.search(lineup_a), DT.search(lineup_b)
        out.append(dict(page=p1, home=a, hs=na, away=b, aw=nb, ref=ref, ent=ent,
                        dt_home=dta.group(1).strip() if dta else None, dt_away=dtb.group(1).strip() if dtb else None))
        j += 2
    return out


def parse_cached(pdf, cache_dir):
    cf = Path(cache_dir) / f"{pdf.stem}.parsed.json"
    if cf.exists():
        return json.loads(cf.read_text(encoding="utf-8"))
    data = parse_pdf(pdf)
    cf.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return data


def main(xlsx, pdf_dir, out_json):
    p = pd.read_excel(xlsx, sheet_name="PARTIDOS")
    p = p[p["ID"].notna()].copy()
    p["ID"] = p["ID"].astype(int)
    # "0 (4)" = definición por penales
    for c in ("G.L", "G.V"):
        p[c] = pd.to_numeric(p[c].astype(str).str.extract(r"^(\d+)")[0], errors="coerce")
    p["Temporada"] = pd.to_numeric(p["Temporada"], errors="coerce")
    pri = p[p["División"] == "Primera División"]
    from collections import Counter
    import difflib
    recs, votes, pending = [], defaultdict(Counter), []
    n_pdf_matches = n_unmatched = n_amb = 0
    for pdf in sorted(Path(pdf_dir).glob("*.pdf")):
        year = int(pdf.stem)
        rows = pri[pri["Temporada"] == year]
        if rows.empty:
            continue
        games = [g for g in parse_cached(pdf, pdf_dir) if "CHACARITA" in g["home"].upper() or "CHACARITA" in g["away"].upper()]
        for g in games:
            n_pdf_matches += 1
            ch_home = "CHACARITA" in g["home"].upper()
            opp = g["away"] if ch_home else g["home"]
            cand = rows[(rows["Condición"] == ("Local" if ch_home else "Visitante")) & (rows["G.L"] == g["hs"]) & (rows["G.V"] == g["aw"])]
            if len(cand) == 0:
                n_unmatched += 1
                continue
            if len(cand) > 1:
                pending.append((year, g, ch_home, opp, cand, pdf))
                continue
            r = cand.iloc[0]
            votes[opp][r["Rival oficial"]] += 1
            recs.append((year, g, ch_home, opp, r, pdf))

    # 2.ª pasada: marcador repetido -> se desempata con el rival aprendido en la 1.ª pasada
    for year, g, ch_home, opp, cand, pdf in pending:
        if not votes[opp]:
            n_amb += 1
            continue
        top = votes[opp].most_common(1)[0][0]
        c2 = cand[cand["Rival oficial"] == top]
        if len(c2) == 1:
            recs.append((year, g, ch_home, opp, c2.iloc[0], pdf))
        else:
            n_amb += 1

    def rival_ok(opp, rival):
        top, n = votes[opp].most_common(1)[0]
        sim = difflib.SequenceMatcher(None, norm(opp), norm(rival)).ratio()
        return rival == top and (n >= 2 or sim >= 0.55)

    # confiabilidad por campo y año (solo con partidos cuyo rival coincide)
    fiab = defaultdict(lambda: dict(c=0, ok=0))
    comps = []
    for year, g, ch_home, opp, r, pdf in recs:
        if not rival_ok(opp, r["Rival oficial"]):
            continue
        dt = g["dt_home"] if ch_home else g["dt_away"]
        for campo, nuevo, col in (("Árbitro", g["ref"], "Árbitro"), ("Espectadores", g["ent"], "Espectadores"), ("DT", dt, "DT")):
            actual = r[col]
            if nuevo in (None, "") or pd.isna(actual) or str(actual).strip() == "":
                continue
            if campo == "Espectadores":
                ok = abs(float(actual) - float(nuevo)) <= 0.02 * float(nuevo)
            else:
                a_, b_ = norm(actual).split(), norm(nuevo).split()
                ok = bool(a_ and b_ and a_[-1] == b_[-1])
            for k in (("a", campo, year), ("d", campo, year // 10 * 10)):
                fiab[k]["c"] += 1
                fiab[k]["ok"] += int(ok)

    def gate(campo, year):
        """Se completa solo si, en ese año (o en su década), el dato del PDF ya coincidía >=90% con el Excel."""
        y = fiab.get(("a", campo, year))
        if y and y["c"] >= 5:
            return y["ok"] / y["c"] >= 0.9
        d = fiab.get(("d", campo, year // 10 * 10))
        return bool(d and d["c"] >= 10 and d["ok"] / d["c"] >= 0.9)

    patch, n_matched, n_fill_rej = [], 0, 0
    for year, g, ch_home, opp, r, pdf in recs:
        if not rival_ok(opp, r["Rival oficial"]):
            continue
        n_matched += 1
        src = f"Historical-Lineups {year}.pdf p.{g['page']}"
        dt = g["dt_home"] if ch_home else g["dt_away"]
        for campo, nuevo, col in (("Árbitro", g["ref"], "Árbitro"), ("Espectadores", g["ent"], "Espectadores"), ("DT", dt, "DT")):
            if nuevo in (None, ""):
                continue
            actual = r[col]
            if not (pd.isna(actual) or str(actual).strip() == ""):
                continue
            if not gate(campo, year):
                n_fill_rej += 1
                continue
            patch.append(dict(id=int(r["ID"]), fecha=str(r["Fecha"])[:10], partido=f"{r['Local']} {r['G.L']:.0f}-{r['G.V']:.0f} {r['Visitante']}",
                              campo=campo, valor=nuevo, fuente=src))
    stats = {}
    for campo in ("Árbitro", "Espectadores", "DT"):
        stats[campo] = dict(
            comparados=sum(v["c"] for (t, cm, y), v in fiab.items() if t == "a" and cm == campo),
            iguales=sum(v["ok"] for (t, cm, y), v in fiab.items() if t == "a" and cm == campo))
        stats[campo]["por_decada"] = {y: f"{v['ok']}/{v['c']}" for (t, cm, y), v in sorted(fiab.items()) if t == "d" and cm == campo}
    res = dict(patch=patch, stats={k: v for k, v in stats.items()},
               cobertura=dict(partidos_pdf=n_pdf_matches, emparejados_verificados=n_matched, ambiguos=n_amb, sin_pareja=n_unmatched, rechazados_por_confiabilidad=n_fill_rej))
    Path(out_json).write_text(json.dumps(res, ensure_ascii=False, indent=1), encoding="utf-8")
    print("cobertura:", res["cobertura"])
    for k, v in res["stats"].items():
        print(f"  {k}: comparados {v['comparados']}, coinciden {v['iguales']} ({100*v['iguales']/max(v['comparados'],1):.0f}%)  por década: {v['por_decada']}")
    por = defaultdict(int)
    for x in patch:
        por[x["campo"]] += 1
    print("celdas nuevas:", dict(por))


if __name__ == "__main__":
    main(*sys.argv[1:4])
