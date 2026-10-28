"""
Museo Granate (museogranate.clublanus.com): fichas de los partidos Lanús–Chacarita (árbitro, estadio, goles con minuto,
formaciones y DT de ambos equipos). robots.txt permite el rastreo.

  python3 -I scrape_museogranate.py <matches.json> <salida.json>
"""
import html as H
import json
import re
import sys
import time
import urllib.request


def get(url):
    for k in range(3):
        try:
            r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (investigacion historica)"})
            return urllib.request.urlopen(r, timeout=40).read().decode("utf-8", "ignore")
        except Exception as e:
            if "404" in str(e):
                return None
            time.sleep(2 * (k + 1))
    return None


def lines(t):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", "\n", t)
    return [l.strip() for l in H.unescape(t).splitlines() if l.strip()]


NAME = re.compile(r'class="truncate text-body-200-semibold text-ink[^"]*"[^>]*>([^<]+)<')


def parse(t):
    d = {}
    L = lines(t)
    for k, lab in (("arbitro", "Árbitro"), ("estadio", "Estadio")):
        if lab in L:
            d[k] = L[L.index(lab) + 1]
    # goles: cada tarjeta "Gooool!!" trae minuto, marcador parcial y goleador
    goles = []
    for card in t.split("Gooool!!")[1:]:
        card = card[:3500]
        mn = re.search(r"(\d+)(?:\+\d+)?&#x27;", card)
        sc = re.search(r"<span class=\"text-body-200-semibold tabular-nums\">(\d+)<!-- --> - <!-- -->(\d+)</span>", card)
        nm = NAME.search(card)
        goles.append(dict(min=int(mn.group(1)) if mn else None, marcador=[int(sc.group(1)), int(sc.group(2))] if sc else None, jugador=nm.group(1).strip() if nm else None))
    d["goles"] = goles
    # formaciones: secciones <h2>Equipo</h2> con subtítulos h3 (Titulares / Suplentes / Director técnico)
    teams = []
    for sec in re.split(r'<h2 class="m-0 text-body-400-bold[^>]*>', t)[1:]:
        name = sec.split("</h2>")[0]
        body = sec.split("</h2>", 1)[1]
        body = re.split(r"<h2 ", body)[0]
        parts = re.split(r'<h3 class="m-0 text-utility-caption-semibold[^>]*>', body)
        tm = dict(nombre=H.unescape(name), titulares=[], suplentes=[], dt=None)
        for pr in parts[1:]:
            title, rest = pr.split("</h3>", 1)
            names = [H.unescape(x).strip() for x in NAME.findall(rest)]
            if title.startswith("Titulares"): tm["titulares"] = names
            elif title.startswith("Suplentes"): tm["suplentes"] = names
            elif title.startswith("Director"): tm["dt"] = names[0] if names else None
        if tm["titulares"] or tm["dt"]:
            teams.append(tm)
    d["equipos"] = teams
    return d


def main():
    M = json.load(open(sys.argv[1], encoding="utf-8"))
    out = {}
    for m in M:
        if m["r"] != "Lanús":
            continue
        url = "https://museogranate.clublanus.com/partidos/lanus-vs-chacarita-juniors-" + m["d"]
        t = get(url)
        time.sleep(1.5)
        if not t:
            continue
        d = parse(t)
        d["url"] = url
        d["mid"] = m["id"]
        out[m["id"]] = d
        print(m["id"], m["d"], d.get("arbitro"), [len(x["titulares"]) for x in d["equipos"]], flush=True)
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
