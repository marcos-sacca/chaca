"""Une los escudos de TheSportsDB y de Wikipedia en data/crests.json (uno por club) y borra las imágenes sobrantes.
  python3 -I merge_crests.py <teams.json> <crests_wikipedia.json> <crests_tsdb.json> <carpeta_img> <salida.json>
Prefiere TheSportsDB (PNG uniformes) salvo los clubes de EXCLUIR_TSDB / EXCLUIR_WIKI, que son homónimos de otro club."""
import json, os, sys

EXCLUIR_WIKI = {"deportivo-italiano"}  # el artículo resuelve al club uruguayo homónimo
EXCLUIR_TSDB = set()


def main(teams, wiki, tsdb, imgdir, out):
    T = json.load(open(teams, encoding="utf-8")); W = json.load(open(wiki, encoding="utf-8")); D = json.load(open(tsdb, encoding="utf-8"))
    res, keep, faltan = {}, set(), []
    for t in T:
        s = t["s"]
        c = D.get(s) if s not in EXCLUIR_TSDB else None
        if not c and s not in EXCLUIR_WIKI:
            c = W.get(s)
        if c and os.path.exists(os.path.join(imgdir, os.path.basename(c["img"]))):
            res[s] = c; keep.add(os.path.basename(c["img"]))
        else:
            faltan.append(t["n"])
    for f in os.listdir(imgdir):
        if f.endswith(".png") and f not in keep:
            os.remove(os.path.join(imgdir, f))
    json.dump(res, open(out, "w"), ensure_ascii=False, indent=1)
    print(len(res), "escudos;", len(faltan), "sin escudo:", faltan)


if __name__ == "__main__":
    main(*sys.argv[1:6])
