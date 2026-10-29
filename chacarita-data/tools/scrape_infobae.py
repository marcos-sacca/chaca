"""
Infobae (archivo desde 2002): crónicas con "Síntesis" (formaciones, DT, goles con minuto, árbitro, cancha) de partidos de Chacarita.
Se listan los artículos de cada día con el sitemap diario (https://www.infobae.com/arc/outboundfeeds/sitemap/AAAA-MM-DD/)
y se bajan los que tienen "chacarita" en la dirección.

  python3 -I scrape_infobae.py <desde AAAA-MM-DD> <hasta AAAA-MM-DD> <salida.jsonl> [regex_de_la_direccion]
  (por defecto "chacarita|funebre"; con "chacarita|funebre|nacional|ascenso|primera-b" se bajan además las notas de la categoría)
"""
import datetime
import html as H
import json
import re
import sys
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor

PAT = sys.argv[4] if len(sys.argv) > 4 else r"chacarita|funebre"
UA = {"User-Agent": "Mozilla/5.0 (investigacion historica)"}


def get(url, tries=3):
    for k in range(tries):
        try:
            return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=40).read().decode("utf-8", "ignore")
        except Exception as e:
            if "404" in str(e):
                return None
            time.sleep(2 * (k + 1))
    return None


def day_urls(day):
    t = get("https://www.infobae.com/arc/outboundfeeds/sitemap/%s/" % day)
    time.sleep(0.25)
    if not t:
        return day, []
    return day, [u for u in re.findall(r"<loc>([^<]+)</loc>", t) if re.search(PAT, u)]


def article(url):
    t = get(url)
    time.sleep(0.25)
    if not t:
        return None
    body = None
    for mm in re.finditer(r'<script type="application/ld\+json">(.*?)</script>', t, re.S):
        try:
            j = json.loads(mm.group(1))
        except Exception:
            continue
        if isinstance(j, dict) and "articleBody" in j:
            body = j["articleBody"]
            head = j.get("headline")
            break
    if not body:
        return None
    if "hacarita" not in body:
        return None
    return dict(url=url, titulo=head, cuerpo=body)


def main():
    a = datetime.date.fromisoformat(sys.argv[1]); b = datetime.date.fromisoformat(sys.argv[2]); out = sys.argv[3]
    days = [(a + datetime.timedelta(days=i)).isoformat() for i in range((b - a).days + 1)]
    urls = []
    with ThreadPoolExecutor(3) as ex:
        for k, (d, us) in enumerate(ex.map(day_urls, days)):
            urls += us
            if k % 100 == 0:
                print("dias", k, "urls", len(urls), flush=True)
    print("urls candidatas", len(urls), flush=True)
    with ThreadPoolExecutor(3) as ex, open(out, "w", encoding="utf-8") as f:
        for r in ex.map(article, urls):
            if r:
                f.write(json.dumps(r, ensure_ascii=False) + "\n"); f.flush()


if __name__ == "__main__":
    main()
