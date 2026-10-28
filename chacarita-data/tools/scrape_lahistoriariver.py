"""
La Historia River (lahistoriariver.com): fichas de los partidos River–Chacarita (≈118) con árbitro, estadio,
goles con minuto, DT, titulares y suplentes de ambos equipos. robots.txt permite /partidos/.

  python3 -I scrape_lahistoriariver.py <urls.txt> <salida.json>
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


def parse(url, t):
    L = lines(t)
    if "Ficha de partido" not in L:
        return None
    i = L.index("Ficha de partido")
    d = dict(url=url, comp=L[i + 1])
    j = i + 2
    if L[j] == "·":
        d["instancia"] = L[j + 1]; j += 2
    d["local"], d["visitante"] = L[j], L[j + 2]
    d["fecha_txt"] = L[j + 3]
    # eventos: entre "Eventos" y "Competencia"
    c0 = L.index("Competencia", i)
    e0 = L.index("Eventos", i) if "Eventos" in L[i:c0] else None
    ev = L[e0 + 1:c0] if e0 is not None else []
    d["eventos"] = ev
    for k, lab in (("arbitro", "Árbitro"), ("estadio", "Estadio"), ("condicion", "Condición")):
        if lab in L[c0:]:
            d[k] = L[L.index(lab, c0) + 1]
    # formaciones
    f0 = L.index("Formaciones", c0) if "Formaciones" in L[c0:] else None
    teams = {}
    if f0:
        k = f0
        while k < len(L):
            if L[k] == "Titulares" and k > 0:
                name = L[k - 1]
                if name not in teams:
                    xi, sup, dt = [], [], None
                    m = k + 1
                    STOP = ("Entrenador", "Suplentes", "Colaborá con La Historia River", "Eventos", "Tarjetas", "Titulares")
                    while m < len(L) and L[m] not in STOP and len(xi) < 12:
                        xi.append(L[m]); m += 1
                    if m < len(L) and L[m] == "Entrenador":
                        dt = L[m + 1]; m += 2
                    if m < len(L) and L[m] == "Suplentes":
                        m += 1
                        while m < len(L) and L[m] not in ("Titulares", "Eventos", "Tarjetas", "Colaborá con La Historia River") and not (m + 1 < len(L) and L[m + 1] == "Titulares"):
                            sup.append(L[m]); m += 1
                    teams[name] = dict(xi=xi, sup=sup, dt=dt)
                k += 1
            else:
                k += 1
    d["equipos"] = teams
    return d


def main():
    urls = [u.strip() for u in open(sys.argv[1]) if u.strip()]
    out = {}
    for u in urls:
        t = get(u)
        time.sleep(1.2)
        if not t:
            print("sin página", u, flush=True); continue
        d = parse(u, t)
        if d:
            out[u] = d
            print(d["fecha_txt"], d["local"], d["visitante"], d.get("arbitro"), {k: len(v["xi"]) for k, v in d["equipos"].items()}, flush=True)
    json.dump(out, open(sys.argv[2], "w", encoding="utf-8"), ensure_ascii=False)


if __name__ == "__main__":
    main()
