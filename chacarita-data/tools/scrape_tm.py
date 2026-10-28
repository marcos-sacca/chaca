"""Transfermarkt: calendario de Chacarita por temporada y ficha de cada partido (árbitro, DT, formaciones, goles).

Uso: python3 -I tools/scrape_tm.py <cache_dir> <salida.json> [desde_temporada] [hasta_temporada]
- robots.txt de Transfermarkt permite el rastreo general; se espera 2,5 s entre pedidos y se guarda todo en caché.
- La fecha/hora del sitio puede venir corrida un día respecto de Argentina: el cruce con la planilla se hace por ±1 día y marcador.
"""
import json, os, re, sys, time, urllib.request
from bs4 import BeautifulSoup

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36 chacarita-data/1.0 (proyecto de hinchas, sin fines comerciales)"
BASE = "https://www.transfermarkt.com"
CLUB = "/ca-chacarita-juniors/spielplan/verein/2154/saison_id/{}"


def get(url, cache, tag):
    f = os.path.join(cache, tag + ".html")
    if os.path.exists(f):
        return open(f, encoding="utf-8", errors="replace").read()
    for i in range(4):
        try:
            h = urllib.request.urlopen(urllib.request.Request(BASE + url, headers={"User-Agent": UA, "Accept-Language": "en"}), timeout=60).read().decode("utf-8", "replace")
            open(f, "w", encoding="utf-8").write(h)
            time.sleep(2.5)
            return h
        except Exception as e:  # noqa: BLE001
            err = e
            time.sleep(6 * (i + 1))
    print("FALLÓ", url, err, file=sys.stderr)
    return None


def txt(el):
    return re.sub(r"\s+", " ", el.get_text(" ")).strip()


def parse_schedule(html, season):
    b = BeautifulSoup(html, "lxml")
    out = []
    for bx in b.select("div.box"):
        h = bx.select_one("h2, .table-header")
        title = txt(h) if h else ""
        if title.startswith("Table section") or not bx.select("table"):
            continue
        for tr in bx.select("table tbody tr"):
            tds = tr.select("td")
            rep = [a.get("href") for a in tr.select("a") if a.get("href", "").startswith("/spielbericht/")]
            if len(tds) < 8 or not rep:
                continue
            cells = [txt(td) for td in tds]
            m = re.search(r"(\d{2}/\d{2}/\d{4})", cells[1])
            res = re.search(r"(\d+):(\d+)", cells[-1])
            if not m:
                continue
            out.append({"season": season, "comp": title, "round": cells[0], "date": m.group(1), "time": cells[2], "ha": cells[3], "opp": re.sub(r"\s*\(\d+\.\)\s*$", "", cells[6]),
                        "res": [int(res.group(1)), int(res.group(2))] if res else None, "report": rep[0].rsplit("/", 1)[1]})
    return out


def slug_name(href):
    m = re.match(r"^/([^/]+)/profil/", href or "")
    return m.group(1).replace("-", " ").title() if m else None


def parse_report(html):
    """Árbitro, DT, formaciones (titulares y banco), goles y asistencia de una ficha. El primer bloque es siempre el local."""
    b = BeautifulSoup(html, "lxml")
    for s in b(["script", "style"]):
        s.decompose()
    t = txt(b)
    r = {}
    ref = b.select_one("a[href*='/schiedsrichter/']")
    r["referee"] = txt(ref) if ref else None
    att = re.search(r"Attendance:\s*([\d.,]+)", t)
    r["attendance"] = int(re.sub(r"[.,]", "", att.group(1))) if att else None
    st = b.select_one(".sb-zusatzinfos a[href*='/stadion/']")
    r["stadium"] = txt(st) if st else None
    r["managers"] = [txt(x) for x in b.select("a[href*='/profil/trainer/']")][:2]
    cont = b.select(".formation-player-container a[href*='/profil/spieler/']")
    xi = [{"n": txt(a), "full": slug_name(a.get("href"))} for a in cont]
    benches = b.select(".aufstellung-ersatzbank-box")
    subs = [[{"n": txt(a), "full": slug_name(a.get("href"))} for a in bx.select("a[href*='/profil/spieler/']")] for bx in benches]
    r["lineups"] = [{"xi": xi[:11], "bench": subs[0] if subs else []}, {"xi": xi[11:22], "bench": subs[1] if len(subs) > 1 else []}]
    # sustituciones: los que ingresaron (nombre completo vía enlace)
    ins = []
    for blk in b.select("div.box"):
        h = blk.select_one("h2")
        if h and txt(h).startswith("Substitutions"):
            for li in blk.select("div.sb-aktion"):
                links = li.select("a[href*='/profil/spieler/']")
                if links:
                    ins.append({"in": slug_name(links[0].get("href")), "out": slug_name(links[1].get("href")) if len(links) > 1 else None, "text": txt(li)})
    r["subs_in"] = ins
    goals, seen = [], None
    for blk in b.select("div.box"):
        h = blk.select_one("h2")
        if h and txt(h).startswith("Goals"):
            for li in blk.select("div.sb-aktion"):
                x = txt(li)
                lk = li.select_one("a[href*='/profil/spieler/']")
                m = re.match(r"(\d+):(\d+)\s", x)
                if m and x != seen:
                    goals.append({"score": [int(m.group(1)), int(m.group(2))], "player": slug_name(lk.get("href")) if lk else None, "short": txt(lk) if lk else None, "text": x})
                seen = x
    r["goals"] = goals
    return r


if __name__ == "__main__":
    cache, out = sys.argv[1], sys.argv[2]
    s0 = int(sys.argv[3]) if len(sys.argv) > 3 else 2002
    s1 = int(sys.argv[4]) if len(sys.argv) > 4 else 2026
    os.makedirs(cache, exist_ok=True)
    res = json.load(open(out, encoding="utf-8")) if os.path.exists(out) else {"matches": {}}
    for season in range(s0, s1 + 1):
        h = get(CLUB.format(season), cache, f"sched_{season}")
        if not h:
            continue
        for it in parse_schedule(h, season):
            key = it["report"]
            if key in res["matches"] and res["matches"][key].get("rep"):
                continue
            rh = get(f"/spielbericht/index/spielbericht/{key}", cache, f"rep_{key}")
            it["rep"] = parse_report(rh) if rh else None
            res["matches"][key] = it
        json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False)
        print(season, len(res["matches"]), flush=True)
