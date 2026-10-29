"""Baja el escudo de cada club: busca el artículo en Wikipedia (es), toma la imagen principal (og:image), la baja achicada y guarda de dónde sale.

  python3 -I fetch_crests.py <data/teams.json> <carpeta_img> <salida.json>
Los escudos son marcas de sus clubes; se muestran solo para identificarlos. Un pedido cada 2 s; se puede cortar y retomar.
"""
import io, json, os, re, sys, time, urllib.parse, urllib.request
from PIL import Image

UA = "bnacional-data/1.0 (https://github.com/marcos-sacca/chaca; estadistica historica del ascenso argentino)"
STOP = {"club", "atletico", "deportivo", "de", "del", "la", "los", "y", "social", "sportivo", "asociacion", "juniors", "fc"}


def norm(t):
    import unicodedata
    return re.sub(r"[^a-z ]", " ", unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower())


def http(url, binary=False, tries=6):
    for k in range(tries):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60)
            return r.geturl(), (r.read() if binary else r.read().decode("utf-8", "ignore"))
        except Exception as e:
            if "404" in str(e) or "400" in str(e):
                return None, None
            time.sleep(6 * (k + 1) if "429" in str(e) else 4)
    return None, None


OVERRIDE = {"Deportivo Italiano": ["Club Deportivo Italiano"], "Estación Quequén": ["Club Social y Deportivo Estación Quequén"], "Racing de Nueva Italia": ["Club Atlético Racing (Nueva Italia)", "Racing Club (Nueva Italia)"], "Sacachispas": ["Sacachispas Fútbol Club"], "Tiro Federal de Rosario": ["Club Atlético Tiro Federal Argentino"], "Almirante Brown": ["Club Almirante Brown"], "Aldosivi de Mar del Plata": ["Club Atlético Aldosivi"], "Agropecuario Argentino de Carlos Casares": ["Club Atlético Agropecuario Argentino", "Agropecuario Argentino"]}


def candidates(name, short):
    if name in OVERRIDE:
        return OVERRIDE[name]
    base = re.sub(r"\s*\(.*?\)", "", name)
    out = [name, f"Club Atlético {name}", f"Club Deportivo {name}", f"Club {name}", f"Club Sportivo {name}", f"Asociación Atlética {name}", short, f"Club Atlético {short}", f"Club Deportivo {short}", f"{short} (Argentina)", f"{base} (fútbol)"]
    return list(dict.fromkeys(out))


def raw_article(title):
    for _ in range(3):  # sigue hasta 2 redirecciones
        _, t = http("https://es.wikipedia.org/w/index.php?title=" + urllib.parse.quote(title.replace(" ", "_")) + "&action=raw")
        time.sleep(0.8)
        if not t:
            return None, None
        m = re.match(r"\s*#(?:REDIRECCI[OÓ]N|REDIRECT)\s*\[\[([^\]|#]+)", t, re.I)
        if not m:
            return title, t
        title = m.group(1).strip()
    return None, None


def find(name, short):
    toks = [w for w in norm(name).split() if w not in STOP and len(w) > 2] or norm(name).split()
    for q in candidates(name, short):
        title, t = raw_article(q)
        if not t or not re.search(r"\{\{\s*Ficha de (?:equipo|club)", t, re.I):
            continue
        if not any(tk in norm(title + " " + t[:600]) for tk in toks[:2]):
            continue
        m = re.search(r"\|\s*(?:escudo|logo|imagen principal|imagen)\s*=\s*(?:\[\[(?:Archivo|File|Imagen):)?([^|\]\n}]+\.(?:svg|png|jpe?g|gif))", t, re.I)
        if m:
            return title, m.group(1).strip().replace("_", " ")
        # el escudo del cuadro viene de Wikidata (P154, logotipo)
        _, html = http("https://es.wikipedia.org/w/index.php?title=" + urllib.parse.quote(title.replace(" ", "_")))
        time.sleep(0.8)
        q_id = re.search(r'"wgWikibaseItemId":"(Q\d+)"', html or "")
        if q_id:
            _, js = http(f"https://www.wikidata.org/wiki/Special:EntityData/{q_id.group(1)}.json")
            time.sleep(0.8)
            try:
                e = list(json.loads(js)["entities"].values())[0]["claims"].get("P154", [])
                best = [c for c in e if c.get("rank") != "deprecated"]
                pref = [c for c in best if c.get("rank") == "preferred"] or best
                if pref:
                    return title, pref[-1]["mainsnak"]["datavalue"]["value"]
            except Exception:
                pass
    return None, None


def main(teams, imgdir, out):
    os.makedirs(imgdir, exist_ok=True)
    T = json.load(open(teams, encoding="utf-8"))
    res = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else {}
    for t in T:
        if t["s"] in res and (res[t["s"]] is None or os.path.exists(os.path.join(imgdir, t["s"] + ".png"))):
            continue
        title, fname = find(t["n"], t["short"])
        if not fname:
            res[t["s"]] = None; print("SIN ESCUDO", t["n"], flush=True); json.dump(res, open(out, "w"), ensure_ascii=False); continue
        import hashlib
        n_ = fname.replace(" ", "_"); h_ = hashlib.md5(n_.encode()).hexdigest(); q_ = urllib.parse.quote(n_)
        ok = src = None
        for kind in ("commons", "es"):
            for w in (250, 330, 160):
                ext = ".png" if n_.lower().endswith((".svg", ".gif", ".tif")) else ""
                u = f"https://upload.wikimedia.org/wikipedia/{kind}/thumb/{h_[0]}/{h_[:2]}/{q_}/{w}px-{q_}{ext}"
                _, data = http(u, binary=True, tries=4)
                time.sleep(0.8)
                if data:
                    try:
                        im = Image.open(io.BytesIO(data)).convert("RGBA"); im.thumbnail((220, 220))
                        im.save(os.path.join(imgdir, t["s"] + ".png"), optimize=True); ok = im.size; src = kind; break
                    except Exception:
                        pass
            if ok:
                break
        if not ok:
            res[t["s"]] = None; print("NO BAJÓ", t["n"], fname, flush=True)
        else:
            res[t["s"]] = dict(img=f"assets/img/crests/{t['s']}.png", article=title, file=fname, source=("commons" if src == "commons" else "es.wikipedia"),
                               page=("https://commons.wikimedia.org/wiki/File:" if src == "commons" else "https://es.wikipedia.org/wiki/Archivo:") + urllib.parse.quote(n_))
            print("ok", t["n"], "|", title, "|", fname, flush=True)
        json.dump(res, open(out, "w"), ensure_ascii=False)


if __name__ == "__main__":
    main(*sys.argv[1:4])
