"""Busca fotos libres en Wikimedia Commons para cada club que ascendió (por temporada y por club) y las categorías generales.

  python3 -I fetch_photos.py <ascensos.csv> <cache.json>
Guarda en cache.json los candidatos de cada consulta (título, miniatura, licencia, autor, descripción, fecha). Respeta el límite de pedidos de Wikimedia:
un pedido cada 6 s y espera cuando responde 429. Se puede cortar y retomar.
"""
import csv, json, os, re, sys, time, urllib.parse, urllib.request

UA = "bnacional-data/1.0 (https://github.com/marcos-sacca/chaca; estadistica historica del ascenso argentino)"
API = "https://commons.wikimedia.org/w/api.php"


def query(q, limit=20):
    p = dict(action="query", generator="search", gsrsearch=q, gsrnamespace="6", gsrlimit=str(limit), prop="imageinfo", iiprop="url|extmetadata|size|mime", iiurlwidth="900", format="json", formatversion="2")
    url = API + "?" + urllib.parse.urlencode(p)
    for k in range(8):
        try:
            r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60)
            return json.loads(r.read().decode())
        except Exception as e:
            if "429" in str(e):
                time.sleep(60 + 30 * k)
            else:
                time.sleep(10)
    return None


def cands(j):
    out = []
    for pg in (j or {}).get("query", {}).get("pages", []):
        ii = (pg.get("imageinfo") or [{}])[0]
        if not ii or not ii.get("mime", "").startswith("image/jpeg") and not ii.get("mime", "").startswith("image/png"):
            continue
        em = ii.get("extmetadata", {})
        g = lambda k: re.sub(r"<[^>]+>", "", (em.get(k, {}) or {}).get("value", "") or "").strip()
        out.append(dict(title=pg["title"], thumb=ii.get("thumburl"), w=ii.get("width"), h=ii.get("height"), lic=g("LicenseShortName"), author=g("Artist")[:120], desc=g("ImageDescription")[:240], date=g("DateTimeOriginal")[:40], page=ii.get("descriptionurl"), index=pg.get("index")))
    out.sort(key=lambda c: c.get("index") or 0)
    return out


def main(csv_path, cache_path):
    rows = list(csv.DictReader(open(csv_path, encoding="utf-8-sig")))
    cache = json.load(open(cache_path, encoding="utf-8")) if os.path.exists(cache_path) else {}
    qs = []
    for r in rows:
        y = r["Temporada"][:4] if r["Temporada"][0].isdigit() else r["Temporada"][-4:]
        y2 = str(int(y) + 1) if "/" in r["Temporada"] else y
        qs.append(f"{r['Club']} {y2}")
    for c in sorted({r["Club"] for r in rows}):
        qs += [f"{c} plantel", f"{c} estadio", f"{c} fútbol"]
    qs += ["Primera B Nacional", "Primera Nacional fútbol Argentina", "Nacional B fútbol Argentina estadio", "ascenso Primera División Argentina festejo", "hinchada ascenso Argentina"]
    for q in qs:
        if q in cache:
            continue
        j = query(q)
        cache[q] = cands(j)
        json.dump(cache, open(cache_path, "w", encoding="utf-8"), ensure_ascii=False)
        print(len(cache), q, len(cache[q]), flush=True)
        time.sleep(6)


if __name__ == "__main__":
    main(*sys.argv[1:3])
