"""Transfermarkt: calendario completo de la Primera Nacional (código ARG2) por temporada, con fecha, equipos y resultado.

Uso: python3 -I tm_league.py <cache_dir> <salida.json> [desde_saison_id] [hasta_saison_id]
Sirve como segunda fuente de resultados (control cruzado de las crónicas) y para temporadas posteriores a 2018/19.
Una sola página por temporada; 3 s entre pedidos. Las horas del sitio están en horario europeo: la fecha puede venir un día corrida.
"""
import json, os, re, sys, time, urllib.request
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36 chacarita-data/1.0 (proyecto de hinchas, sin fines comerciales)"
URL = "https://www.transfermarkt.com/primera-nacional/gesamtspielplan/wettbewerb/ARG2/saison_id/{}"


def get(season, cache):
    f = os.path.join(cache, f"arg2_{season}.html")
    if os.path.exists(f):
        return open(f, encoding="utf-8", errors="replace").read()
    err = None
    for i in range(4):
        try:
            h = urllib.request.urlopen(urllib.request.Request(URL.format(season), headers={"User-Agent": UA, "Accept-Language": "en"}), timeout=90).read().decode("utf-8", "replace")
            open(f, "w", encoding="utf-8").write(h)
            time.sleep(3)
            return h
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(8 * (i + 1))
    print("FALLÓ", season, err, file=sys.stderr)
    return None


def txt(el):
    return re.sub(r"\s+", " ", el.get_text(" ")).strip()


def parse(html):
    b = BeautifulSoup(html, "lxml")
    title = txt(b.title) if b.title else ""
    out, rounds = [], []
    for bx in b.select("div.box"):
        hd = bx.select_one(".content-box-headline")
        if not hd:
            continue
        label = txt(hd)
        date = None
        for tr in bx.select("table tbody tr"):
            tds = [txt(td) for td in tr.select("td")]
            rep = [a.get("href") for a in tr.select("a[href*='spielbericht']")]
            if len(tds) == 1:
                m = re.search(r"(\d{2}/\d{2}/\d{2})", tds[0])
                if m:
                    date = m.group(1)
                continue
            if len(tds) < 7 or not rep:
                continue
            m = re.search(r"(\d{2}/\d{2}/\d{2})", tds[0])
            if m:
                date = m.group(1)
            res = re.search(r"(\d+):(\d+)", tds[4])
            home = re.sub(r"^\(\d+\.\)\s*", "", tds[2])
            away = re.sub(r"\s*\(\d+\.\)$", "", tds[6])
            out.append({"round": label, "date": date, "time": tds[1] or None, "home": home, "away": away, "hg": int(res.group(1)) if res else None, "ag": int(res.group(2)) if res else None,
                        "report": rep[0].rsplit("/", 1)[1], "slug": rep[0].split("/")[1]})
    return {"title": title, "matches": out}


if __name__ == "__main__":
    cache, out = sys.argv[1], sys.argv[2]
    a = int(sys.argv[3]) if len(sys.argv) > 3 else 2008
    z = int(sys.argv[4]) if len(sys.argv) > 4 else 2026
    os.makedirs(cache, exist_ok=True)
    res = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else {}
    for s in range(a, z + 1):
        h = get(s, cache)
        if h:
            res[str(s)] = parse(h)
            print(s, len(res[str(s)]["matches"]), res[str(s)]["title"][:60], flush=True)
            json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False)
