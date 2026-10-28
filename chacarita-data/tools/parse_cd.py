"""Interpreta las notas de temporada de Chacarita Digital y devuelve los partidos con formaciones, DT, árbitro, entradas y cancha.

Uso: python3 -I tools/parse_cd.py <posts.json> <salida.json>
"""
import html, json, re, sys, unicodedata

MESES = {"enero": 1, "febrero": 2, "marzo": 3, "abril": 4, "mayo": 5, "junio": 6, "julio": 7, "agosto": 8, "septiembre": 9, "setiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12}
HEAD = re.compile(r"^(?P<h>[^\n]*?)\((?P<d>\d{1,2})\s+de\s+(?P<m>[a-zA-Zéáíóú]+)\s+de\s+(?P<y>\d{4})\)\s*(?P<rest>.*)$")
TEAM = re.compile(r"^(?P<t>[A-ZÁÉÍÓÚÑÜ0-9][A-ZÁÉÍÓÚÑÜ0-9 .'’()/\-&]*?)\s*\((?P<g>\d+)\)\s*:\s*(?P<p>.*)$")
GOAL = re.compile(r"^(?P<min>\d+(?:\+\d+)?)\s*(?:m\.?|′|’|')\s*(?P<a>\d+)-(?P<b>\d+)\s*(?P<who>.*)$")
SUBS = re.compile(r"\((\d+)\s*(?:m\.?|′|’|')\s*([^()]+?)\)")


def nk(s):
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn").lower()


def text_of(content):
    c = re.sub(r"<br\s*/?>", "\n", content)
    c = re.sub(r"</(p|div|h\d|li|tr)>", "\n", c)
    c = re.sub(r"<[^>]+>", "", c)
    c = html.unescape(c)
    c = re.sub(r"[ \t ]+", " ", c)
    return re.sub(r"\n\s*\n+", "\n", c)


def split_players(s):
    """'A; B y C, D' -> [(nombre, minuto_cambio | None, entra | None)] con los cambios '(45m. Nombre)'."""
    out = []
    subs = []
    def grab(m):
        subs.append((int(m.group(1)), m.group(2).strip()))
        return "§" + str(len(subs) - 1) + "§"
    s2 = SUBS.sub(grab, s)
    parts = [p.strip() for p in re.split(r"\s*[;,]\s*|\s+y\s+(?=[A-ZÁÉÍÓÚÑ])", s2) if p.strip()]
    for p in parts:
        mm = re.search(r"§(\d+)§", p)
        name = re.sub(r"§\d+§", "", p).strip(" .")
        if not name:
            continue
        if mm:
            minute, ent = subs[int(mm.group(1))]
            out.append((name, minute, ent))
        else:
            out.append((name, None, None))
    return out


def parse_post(title, text):
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    matches, cur, team_idx = [], None, -1
    comp = None
    for ln in lines:
        mh = HEAD.match(ln)
        if mh and mh.group("m").lower() in MESES and not TEAM.match(ln):
            cur = {"header": mh.group("h").strip(" -–:"), "date": f"{int(mh.group('y')):04d}-{MESES[mh.group('m').lower()]:02d}-{int(mh.group('d')):02d}", "teams": [], "goals": [], "post": title, "comp": comp}
            matches.append(cur)
            team_idx = -1
            continue
        if re.match(r"^(CAMPEONATO|TORNEO|COPA|ZONA|APERTURA|CLAUSURA|NACIONAL|METROPOLITANO|RUEDA)\b", ln) and len(ln) < 80 and not TEAM.match(ln):
            comp = ln
            continue
        if cur is None:
            continue
        mt = TEAM.match(ln)
        if mt and len(cur["teams"]) < 2:
            body = mt.group("p")
            bench, dt = [], None
            md = re.search(r"\bD\.?T\.?\s*:\s*(.*)$", body)
            if md:
                dt, body = md.group(1).strip(" ."), body[:md.start()]
            ms_ = re.search(r"\b(?:SUP\.?|SUPLENTES)\s*:\s*(.*)$", body, re.I)
            if ms_:
                bench, body = [x[0] for x in split_players(ms_.group(1))], body[:ms_.start()]
            cur["teams"].append({"name": mt.group("t").strip(), "goals": int(mt.group("g")), "players": split_players(body.strip(" .")), "bench": bench, "dt": dt})
            team_idx = len(cur["teams"]) - 1
            continue
        up = ln.upper()
        mg = GOAL.match(ln)
        if mg:
            cur["goals"].append(ln)
            continue
        if team_idx >= 0:
            t = cur["teams"][team_idx]
            ms = re.match(r"^(?:SUP\.?|SUPLENTES)\s*:?\s*(.*)$", ln, re.I)
            if ms:
                t["bench"] = [x[0] for x in split_players(ms.group(1))]
                continue
            md = re.match(r"^D\.?T\.?\s*:?\s*(.*)$", ln, re.I)
            if md:
                t["dt"] = md.group(1).strip(" .")
                continue
        mr = re.match(r"^[ÁA]RBITRO\s*:\s*(.*?)(?:\.\s*(?:RECAUDACI|ENTRADAS|CANCHA)|\.?$)", ln, re.I)
        if mr:
            cur["referee"] = mr.group(1).strip()
        me = re.search(r"RECAUDACI[OÓ]N\s*:\s*\$?\s*([\d.,]+)", ln, re.I)
        if me:
            cur["recaud"] = me.group(1)
        mn = re.search(r"ENTRADAS?\s*:?\s*([\d.]+)|\(([\d.]+)\s*entradas\)", ln, re.I)
        if mn and ("ENTRADAS" in up or "entradas" in ln):
            v = mn.group(1) or mn.group(2)
            cur["entradas"] = int(v.replace(".", "")) if v else None
        mc = re.search(r"CANCHA\s*:\s*(.+?)\.?$", ln, re.I)
        if mc:
            cur["cancha"] = mc.group(1).strip()
        # continuación de la línea de jugadores (a veces el listado sigue en la línea siguiente)
        if team_idx >= 0 and not re.match(r"^(AMONESTADOS|EXPULSADOS|ARBITRO|RECAUDACI|ENTRADAS|CANCHA|SUP|DT|D\.T|LIBRE|\d+ ?m)", up) and len(cur["teams"]) <= 2 and not cur["teams"][team_idx]["players"] and "(" not in ln:
            cur["teams"][team_idx]["players"] = split_players(ln)
    return [m for m in matches if len(m["teams"]) == 2]


def main(posts_path, out):
    posts = json.load(open(posts_path, encoding="utf-8"))
    res = []
    for p in posts:
        title = html.unescape(p["title"]["rendered"])
        t = text_of(p["content"]["rendered"])
        if "ARBITRO" not in t.upper() and "ÁRBITRO" not in t.upper():
            continue
        ms = parse_post(title, t)
        for m in ms:
            m["post_id"] = p["id"]
            m["url"] = p["link"]
        res += ms
    json.dump(res, open(out, "w", encoding="utf-8"), ensure_ascii=False)
    print(len(res), "partidos")


if __name__ == "__main__":
    main(*sys.argv[1:3])
