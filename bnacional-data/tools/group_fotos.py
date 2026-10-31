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


# fotos revisadas a mano que NO son del club al que se las asignó la búsqueda: (slug, archivo, motivo)
EXCLUIR = [
    ("los-andes", "Plantel Meridiano V°.jpg", "Es el plantel de Meridiano V (La Plata), no de Los Andes"),
    ("olimpo-de-bahia-blanca", "Plantel Meridiano V°.jpg", "Es el plantel de Meridiano V (La Plata), no de Olimpo"),
    ("platense", "Gimnasia-mussis-niell-2013.JPG", "Gol de Gimnasia La Plata; «platense» en el texto es gentilicio de La Plata"),
]
EXCL = {(c, f) for c, f, _ in EXCLUIR}
# palabras que no identifican a un club por sí solas
GEN = {"club", "atletico", "deportivo", "sportivo", "social", "union", "ciudad", "san", "santa", "villa", "central", "juventud", "sporting", "general", "comision", "actividades", "infantiles"}
STOPW = {"de", "del", "la", "las", "los", "el", "y", "e", "fc", "ac", "cd", "ca"}
PJ = {}
try:
    for r in json.load(open(os.path.join(ROOT, "data/general.json"), encoding="utf-8")):
        PJ[r[1]] = r[3]
except Exception:
    pass
words = lambda t: set(__import__("re").findall(r"[a-z]+", norm(t)))


def ident(name):
    """palabras que distinguen al club, con el lugar incluido («gimnasia esgrima plata», «gimnasia esgrima jujuy»)"""
    w = [x for x in __import__("re").findall(r"[a-z]+", norm(name)) if x not in STOPW and len(x) > 2]
    core = [x for x in w if x not in GEN]
    return set(core or w)


def clubs_in(text):
    """clubes nombrados en el texto de una foto. Entre clubes que comparten palabras (los cuatro Gimnasia y Esgrima,
    los Almirante Brown, los Belgrano) queda el que coincide más completo; un club se acepta si coincide entero
    o si gana su grupo. Desempata el que más partidos jugó en la categoría."""
    W = words(text)
    cand = []
    for i, t in enumerate(T):
        idt = ident(t["n"])
        m = idt & W
        if m:
            cand.append((i, t, idt, m, len(m) / len(idt)))
    out = []
    for i, t, idt, m, fr in cand:
        rivals = [c for c in cand if c[0] != i and c[3] & m]
        best = max([fr] + [c[4] for c in rivals])
        win = fr == best and all(not (c[4] == fr and PJ.get(c[0], 0) > PJ.get(i, 0)) for c in rivals)
        if fr == 1 or (win and fr >= .5):
            out.append(t["s"])
    return out


for k, ph in d["entries"].items():
    if (k.split("|")[1], ph["file"]) not in EXCL:
        add(k.split("|")[1], ph)
for slug, ph in d["clubs"].items():
    if (slug, ph["file"]) not in EXCL:
        add(slug, ph)
general = []
for ph in d["general"]:
    hit = False
    for s in clubs_in(ph["file"] + " " + ph["caption"]):
        if (s, ph["file"]) not in EXCL:
            add(s, ph); hit = True
    if not hit:
        general.append(ph)
rank = {"temporada": 0, "general": 1, "club": 2}
for L in clubs.values():
    L.sort(key=lambda p: rank.get(p.get("kind"), 3))
json.dump(dict(clubs=clubs, general=general), open(os.path.join(ROOT, "data/galeria.json"), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print(len(clubs), "clubes con fotos;", len(general), "sin club;", sum(len(v) for v in clubs.values()), "fotos")
