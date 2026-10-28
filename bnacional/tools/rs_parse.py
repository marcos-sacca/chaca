"""RSSSF «Argentina Second Level»: lee los resultados por fecha de cada temporada (archivos arg2-YY.html).

Cada partido figura como 'Local<tab>1-0<tab>Visitante' (con o sin '(at ...)'), agrupado en 'Round N' y con fechas '[Feb 1, 1986]' / '(Aug 9)'.
"""
import html, re

LINE = re.compile(r"^\s*(?P<h>[^\d\[\]()][^\t]*?)\s*(?:\t+|\s{2,})(?P<a>\d+)-(?P<b>\d+)(?:\s*\([^)]*\))?\s*(?:\t+|\s{2,}|\s)(?P<v>[^\t\[\]]*?)\s*(?:\(at [^)]*\))?\s*(?:\[[^\]]*\])?\s*$")
DATE = re.compile(r"^\s*[\[(]([A-Z][a-z]{2})\w*\s+(\d{1,2})(?:,\s*(\d{4}))?[\])]")


def text_of(path):
    t = open(path, encoding="latin-1").read()
    t = re.sub(r"<[^>]+>", "", t)
    return html.unescape(t).replace("\r", "")


def parse(path):
    """-> [{'sec': título de la sección, 'round': 'Round 3', 'date': 'Aug 9' | None, 'home','away','hg','ag'}]"""
    out, sec, rnd, date = [], "", "", None
    lines = text_of(path).split("\n")
    for i, ln in enumerate(lines):
        s = ln.strip()
        if not s:
            continue
        mr = re.match(r"^(Round \d+|Matchday \d+|Fecha \d+|Semi-?finals?|Quarter-?finals?|Final|Final Round|1st Leg|2nd Leg|First Round|Second Round|Third Round|Play-?offs?)\b", s, re.I)
        if mr and not re.search(r"\d-\d", s):
            rnd = s
            date = None
            continue
        md = DATE.match(s)
        if md and not re.search(r"\d-\d", s):
            date = f"{md.group(1)} {md.group(2)}" + (f" {md.group(3)}" if md.group(3) else "")
            continue
        m = LINE.match(ln.rstrip())
        if m and not re.match(r"^\s*\d+\s*\.?", m.group("h")) and not re.search(r"\d\s+\d", m.group("v")) and len(m.group("h")) > 2 and len(m.group("v")) > 2 and not s.startswith("No.") and "Table" not in s:
            out.append({"sec": sec, "round": rnd, "date": date, "home": m.group("h").strip(), "away": m.group("v").strip(), "hg": int(m.group("a")), "ag": int(m.group("b"))})
            continue
        if len(s) < 70 and not re.search(r"\d-\d", s) and re.match(r"^[A-Za-zÁÉÍÓÚáéíóúñÑ0-9 /\-\"'()º.]+$", s) and ("Group" in s or "Zone" in s or "Apertura" in s or "Clausura" in s or "Nacional" in s or "Primera" in s or "Promotion" in s or "Playoff" in s or "Stage" in s or "Octogonal" in s or "Final" in s or "Reducido" in s or "Relegation" in s or "Championship" in s or "Permanence" in s):
            sec = s
    return out
