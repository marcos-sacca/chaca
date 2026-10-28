"""Baja las páginas de RSSSF «Argentina Second Level» (arg2-87 a arg2-08) al directorio de caché. Uso: python3 -I rs_fetch.py <dir>"""
import os, sys, time, urllib.request

UA = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36 chacarita-data/1.0 (proyecto de hinchas, sin fines comerciales)"
YY = ["87", "88", "89", "90", "91", "92", "93", "94", "95", "96", "97", "98", "99", "00", "01", "02", "03", "04", "05", "06", "07", "08"]

if __name__ == "__main__":
    d = sys.argv[1]
    os.makedirs(d, exist_ok=True)
    for y in YY:
        f = os.path.join(d, f"arg2-{y}.html")
        if os.path.exists(f) and os.path.getsize(f) > 2000:
            continue
        data = urllib.request.urlopen(urllib.request.Request(f"https://www.rsssf.org/tablesa/arg2-{y}.html", headers={"User-Agent": UA}), timeout=60).read()
        open(f, "wb").write(data)
        print(y, len(data))
        time.sleep(1.5)
