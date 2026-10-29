"""Busca fotos libres de cada club que ascendió en Wikimedia Commons sin usar la API (que limita los pedidos):
artículo de Wikipedia -> categoría de Commons -> archivos y subcategorías -> descripción de cada archivo (licencia, autor, fecha).

  python3 -I fetch_photos2.py <ascensos.csv> <wikipedia_primera_b_nacional.wiki> <carpeta_cache> <salida.json>
Un pedido cada 1,5 s; todo se guarda en la carpeta de caché, así se puede cortar y retomar.
"""
import csv, hashlib, json, os, re, sys, time, urllib.parse, urllib.request

UA = "bnacional-data/1.0 (https://github.com/marcos-sacca/chaca; estadistica historica del ascenso argentino)"
BAD = re.compile(r"logo|escudo|crest|badge|kit|camiseta|flag|bandera|mapa|map\b|retrato|portrait|firma|signature|signature|svg|stadium_map|plano|diagrama|ticket|entrada|trofeo|trophy|copa|banner|poster|cartel", re.I)
GOOD = re.compile(r"equipo|plantel|team|squad|campe|ascenso|champion|celebr|festej|hinchada|fans|supporters|barra|torcida|estadio|stadium|cancha|vs|partido|match|final", re.I)


def get(url, cache, tries=6):
    f = os.path.join(cache, hashlib.md5(url.encode()).hexdigest() + ".txt")
    if os.path.exists(f):
        return open(f, encoding="utf-8").read()
    for k in range(tries):
        try:
            t = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read().decode("utf-8", "ignore")
            open(f, "w", encoding="utf-8").write(t)
            time.sleep(2.0)
            return t
        except Exception as e:
            if "404" in str(e):
                open(f, "w", encoding="utf-8").write("")
                return ""
            time.sleep(10 * (k + 1) if "429" in str(e) else 6)
    return ""


def raw(host, title, cache):
    return get(f"https://{host}/w/index.php?title={urllib.parse.quote(title.replace(' ', '_'))}&action=raw", cache)


def cat_files(cat, cache):
    h = get("https://commons.wikimedia.org/wiki/Category:" + urllib.parse.quote(cat.replace(" ", "_")), cache)
    files = [urllib.parse.unquote(x).replace("_", " ") for x in dict.fromkeys(re.findall(r'href="/wiki/File:([^"#]+)"', h))]
    subs = [urllib.parse.unquote(x).replace("_", " ") for x in dict.fromkeys(re.findall(r'href="/wiki/Category:([^"#]+)"', h))]
    return files, subs


def main(csv_path, wiki_path, cache, out):
    os.makedirs(cache, exist_ok=True)
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    wiki = open(wiki_path, encoding="utf-8").read()
    target = {}
    for m in re.finditer(r"\[\[([^\]|]+)\|([^\]]+)\]\]", wiki):
        target.setdefault(m.group(2).strip(), m.group(1).strip())
    clubs = {}
    for r in rows:
        clubs.setdefault(r["Club"], r["Nombre en la fuente"])
    res = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else {}
    for club, lab in sorted(clubs.items()):
        if club in res:
            continue
        title = target.get(lab) or target.get(club) or club
        art = raw("es.wikipedia.org", title, cache)
        mcat = re.search(r"\{\{\s*commonscat\s*(?:\|\s*([^}|]+))?", art, re.I)
        cats = []
        if mcat and mcat.group(1):
            cats.append(mcat.group(1).strip())
        cats += [title, club]
        files, subs, used = [], [], None
        for c in cats:
            f, s = cat_files(c, cache)
            if f or s:
                files, subs, used = f, s, c
                break
        # subcategorías útiles (partidos, equipos, estadio, hinchada)
        pick = [s for s in subs if re.search(r"match|team|squad|stadium|estadio|fans|supporters|champion|celebr|history|players of", s, re.I) and not re.search(r"logo|kit|coach|mascot", s, re.I)][:5]
        sub_files = {}
        for s in pick:
            f2, _ = cat_files(s, cache)
            sub_files[s] = f2[:60]
        # imágenes del artículo
        art_files = [x.strip().replace("_", " ") for x in re.findall(r"\[\[(?:Archivo|File|Imagen):([^|\]]+)", art)] + [x.strip() for x in re.findall(r"\|\s*(?:imagen|escudo|image)\s*=\s*([^|\n}]+\.(?:jpe?g|png))", art, re.I)]
        res[club] = dict(title=title, categoria=used, archivos=files[:200], subcategorias=sub_files, articulo=list(dict.fromkeys(art_files)))
        json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False)
        print(club, "|", used, len(files), {k: len(v) for k, v in sub_files.items()}, len(art_files), flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:5])
