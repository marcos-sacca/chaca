"""Compara lo que calcula el sitio (js/store.js sobre data/*.json) con los valores que ya tiene calculados la planilla.

Uso:  python3 -I tools/verify_vs_excel.py <DATACHACA.xlsx>
Lee los valores guardados de las hojas CHACADATA, DATOS CURIOSOS, RACHAS Y RÉCORDS, RANKING GOLEADORES, PARTIDOS JUGADOS y
EFEMÉRIDES (con los filtros tal como quedaron guardados en el archivo) y ejecuta tools/verify.mjs con Node.
"""
import json, subprocess, sys, tempfile, pathlib, datetime
import openpyxl

xlsx = sys.argv[1]
wb = openpyxl.load_workbook(xlsx, read_only=True, data_only=True)

def rows(name, r0, r1, c0=1, c1=12):
    return [list(r) for r in wb[name].iter_rows(min_row=r0, max_row=r1, min_col=c0, max_col=c1, values_only=True)]

def day(x):
    return x.strftime("%Y-%m-%d") if isinstance(x, (datetime.datetime, datetime.date)) else x

E = {}
dc = "DATOS CURIOSOS"
E["totales"] = {r[0]: r[1:7] for r in rows(dc, 8, 11, 2, 8)}
top = rows(dc, 17, 26, 2, 9)
E["rivales_por_div"] = {"Primera División": [(r[0], r[1]) for r in top], "Segunda División": [(r[3], r[4]) for r in top], "Tercera División": [(r[6], r[7]) for r in top]}
E["canchas"] = []
for r in rows(dc, 31, 400, 2, 7):
    if r[0] is None or r[1] is None: break
    E["canchas"].append(r)
E["anio"] = []
for r in rows(dc, 8, 140, 12, 20):
    if not isinstance(r[0], (int, float)): break
    E["anio"].append(r)
rr = "RACHAS Y RÉCORDS"
E["records_temp"] = rows(rr, 35, 43, 2, 6)
E["min_pj"] = rows(rr, 33, 33, 3, 3)[0][0]
E["filtro_rachas"] = {"div": rows(rr, 5, 5, 3, 3)[0][0], "rival": rows(rr, 5, 5, 6, 6)[0][0], "cond": rows(rr, 5, 5, 9, 9)[0][0], "desde": rows(rr, 6, 6, 3, 3)[0][0], "hasta": rows(rr, 6, 6, 6, 6)[0][0]}
E["rachas"] = [[r[0], r[1], day(r[2]), day(r[3]), r[4], r[5], r[6], r[7]] for r in rows(rr, 10, 17, 2, 9)]
E["rachas_cond"] = rows(rr, 22, 29, 2, 8)
E["campanas"] = []
for r in rows(rr, 10, 200, 12, 24):
    if r[0] is None: break
    E["campanas"].append(r)
cd = "CHACADATA"
E["chacadata"] = {"rival": rows(cd, 4, 4, 3, 3)[0][0], "tot": rows(cd, 7, 9, 2, 10), "div": rows(cd, 12, 15, 2, 10), "clave": rows(cd, 18, 22, 2, 4), "goleadores": rows(cd, 25, 29, 2, 3)}
rg = "RANKING GOLEADORES"
E["filtro_rank"] = {"div": rows(rg, 5, 5, 3, 3)[0][0], "dec": rows(rg, 5, 5, 6, 6)[0][0], "sd": rows(rg, 5, 5, 11, 11)[0][0]}
E["ranking"] = [r for r in rows(rg, 8, 40, 2, 9) if r[1]]
E["pj_ranking"] = [r for r in rows("PARTIDOS JUGADOS", 8, 30, 2, 7) if r[1]]
ef = "EFEMÉRIDES"
E["efem"] = {"dia": rows(ef, 5, 5, 3, 3)[0][0], "mes": rows(ef, 5, 5, 6, 6)[0][0], "res": rows(ef, 10, 10, 2, 6)[0], "lista": [r for r in rows(ef, 14, 80, 2, 6) if isinstance(r[0], (int, float))]}

tmp = pathlib.Path(tempfile.mkdtemp()) / "expected.json"
tmp.write_text(json.dumps(E, ensure_ascii=False, default=str))
sys.exit(subprocess.call(["node", str(pathlib.Path(__file__).with_name("verify.mjs")), str(tmp)]))
