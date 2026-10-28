"""Chacarita Digital (chacaritadigital.com.ar): baja por la API pública de WordPress todas las notas y las guarda en un JSON.

Uso: python3 -I tools/scrape_cd.py <salida_posts.json>
Cada nota de temporada trae, partido por partido: formaciones de los dos equipos, DT, árbitro, recaudación/entradas, cancha y goles con minuto.
robots.txt permite el acceso (solo bloquea /wp-admin/); se pide en lotes de 50 con 2 s de pausa.
"""
import json, sys, time, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36 chacarita-data/1.0 (proyecto de hinchas, sin fines comerciales)"

if __name__ == "__main__":
    out, page, allp = sys.argv[1], 1, []
    while True:
        u = f"https://www.chacaritadigital.com.ar/wp-json/wp/v2/posts?per_page=50&page={page}&_fields=id,date,slug,link,title,categories,content"
        try:
            d = json.load(urllib.request.urlopen(urllib.request.Request(u, headers={"User-Agent": UA}), timeout=120))
        except urllib.error.HTTPError:
            break
        if not d:
            break
        allp += d
        page += 1
        time.sleep(2)
    json.dump(allp, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print(len(allp), "notas")
