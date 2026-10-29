"""
Baja las "síntesis" de partidos de Solo Ascenso (soloascenso.com.ar/sintesis/x/<id>) y las guarda como JSON Lines.
Cada página trae: fecha, categoría, estadio, árbitro, formaciones (con puesto y edad), DT, goles, cambios, tarjetas.

  python3 -I sa_scrape.py <salida.jsonl> <id_desde> <id_hasta> [demora_seg=0.35]

Se puede cortar y retomar: salta los ids que ya están en la salida. robots.txt de Solo Ascenso permite el rastreo.
"""
import html as H
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

URL = "https://www.soloascenso.com.ar/sintesis/x/%d"


def fetch(i, tries=4):
    for k in range(tries):
        try:
            r = urllib.request.Request(URL % i, headers={"User-Agent": "Mozilla/5.0 (investigacion historica; contacto marcos.e.sacca@gmail.com)"})
            return urllib.request.urlopen(r, timeout=40).read().decode("utf-8", "ignore")
        except Exception as e:
            if "404" in str(e):
                return None
            time.sleep(2 * (k + 1))
    return "ERR"


def txt(s):
    return H.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


def parse(i, t):
    m = re.search(r'<div id="fecha-hora">(.*?)</div>', t, re.S)
    if not m:
        return None
    head = txt(m.group(1))
    c1 = re.search(r'<div id="columna1">.*?<p>(.*?)</p>\s*<p>(.*?)</p>', t, re.S)
    c2 = re.search(r'<div id="columna2">.*?<p>(.*?)</p>\s*<p>(.*?)</p>', t, re.S)
    if not (c1 and c2):
        return None
    d = dict(id=i, head=head, local=txt(c1.group(1)), visitante=txt(c2.group(1)), gl=txt(c1.group(2)), gv=txt(c2.group(2)))
    p = [x.strip() for x in head.split("|")]
    mm = re.match(r"(\d\d)\.(\d\d)\.(\d\d)$", p[0]) if p else None
    if not mm:
        return None
    yy = int(mm.group(3))
    d["fecha"] = f"{2000 + yy if yy < 70 else 1900 + yy}-{mm.group(2)}-{mm.group(1)}"
    for x in p[1:]:
        if re.match(r"\d\d:\d\d$", x): d["hora"] = x
        elif x.startswith("Fecha ") or x.lower().startswith(("octavos", "cuartos", "semi", "final", "reducido", "ida", "vuelta", "promoci", "zona", "grupo", "fase", "repechaje", "dieciseisavos", "16avos")): d["ronda"] = x
        elif x.startswith("Estadio:"): d["estadio"] = x[8:].strip()
        elif x.startswith("Árbitro:"): d["arbitro"] = x[8:].strip()
        elif x in ("Primera Nacional", "Primera B", "Primera C", "Promocional Amateur", "Federal A", "Regional Amateur", "Copa Argentina", "Primera B Metropolitana", "Torneo Federal A", "Torneo Argentino A", "Torneo Argentino B", "Torneo del Interior", "Primera División"): d["cat"] = x
    teams = re.split(r'<div id="(?:local|visitante)">', t)[1:]
    d["eq"] = []
    for blk in teams[:2]:
        blk = blk.split("</div>")[0] if False else blk
        arts = re.findall(r'<article class="([^"]*)">\s*<img src="/\.\./perfil/(\d+)\.png"/>\s*<span class="camiseta">([^<]*)</span>\s*<a href="[^"]*/(\d+)" target="_blank">([^<]*)</a>', blk)
        xi, sup, dt = [], [], None
        for k, (cls, imgid, cam, pid, nm) in enumerate(arts):
            nm = H.unescape(nm).strip()
            ma = re.match(r"(.*?)\s*\((\d+)\)$", nm)
            name, age = (ma.group(1), int(ma.group(2))) if ma else (nm, None)
            if cls == "suplente" and cam == "DT" and k == len(arts) - 1:
                dt = name
                continue
            row = [cam, name, age, cls, int(pid)]
            (sup if cls == "suplente" else xi).append(row)
        d["eq"].append(dict(xi=xi, sup=sup, dt=dt))
    for key, lab in (("goles", "Goles"), ("cambios", "Cambios"), ("amon", "Amonestados"), ("exp", "Expulsados")):
        mg = re.search(r'<b>%s:</b>(.*?)</p>' % lab, t, re.S)
        if mg:
            d[key] = txt(mg.group(1))
    return d


def main():
    out, a, b = Path(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
    delay = float(sys.argv[4]) if len(sys.argv) > 4 else 0.35
    done = set()
    for f in out.parent.glob("*.jsonl"):  # también lo que bajaron otros procesos en la misma carpeta
        for ln in f.read_text(encoding="utf-8").splitlines():
            try: done.add(json.loads(ln)["id"])
            except Exception: pass
    with out.open("a", encoding="utf-8") as f:
        for i in range(a, b + 1):
            if i in done:
                continue
            t = fetch(i)
            if t == "ERR":
                f.write(json.dumps(dict(id=i, err=1)) + "\n"); f.flush(); continue
            d = parse(i, t) if t else None
            f.write(json.dumps(d if d else dict(id=i, vacio=1), ensure_ascii=False, separators=(",", ":")) + "\n")
            if i % 50 == 0: f.flush()
            time.sleep(delay)


if __name__ == "__main__":
    main()
