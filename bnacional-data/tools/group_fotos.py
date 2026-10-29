"""Agrupa las fotos de data/fotos.json por club (data/galeria.json): las de la temporada, la del club y las de partidos donde el club figura por nombre.
  python3 -I tools/group_fotos.py
"""
import json, os, sys, unicodedata
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
import pick_photos as pp  # noqa: E402

d = json.load(open(os.path.join(ROOT, "data/fotos.json"), encoding="utf-8")); T = json.load(open(os.path.join(ROOT, "data/teams.json"), encoding="utf-8"))
norm = lambda t: unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower().replace("_", " ")
clubs = {}


def add(slug, ph):
    L = clubs.setdefault(slug, [])
    if all(x["file"] != ph["file"] for x in L):
        L.append(ph)


for k, ph in d["entries"].items():
    add(k.split("|")[1], ph)
for slug, ph in d["clubs"].items():
    add(slug, ph)
general = []
for ph in d["general"]:
    hit = False
    for t in T:
        kw = pp.keyword_tokens(t["n"])
        if kw and all(w in norm(ph["file"] + " " + ph["caption"]) for w in kw):
            add(t["s"], ph); hit = True
    if not hit:
        general.append(ph)
rank = {"temporada": 0, "general": 1, "club": 2}
for L in clubs.values():
    L.sort(key=lambda p: rank.get(p.get("kind"), 3))
json.dump(dict(clubs=clubs, general=general), open(os.path.join(ROOT, "data/galeria.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(clubs), "clubes con fotos;", len(general), "sin club;", sum(len(v) for v in clubs.values()), "fotos")
