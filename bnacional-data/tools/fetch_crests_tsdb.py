"""Escudos desde TheSportsDB (API gratuita, clave de prueba 123): busca cada club por nombre, se queda con equipos de Argentina
cuyo nombre coincide, baja el escudo achicado. Guarda aparte (<salida>.json) para no pisar la pasada de Wikipedia.
  python3 -I fetch_crests_tsdb.py <data/teams.json> <carpeta_img> <salida.json>
Los escudos son marcas de sus clubes; se muestran solo para identificarlos."""
import io, json, os, re, sys, time, unicodedata, urllib.parse, urllib.request
from PIL import Image

UA = "bnacional-data/1.0 (estadistica historica del ascenso argentino)"
STOP = {"club", "atletico", "deportivo", "de", "del", "la", "los", "las", "y", "social", "sportivo", "asociacion", "fc", "cultural", "cd", "ca", "sc"}


def norm(t):
    return re.sub(r"[^a-z ]", " ", unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower())


def toks(t):
    return {w for w in norm(t).split() if w not in STOP and len(w) > 1}


def get(url, binary=False, tries=4):
    for k in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=40)
            return r.read() if binary else r.read().decode("utf-8", "ignore")
        except Exception as e:
            if "404" in str(e):
                return None
            time.sleep(3 * (k + 1))
    return None


def search(q):
    t = get("https://www.thesportsdb.com/api/v1/json/123/searchteams.php?t=" + urllib.parse.quote(q))
    time.sleep(1.2)
    try:
        return [x for x in (json.loads(t).get("teams") or []) if x.get("strCountry") == "Argentina" and x.get("strBadge")]
    except Exception:
        return []


ALIAS = {"Arsenal FC": ["Arsenal de Sarandí", "Arsenal Sarandí"], "Tiro Federal de Rosario": ["Tiro Federal"], "Güemes de Santiago del Estero": ["Güemes", "Gimnasia y Tiro", "Güemes Santiago"],
         "Deportivo Mandiyú de Corrientes": ["Mandiyú"], "Unión de Mar del Plata": ["Unión Mar del Plata"], "Unión de Villa Krause": ["Unión Villa Krause"],
         "Atlético Concepción de Tucumán": ["Atlético Concepción", "Concepción"], "Deportivo Italiano": ["Italiano"], "Guaraní Antonio Franco de Posadas": ["Guaraní Antonio Franco", "Guaraní A. Franco"],
         "Huracán Corrientes": ["Huracán de Corrientes", "Huracán Ctes"], "Atlético Paraná": ["Atlético de Paraná"], "Deportivo Laferrere": ["Laferrere"], "General Paz Juniors": ["Gral. Paz Juniors", "General Paz Jrs"],
         "Estación Quequén": ["Quequén"], "Sacachispas": ["Sacachispas FC"], "Chaco For Ever": ["Chaco Forever", "Chaco For-Ever"]}
NOCITY = {"Comisión de Actividades Infantiles"}


# pares (club nuestro, id TheSportsDB) que comparten nombre genérico pero son otro club
BLOCK = {("Almirante Brown de Arrecifes", "141011"), ("Racing de Nueva Italia", "135170"), ("Huracán de Tres Arroyos", "135163"), ("Juventud Unida de Gualeguaychú", "150169")}


def best(name, short, cands):
    want = toks(name) or toks(short)
    sw = toks(short)
    sc = []
    for c in cands:
        if (name, c.get("idTeam")) in BLOCK:
            continue
        got = toks(c["strTeam"]) | toks(c.get("strTeamAlternate") or "")
        if got and (got <= want or want <= got or got & sw == sw):
            sc.append((len(got & want) - 0.1 * len(got ^ want), c))
    return max(sc, key=lambda x: x[0])[1] if sc else None


def main(teams, imgdir, out):
    os.makedirs(imgdir, exist_ok=True)
    T = json.load(open(teams, encoding="utf-8")); res = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else {}
    for t in T:
        if res.get(t["s"]) and os.path.exists(os.path.join(imgdir, "tsdb_" + t["s"] + ".png")) and "--redo" not in sys.argv:
            continue
        c = None
        for q in dict.fromkeys([t["short"], t["n"], re.sub(r"\s+de\s+.*$", "", t["n"])] + ALIAS.get(t["n"], [])):
            c = best(t["n"], t["short"], search(q))
            if c:
                break
        if not c:
            res[t["s"]] = None; print("SIN", t["n"], flush=True); continue
        data = get(c["strBadge"], binary=True)
        time.sleep(1)
        try:
            im = Image.open(io.BytesIO(data)).convert("RGBA"); im.thumbnail((220, 220))
            im.save(os.path.join(imgdir, "tsdb_" + t["s"] + ".png"), optimize=True)
            res[t["s"]] = dict(img=f"assets/img/crests/tsdb_{t['s']}.png", article=c["strTeam"], file=c["strBadge"].rsplit("/", 1)[-1], source="TheSportsDB", page="https://www.thesportsdb.com/team/" + c["idTeam"])
            print("ok", t["n"], "|", c["strTeam"], flush=True)
        except Exception as e:
            res[t["s"]] = None; print("NO BAJÓ", t["n"], flush=True)
        json.dump(res, open(out, "w"), ensure_ascii=False)
    json.dump(res, open(out, "w"), ensure_ascii=False)


if __name__ == "__main__":
    main(*[a for a in sys.argv[1:] if not a.startswith('--')][:3])
