"""
Scraping puntual (uso interno, bajo volumen) del plantel de un club en
Transfermarkt via BeautifulSoup: nombre, posicion, edad, nacionalidad,
valor de mercado. Ver informe_datos_chacarita.html para el encuadre legal.
"""
import sys
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup
import pandas as pd

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
ROOT = Path(__file__).resolve().parent.parent


def fetch_squad(slug: str, verein_id: int) -> pd.DataFrame:
    url = f"https://www.transfermarkt.com/{slug}/startseite/verein/{verein_id}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    rows = []
    table = soup.find("table", class_="items")
    if not table:
        return pd.DataFrame()
    for tr in table.find("tbody").find_all("tr", recursive=False):
        name_tag = tr.select_one("td.posrela a[href*='/profil/spieler/']")
        if not name_tag:
            continue
        name = name_tag.get_text(strip=True)
        pos_tag = tr.select_one("td.posrela table.inline-table tr:nth-of-type(2) td")
        position = pos_tag.get_text(strip=True) if pos_tag else None
        dob_tag = tr.select_one("td.zentriert:nth-of-type(3)")
        age_dob = dob_tag.get_text(strip=True) if dob_tag else None
        nat_imgs = tr.select("td.zentriert img.flaggenrahmen")
        nationality = ", ".join(img.get("title", "") for img in nat_imgs)
        value_tag = tr.select_one("td.rechts.hauptlink a")
        value = value_tag.get_text(strip=True) if value_tag else None
        rows.append({
            "name": name, "position": position, "age_dob": age_dob,
            "nationality": nationality, "market_value": value,
        })
    return pd.DataFrame(rows)


if __name__ == "__main__":
    slug, vid, out_name = sys.argv[1], int(sys.argv[2]), sys.argv[3]
    df = fetch_squad(slug, vid)
    out_path = ROOT / "data" / "raw" / f"tm_squad_{out_name}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8-sig")
    print(f"Guardado {len(df)} jugadores en {out_path}")
    print(df.to_string(index=False))
