"""Elige una foto libre por club ascendido (y por temporada cuando el nombre del archivo trae el año), baja una copia achicada y arma data/fotos.json.

  python3 -I pick_photos.py <club_files.json> <ascensos.csv> <carpeta_cache> <carpeta_salida_img> <fotos.json>
Solo acepta archivos con licencia libre declarada en la página de Commons (CC BY, CC BY-SA, CC0, dominio público). Si no hay licencia clara, descarta el archivo.
"""
import csv, io, json, os, re, sys, urllib.parse, urllib.request
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_photos2 import get, BAD, GOOD, UA, cat_files  # noqa: E402
from PIL import Image  # noqa: E402

FREE = re.compile(r"\{\{\s*(?:self\|)?(?:cc-by[^}]*|cc-zero|cc0|pd[-\w ]*|public domain[^}]*|cc-pd[^}]*|anonymous-EU|PD-[^}]*)\}\}|creative commons|public domain|dominio p[uú]blico", re.I)
NONFREE = re.compile(r"non-free|fair use|copyrighted|\{\{\s*no permission|\{\{\s*speedy|\{\{\s*copyvio|nc-by|cc-by-nc|-nd", re.I)
EXT = re.compile(r"\.(jpe?g|png)$", re.I)


def licence(rawtxt):
    if NONFREE.search(rawtxt) or not FREE.search(rawtxt):
        return None
    m = re.search(r"\{\{\s*(?:self\|)?(cc-[\w.\-]+|pd[-\w ]*|cc0)", rawtxt, re.I)
    name = m.group(1) if m else "Licencia libre"
    nice = re.sub(r"^cc-by-sa-([\d.]+).*", r"CC BY-SA \1", name, flags=re.I)
    nice = re.sub(r"^cc-by-([\d.]+).*", r"CC BY \1", nice, flags=re.I)
    if re.match(r"(?i)pd|cc0|cc-zero", name):
        nice = "Dominio público" if not re.match(r"(?i)cc0|cc-zero", name) else "CC0"
    return nice


def field(rawtxt, key):
    m = re.search(r"\|\s*" + key + r"\s*=\s*(.+?)(?=\n\s*\||\n\}\}|\Z)", rawtxt, re.S | re.I)
    if not m:
        return ""
    t = re.sub(r"\{\{[a-z]{2}\|(?:1=)?([^}]*)\}\}", r"\1", m.group(1), flags=re.I)
    t = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]*)\]\]", r"\1", t)
    t = re.sub(r"\{\{[^}]*\}\}|<[^>]+>|'''?", "", t)
    return re.sub(r"\s+", " ", t).strip()


def years_of(label):
    ys = [int(y) for y in re.findall(r"\d{4}", label)]
    if "/" in label and ys:
        ys.append(ys[0] + 1)
    return set(ys)


def score(name, years=None):
    sc = 0
    if GOOD.search(name):
        sc += 2
    if re.search(r"equipo|plantel|team|squad|campe|champion|ascenso|celebr|festej", name, re.I):
        sc += 2
    if years and any(str(y) in name for y in years):
        sc += 5
    if re.search(r"^\d+px|IMG_|DSC|P\d{6,}", name):
        sc -= 1
    return sc


def describe(name, cache):
    t = get("https://commons.wikimedia.org/w/index.php?title=" + urllib.parse.quote("File:" + name.replace(" ", "_")) + "&action=raw", cache)
    lic = licence(t)
    if not lic:
        return None
    return dict(lic=lic, author=field(t, "author")[:100], desc=field(t, "description")[:200], date=field(t, "date")[:30])


def download(name, dest):
    import hashlib, time
    n = name.replace(" ", "_"); h = hashlib.md5(n.encode()).hexdigest(); q = urllib.parse.quote(n)
    urls = [f"https://upload.wikimedia.org/wikipedia/commons/thumb/{h[0]}/{h[:2]}/{q}/{w}px-{q}" for w in (960, 500)] + [f"https://upload.wikimedia.org/wikipedia/commons/{h[0]}/{h[:2]}/{q}"]
    for k in range(14):
        url = urls[0 if k < 6 else 1 if k < 11 else 2]
        try:
            data = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=90).read()
            im = Image.open(io.BytesIO(data)).convert("RGB")
            im.thumbnail((760, 760))
            im.save(dest, "JPEG", quality=66, optimize=True, progressive=True)
            return im.size
        except Exception as e:
            time.sleep(4 if "429" in str(e) else 3)
    return None


GENERAL_CATS = ["Primera Nacional matches", "Matches of River Plate in Primera B Nacional", "Banfield v Belgrano, 13 June 1987", "Gimnasia y Esgrima LP v Sarmiento de Junín, 15 June 2013",
                "Unión de Santa Fe v Independiente Rivadavia, 19 February 2010", "2012-13 Primera B Nacional Championship", "Primera Nacional"]
GENERIC = {"club", "atletico", "deportivo", "sportivo", "asociacion", "social", "juniors", "de", "del", "la", "los", "y", "fc", "mar", "plata"}


AMBIG = {"rosario", "central", "san", "nueva", "godoy", "tiro", "all", "gimnasia", "union", "huracan", "talleres", "estudiantes", "argentinos", "independiente", "sarmiento", "olimpo"}


def keyword_tokens(club):
    """Palabras que identifican al club en el nombre de un archivo (dos si la primera es ambigua, como «Rosario» o «San»)."""
    import unicodedata
    t = unicodedata.normalize("NFD", club).encode("ascii", "ignore").decode().lower()
    toks = [w for w in re.findall(r"[a-z]+", t) if w not in GENERIC and len(w) > 2]
    toks = [w for i, w in enumerate(toks) if w not in toks[:i] or w == "san" and toks[:i].count("san") == 0]
    if toks and toks[0] == "san":
        toks = ["san"] + [w for w in toks[1:] if w != "san"]
    return toks[:3] if toks and toks[0] == "san" else toks[:2] if toks and toks[0] in AMBIG else toks[:1]


FOOT = re.compile(r"f[uú]tbol|football|soccer|partido|match|equipo|team|squad|plantel|hinchada|hincha|fans|supporters|barra|estadio|stadium|ascenso|promot|campe|champion|cancha|torcida|festej|celebr|gol\b|goal|copa|torneo|primera|nacional", re.I)
NOFOOT = re.compile(r"rugby|tennis|tenis|portrait|retrato|entrevista|interview|speaking|posing|hotel|world cup|mundial|fifa|olymp|hockey|basket|b[aá]squet|medical|school|escuela|graffiti|mural en homenaje a los|selecci[oó]n|argentina vs|vs germany", re.I)


def relevant(f, d, kw, in_cat):
    """El archivo trata de fútbol y del club: está en su categoría de Commons, o su nombre/descripción lo nombran."""
    txt = norm_txt(f + " " + d["desc"])
    if NOFOOT.search(f + " " + d["desc"]) or not FOOT.search(f + " " + d["desc"]):
        return False
    return in_cat or all(k in txt for k in kw)


def norm_txt(t):
    import unicodedata
    return unicodedata.normalize("NFD", t).encode("ascii", "ignore").decode().lower().replace("_", " ")


def main(cf, csvp, cache, imgdir, out):
    os.makedirs(imgdir, exist_ok=True)
    cf = json.load(open(cf, encoding="utf-8"))
    rows = list(csv.DictReader(open(csvp, encoding="utf-8-sig")))
    entries, clubs, used = {}, {}, {}
    slug = lambda s: re.sub(r"[^a-z0-9]+", "-", __import__("unicodedata").normalize("NFD", s).encode("ascii", "ignore").decode().lower()).strip("-")

    def take(club, name, d, kind, key_hint):
        fn = f"{slug(club)}-{key_hint}.jpg"
        dest = os.path.join(imgdir, fn)
        if name in used:
            return used[name]
        title = re.sub(r"\.(jpe?g|png)$", "", name, flags=re.I)
        cap = d["desc"] or title
        ph = dict(img=f"assets/img/ascensos/{fn}", caption=cap[:180], alt=title, author=re.sub(r"\s+", " ", d["author"]), lic=d["lic"], page="https://commons.wikimedia.org/wiki/File:" + urllib.parse.quote(name.replace(" ", "_")), kind=kind, file=name)
        used[name] = ph
        ph["_dest"] = dest
        return ph

    general = []
    for gc in GENERAL_CATS:
        fs, _ = cat_files(gc, cache)
        general += [f for f in fs if EXT.search(f) and not BAD.search(f)]
    general = list(dict.fromkeys(general))
    norm_ = lambda f: __import__("unicodedata").normalize("NFD", f).encode("ascii", "ignore").decode().lower().replace("_", " ")
    for club, c in sorted(cf.items()):
        kw = keyword_tokens(club)
        gen_for_club = [f for f in general if kw and all(k in norm_(f) for k in kw)]
        pool = gen_for_club + list(dict.fromkeys([f for f in c["articulo"] if EXT.search(f)] + [f for f in c["archivos"] if EXT.search(f)] + [f for sc, fs in c["subcategorias"].items() if not re.search(r"player|coach|manager|jugador", sc, re.I) for f in fs if EXT.search(f)]))
        pool = [f for f in pool if not BAD.search(f)]
        cat_set = set(c["archivos"]) | {f for sc, fs in c["subcategorias"].items() if not re.search(r"player|coach|manager|jugador", sc, re.I) for f in fs} | set(gen_for_club)
        # fotos de cada temporada de ascenso (el año figura en el nombre del archivo)
        for r in rows:
            if r["Club"] != club:
                continue
            ys = years_of(r["Temporada"])
            cand = sorted([f for f in pool if any(str(y) in f for y in ys)], key=lambda f: -score(f, ys))[:4]
            for f in cand:
                d = describe(f, cache)
                if d and relevant(f, d, kw, f in cat_set):
                    key = f"{slug(r['Temporada'])}"
                    ph = take(club, f, d, "temporada", key)
                    if ph:
                        entries[f"{slug(r['Temporada'].replace('/', '-'))}|{slug(club)}"] = ph
                        break
        # foto general del club
        for f in sorted(pool, key=lambda f: -score(f))[:8]:
            d = describe(f, cache)
            if d and relevant(f, d, kw, f in cat_set):
                ph = take(club, f, d, "club", "club")
                if ph:
                    clubs[slug(club)] = dict(ph, kind="club")
                    break
        print(club, "temporadas:", sum(1 for k in entries if k.endswith("|" + slug(club))), "club:", slug(club) in clubs, flush=True)
    gen_out = []
    for f in general:
        if len(gen_out) >= 16:
            break
        if f in used:
            gen_out.append(used[f]); continue
        d = describe(f, cache)
        if d and not NOFOOT.search(f + " " + d["desc"]) and len(d["desc"] or f) > 14 and all((d["desc"] or f)[:40] != (g["caption"] or "")[:40] for g in gen_out):
            ph = take("categoria", f, d, "general", slug(re.sub(r"\.\w+$", "", f))[:40])
            if ph:
                gen_out.append(ph)
    # descargas (al final, con reintentos: Wikimedia limita los pedidos de imágenes)
    todo = [ph for ph in used.values() if not os.path.exists(ph["_dest"])]
    print("para descargar:", len(todo), flush=True)
    failed = set()
    for ph in todo:
        if not download(ph["file"], ph["_dest"]):
            failed.add(ph["file"]); print("no se pudo bajar", ph["file"], flush=True)
        else:
            print("ok", ph["file"], flush=True)
    entries = {k: v for k, v in entries.items() if v["file"] not in failed}
    clubs = {k: v for k, v in clubs.items() if v["file"] not in failed}
    gen_out = [g for g in gen_out if g["file"] not in failed]
    clean = lambda d: {k: {kk: vv for kk, vv in v.items() if not kk.startswith("_")} for k, v in d.items()}
    json.dump(dict(entries=clean(entries), clubs=clean(clubs), general=[{kk: vv for kk, vv in g.items() if not kk.startswith("_")} for g in gen_out]), open(out, "w", encoding="utf-8"), ensure_ascii=False, indent=0)


if __name__ == "__main__":
    main(*sys.argv[1:6])
