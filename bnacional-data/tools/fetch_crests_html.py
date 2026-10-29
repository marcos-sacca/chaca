"""Segunda pasada de escudos: para los clubes sin logo en Wikidata/infobox toma la primera imagen que no sea camiseta/bandera
de la ficha HTML del artículo. python3 -I fetch_crests_html.py <teams.json> <carpeta_img> <crests.json>"""
import hashlib, io, json, os, re, sys, time, urllib.parse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from fetch_crests import http, raw_article, candidates, STOP, norm  # noqa
from PIL import Image

BAD = re.compile(r"kit_|flag|bandera|pattern|map|mapa|estadio|stadium|camiseta|commons-logo|wiki|cup|copa|trophy", re.I)


def logo_from_html(title):
    _, html = http("https://es.wikipedia.org/w/index.php?title=" + urllib.parse.quote(title.replace(" ", "_")))
    time.sleep(0.8)
    if not html:
        return None
    box = re.search(r'<table[^>]*class="[^"]*infobox[^"]*".*?</table>', html, re.S)
    for m in re.finditer(r'upload\.wikimedia\.org/wikipedia/(commons|es)/(?:thumb/)?\w/\w\w/([^/"?]+)', (box.group(0) if box else html[:60000])):
        f = urllib.parse.unquote(m.group(2))
        if not BAD.search(f) and re.search(r"\.(svg|png|jpe?g)$", f, re.I):
            return f.replace("_", " ")
    return None


def main(teams, imgdir, out):
    T = json.load(open(teams, encoding="utf-8")); res = json.load(open(out, encoding="utf-8"))
    for t in T:
        if res.get(t["s"]):
            continue
        fname = title = None
        for q in candidates(t["n"], t["short"]):
            ti, txt = raw_article(q)
            if txt and re.search(r"\{\{\s*Ficha de (?:equipo|club)", txt, re.I):
                title = ti; fname = logo_from_html(ti)
                if fname:
                    break
        if not fname:
            print("SIN", t["n"], flush=True); continue
        n_ = fname.replace(" ", "_"); h_ = hashlib.md5(n_.encode()).hexdigest(); q_ = urllib.parse.quote(n_)
        for kind in ("commons", "es"):
            ext = ".png" if n_.lower().endswith(".svg") else ""
            _, data = http(f"https://upload.wikimedia.org/wikipedia/{kind}/thumb/{h_[0]}/{h_[:2]}/{q_}/250px-{q_}{ext}", binary=True, tries=4)
            time.sleep(0.8)
            if data:
                try:
                    im = Image.open(io.BytesIO(data)).convert("RGBA"); im.thumbnail((220, 220)); im.save(os.path.join(imgdir, t["s"] + ".png"), optimize=True)
                    res[t["s"]] = dict(img=f"assets/img/crests/{t['s']}.png", article=title, file=fname, source=("commons" if kind == "commons" else "es.wikipedia"),
                                       page=("https://commons.wikimedia.org/wiki/File:" if kind == "commons" else "https://es.wikipedia.org/wiki/Archivo:") + q_)
                    print("ok", t["n"], "|", title, "|", fname, flush=True); json.dump(res, open(out, "w"), ensure_ascii=False); break
                except Exception:
                    pass
        else:
            print("NO BAJÓ", t["n"], fname, flush=True)


if __name__ == "__main__":
    main(*sys.argv[1:4])
