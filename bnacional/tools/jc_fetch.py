"""Descarga páginas de josecarluccio.blogspot.com («Historia y Fútbol») y las guarda como texto plano en un caché local.

Uso:
  python3 -I jc_fetch.py catalog <cache_dir>            # lista de todas las entradas del blog (feed JSON de Blogger)
  python3 -I jc_fetch.py get <cache_dir> <url> [<url>…]  # baja páginas puntuales
Pausa de 1,2 s entre pedidos; no vuelve a bajar lo que ya está en el caché.
"""
import html, json, os, re, sys, time, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36 chacarita-data/1.0 (proyecto de hinchas, sin fines comerciales)"
BASE = "https://josecarluccio.blogspot.com"


def key(url):
    return re.sub(r"[^a-z0-9]+", "_", url.split("josecarluccio.blogspot.com")[-1].lower().strip("/"))[:140]


def to_text(page):
    m = re.search(r"<div class='post-body[^>]*>(.*?)<div class='post-footer", page, re.S)
    b = m.group(1) if m else page
    t = re.sub(r"<br\s*/?>", "\n", b)
    t = re.sub(r"</(p|div|tr|h\d|li)>", "\n", t)
    t = re.sub(r"<[^>]+>", "", t)
    t = html.unescape(t)
    t = re.sub(r"[ \t ]+", " ", t)
    return re.sub(r"\n\s*\n+", "\n", t)


def get(url, cache, retries=3):
    os.makedirs(cache, exist_ok=True)
    f = os.path.join(cache, key(url) + ".txt")
    if os.path.exists(f):
        return open(f, encoding="utf-8").read()
    err = None
    for i in range(retries):
        try:
            page = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=60).read().decode("utf-8", "replace")
            t = to_text(page)
            open(f, "w", encoding="utf-8").write(t)
            time.sleep(1.2)
            return t
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(3 * (i + 1))
    print("FALLÓ", url, err, file=sys.stderr)
    return None


def catalog(out):
    posts, start = [], 1
    while True:
        u = f"{BASE}/feeds/posts/summary?alt=json&max-results=150&start-index={start}"
        d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=60))
        ent = d["feed"].get("entry", [])
        if not ent:
            break
        for e in ent:
            link = [l["href"] for l in e["link"] if l["rel"] == "alternate"][0]
            posts.append({"t": e["title"]["$t"], "u": link, "p": e["published"]["$t"][:10]})
        start += len(ent)
        time.sleep(1)
    json.dump(posts, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    return posts


if __name__ == "__main__":
    cmd, cache = sys.argv[1], sys.argv[2]
    if cmd == "catalog":
        print(len(catalog(os.path.join(cache, "catalog.json"))), "entradas")
    else:
        for u in sys.argv[3:]:
            print(u[-60:], len(get(u, cache) or ""))
