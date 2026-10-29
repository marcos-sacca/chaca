"""Orquesta todo: baja lo que falta (si se pide), lee las crónicas, cruza con otras fuentes, calcula tablas y arma CSV + Excel.

Uso:
  python3 -I bnacional/tools/run.py                 # reconstruye todo con lo que hay en el caché (bnacional/cache)
  python3 -I bnacional/tools/run.py --bajar         # además baja crónicas, RSSSF y Transfermarkt que falten (lento la primera vez)
  python3 -I bnacional/tools/run.py --actual        # vuelve a bajar solo la temporada en curso de Transfermarkt y reconstruye
"""
import json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CACHE = os.path.join(ROOT, "cache")
DATA = os.path.join(ROOT, "data")
PY = [sys.executable, "-I"]


def run(*args):
    print("»", " ".join(os.path.basename(a) if os.path.sep in a and i == 2 else a for i, a in enumerate(args)))
    subprocess.check_call(list(args))


def main():
    bajar, actual = "--bajar" in sys.argv, "--actual" in sys.argv
    blog, rs, tmc = os.path.join(CACHE, "blog"), os.path.join(CACHE, "rsssf"), os.path.join(CACHE, "tm_arg2")
    cat = os.path.join(CACHE, "catalog.json")
    tm_json = os.path.join(DATA, "fuentes", "tm_primera_nacional.json")
    os.makedirs(os.path.join(DATA, "fuentes"), exist_ok=True)
    if bajar:
        run(*PY, os.path.join(HERE, "jc_fetch.py"), "catalog", CACHE)
        import re
        posts = json.load(open(cat, encoding="utf-8"))
        urls = [p["u"] for p in posts if re.search(r'Nacional "B"|"B" Nacional|Nacional B', p["t"]) and "División AFA" not in p["t"]]
        for i in range(0, len(urls), 40):
            run(*PY, os.path.join(HERE, "jc_fetch.py"), "get", blog, *urls[i:i + 40])
        run(*PY, os.path.join(HERE, "rs_fetch.py"), rs)
    if bajar or actual:
        import datetime
        y = datetime.date.today().year
        run(*PY, os.path.join(HERE, "tm_league.py"), tmc, tm_json, str(2008 if bajar else y - 1), str(y))
    sa = os.path.join(os.path.dirname(ROOT), "ascenso", "data", "sintesis_solo_ascenso.jsonl.gz")
    run(*PY, os.path.join(HERE, "bn_build.py"), blog, cat, DATA, rs, tm_json, sa)
    run(*PY, os.path.join(HERE, "bn_export.py"), os.path.join(DATA, "_crudo.json"), DATA)
    run(*PY, os.path.join(HERE, "crosscheck.py"), os.path.join(DATA, "_crudo.json"), rs, tm_json, DATA, sa)
    run(*PY, os.path.join(HERE, "xlsx_make.py"), DATA, os.path.join(DATA, "B_Nacional_historico.xlsx"))


if __name__ == "__main__":
    main()
