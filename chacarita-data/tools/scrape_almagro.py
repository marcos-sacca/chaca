"""
El Sitio de Almagro (elsitiodealmagro.com.ar): fichas de los partidos Almagro–Chacarita (árbitro, estadio, formación de Almagro,
DT de Almagro). Se piden por fecha de los partidos que ya tenemos contra Almagro.

  python3 -I scrape_almagro.py <matches.json> <salida.json>
"""
import html as H
import json
import re
import sys
import time
import urllib.request

PATS = ["chacarita-juniors-club-almagro-%s", "almagro-chacarita-juniors-%s", "club-almagro-chacarita-juniors-%s", "chacarita-juniors-almagro-%s"]


def get(url):
    try:
        r = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (investigacion historica)"})
        return urllib.request.urlopen(r, timeout=40).read().decode("utf-8", "ignore")
    except Exception:
        return None


def lines(t):
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    t = re.sub(r"<[^>]+>", "\n", t)
    return [l.strip() for l in H.unescape(t).splitlines() if l.strip()]


def main():
    M = json.load(open(sys.argv[1], encoding="utf-8"))
    out = {}
    for m in M:
        if m["r"] != "Almagro":
            continue
        for p in PATS:
            url = "https://www.elsitiodealmagro.com.ar/partido/" + p % m["d"] + "/"
            t = get(url)
            time.sleep(0.8)
            if t and "Alineación inicial" in t or (t and "Árbitros" in t):
                L = lines(t)
                d = dict(url=url, mid=m["id"], L=L[L.index("Medio tiempo: -") - 4 if "Medio tiempo: -" in L else 0:][:140])
                out[m["id"]] = d
                print(m["id"], m["d"], "ok", flush=True)
                break
        else:
            print(m["id"], m["d"], "sin página", flush=True)
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
