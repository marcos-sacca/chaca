"""Lee el texto de una entrada del blog «Historia y Fútbol» (campeonatos argentinos) y devuelve partidos, goleadores y tablas.

Formato de cada partido en la fuente:
  19/07/1986 en Vicente López: Deportivo Armenio 1 (Rubén E. Gallardo (p)), Chacarita Juniors 1 (Luis E. Sosa)
  Nota: Se jugó en cancha de Platense.
"""
import re

FECHA_RE = re.compile(r"^(\d+)(?:ra|da|er|ta|ma|va|na|mo|vo|º|°)?\.?\s*Fecha\b", re.I)
MATCH_RE = re.compile(r"(\d{2}/\d{2}/\d{4})\s+en\s+")
HEAD = r"(?:Partidos? de (?:Ida|Vuelta)|Partido (?:Único|Desempate)|Octavos de Final|Cuartos de Final|Semifinales?|Finales|Ganador|Clasificados?:|Resultado:|Posiciones|Promedios|Desempate|Llave|(?:1ra|2da|3ra|4ta)\. Fase|(?:1ra|2da)\. Etapa|Zona [A-Z0-9]+|Grupo [A-Z0-9]+)"
SEP = r"(?=(?:Campe[óo]n:|Revalid[óo]|Descendi[óo]|Ascendi[óo]|(?:Primera|Segunda|Tercera|Cuarta) (?:Fase|Etapa|Ronda)|Fase Final)|(?:\d{2}/\d{2}/\d{4}\s*/?\s*\d*\s*en\s)|(?:Nota:)|(?:Libre:)|(?:\d+(?:ra|da|er|ta|ma|va|na|mo|vo|º|°)?\.?\s*Fecha\b)|" + HEAD + ")"


def unwrap(text):
    """Une las líneas cortadas por el procesador de texto original; corrige errores de tipeo frecuentes de la fuente."""
    t = re.sub(r"\s*\n\s*", " ", text)
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"(?<!de )\bFinal (Partidos? de)", r"Finales \1", t)
    t = re.sub(r"(\d{2}/\d{2}/\d{4})\s*(?=en\s)", r"\1 ", t)
    t = re.sub(r"(\d{2}/\d{2}/\d{4}) en([A-ZÁÉÍÓÚ])", r"\1 en \2", t)
    t = re.sub(r"(\d{2}/\d{2}/\d{4}\s+en\s+[^:;.]{2,40})[;.] (?=[A-ZÁÉÍÓÚ])", r"\1: ", t)
    return t


def split_top(s, seps=(",",)):
    """Parte s por las comas que no están dentro de paréntesis."""
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if depth == 0 and ch in seps:
            out.append(cur)
            cur = ""
        else:
            cur += ch
    out.append(cur)
    return [x.strip() for x in out if x.strip()]


def parse_scorers(s):
    """'Leandro Damico, Javier Toledo 2 y Diego Morales (p) e Iván Juárez' -> [{'n','k','pen','ec'}]"""
    res = []
    if not s:
        return res
    parts = []
    for chunk in split_top(s):
        # ' y ' / ' e ' como conectores (fuera de paréntesis)
        depth, cur, i = 0, "", 0
        toks = re.split(r"(\(|\))", chunk)
        buf = ""
        for tk in toks:
            if tk == "(":
                depth += 1
            elif tk == ")":
                depth -= 1
            if depth == 0 and tk not in "()":
                sub = re.split(r"\s+(?:y|e)\s+(?=[A-ZÁÉÍÓÚÑ])", tk)
                buf += sub[0]
                for extra in sub[1:]:
                    parts.append(buf)
                    buf = extra
            else:
                buf += tk
        parts.append(buf)
    for p in parts:
        p = p.strip()
        if not p:
            continue
        ec = bool(re.search(r"\be/c\b|\ben contra\b", p))
        p2 = re.sub(r"\be/c\b|\(en contra\)", "", p).strip()
        pen = 0
        m = re.match(r"^(.*?)\s+(\d+)\s*\((\d+)\s*p\)\s*$", p2)      # 'Nombre 2 (1p)': 2 goles, 1 de penal
        if m:
            name, k, pen = m.group(1).strip(), int(m.group(2)), int(m.group(3))
        else:
            if re.search(r"\(p\)", p2):
                pen = 1
            p2 = re.sub(r"\(p\)", "", p2).strip()
            m = re.match(r"^(.*?)(?:\s+(\d+))?\s*$", p2)
            name, k = m.group(1).strip(), int(m.group(2) or 1)
        res.append({"n": name, "k": k, "pen": pen, "ec": ec})
    return res


def parse_side(s):
    """'Tigre 2 (Adrián Pasceri y Edgardo Paruzzo)' -> (equipo, goles, [goleadores], resto); None si no cuadra.
    «resto» es el texto que sobra después del marcador (a veces la fuente pega acá títulos o aclaraciones)."""
    s = s.strip()
    m = re.match(r"^(.*?)\s+(\d+)\s*(.*)$", s, re.S)
    if not m:
        return None
    team, goals, rest = m.group(1).strip(), int(m.group(2)), m.group(3).strip()
    scorers, tail = [], rest
    if rest.startswith("("):
        depth, end = 0, None
        for i, ch in enumerate(rest):
            depth += ch == "("
            depth -= ch == ")"
            if depth == 0:
                end = i
                break
        if end is None:
            scorers, tail = parse_scorers(rest[1:]), ""
        else:
            scorers, tail = parse_scorers(rest[1:end]), rest[end + 1:].strip()
    return team, goals, scorers, tail


def repair(body):
    """Corrige el paréntesis que falta en algunas líneas de la fuente: 'A 1 (Gómez (p), B 1 (Pérez)'."""
    if body.count("(") <= body.count(")"):
        return body
    depth, out, i = 0, "", 0
    while i < len(body):
        ch = body[i]
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
        if ch == "," and depth > 0 and re.match(r",\s+[A-ZÁÉÍÓÚÑ][^,()]*?\s\d+\s*(?:\(|$)", body[i:]):
            out += ")"
            depth -= 1
        out += ch
        i += 1
    return out


def parse_matches(text, fixes=()):
    """Devuelve (partidos, notas_sueltas). Cada partido: dict(fecha_n, date, city, home, hg, away, ag, hs, as_, notes, raw, pen)."""
    t = unwrap(text)
    for old, new in fixes:
        t = t.replace(old, new)
    # cortar en cabeceras, partidos y notas
    pieces = re.split(SEP, t)
    cur_fecha, matches, loose = None, [], []
    last = None
    stage, leg = None, None
    for p in pieces:
        p = p.strip()
        if not p:
            continue
        mh = re.match(r"(Octavos de Final|Cuartos de Final|Semifinales?|Finales|(?:1ra|2da|3ra|4ta)\. Fase|(?:1ra|2da)\. Etapa|Zona [A-Z0-9]+|Grupo [A-Z0-9]+)", p)
        ml = re.match(r"Partidos? de (Ida|Vuelta)|Partido (Único|Desempate)", p)
        if mh and not MATCH_RE.match(p):
            stage = mh.group(1)
            leg = None
            last = None
            continue
        if ml:
            leg = (ml.group(1) or ml.group(2))
            last = None
            continue
        if re.match(HEAD, p) and not MATCH_RE.match(p) and not FECHA_RE.match(p):
            last = None
            loose.append(p)
            continue
        mf = FECHA_RE.match(p)
        if mf:
            cur_fecha = int(mf.group(1))
            last = None
            continue
        mm = MATCH_RE.match(p)
        if mm:
            date = mm.group(1)
            rest = p[mm.end():]
            city, _, body = rest.partition(":")
            body = repair(body.strip().rstrip("."))
            body = re.sub(r"(\d|\))\s*[.;]\s+(?=[A-ZÁÉÍÓÚÑ])", r"\1, ", body)
            sides = split_top(body)
            pen = None
            # resultado por penales: '(5-4 en penales)' queda como lado extra; se ignora acá
            if len(sides) < 2:
                matches.append({"fecha_n": cur_fecha, "date": date, "city": city.strip(), "raw": p, "error": "lados"})
                last = matches[-1]
                continue
            a, b = parse_side(sides[0]), parse_side(sides[1])
            if a and a[3]:
                a = None  # texto colgado en el primer equipo: la línea está rota
            if not a or not b:
                matches.append({"fecha_n": cur_fecha, "date": date, "city": city.strip(), "raw": p, "error": "marcador"})
                last = matches[-1]
                continue
            extra = " ".join([b[3]] + sides[2:]).strip()
            matches.append({"fecha_n": cur_fecha, "stage": stage, "leg": leg, "date": date, "city": city.strip(), "home": a[0], "hg": a[1], "hs": a[2], "away": b[0], "ag": b[1], "as_": b[2], "notes": [], "extra": extra, "raw": p})
            last = matches[-1]
            continue
        if p.startswith("Nota:") and last is not None:
            last.setdefault("notes", []).append(p[5:].strip())
            continue
        if p.startswith("Libre:"):
            continue
        loose.append(p)
    return matches, loose


def parse_tables(text):
    """Posiciones finales y promedios: {'pos': [(posición, equipo, puntos)], 'prom': [...]}"""
    t = unwrap(text)
    out = {}
    for tag, key in (("Posiciones Finales", "pos"), ("Posiciones", "pos")):
        m = re.search(tag + r"[^:]*:\s*(.*?)(?:\s+Nota:|\s+Promedios|\s+El Torneo|$)", t)
        if m and key not in out:
            out[key] = split_table(m.group(1))
    m = re.search(r"Promedios Descenso[^:]*:\s*(.*?)(?:\s+Nota:|\s+El Torneo|$)", t)
    if m:
        out["prom"] = split_table(m.group(1))
    return out


def split_table(s):
    """'A y B 62; C, D y E 54; F 53 y G 40' -> [(nombres_crudos, valor)] (el orden da la posición; los nombres se separan después)."""
    res = []
    for chunk in re.split(r";\s*|(?<=\d)\s+(?:y|e)\s+(?=[A-ZÁÉÍÓÚÑ])", s.strip().rstrip(".")):
        m = re.match(r"^(.*?)\s+(\d+(?:[.,]\d+)?)(?:\s+puntos?)?\s*$", chunk.strip())
        if m:
            res.append((m.group(1).strip(), float(m.group(2).replace(",", "."))))
    return res


NUM = {"un": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8, "nueve": 9, "diez": 10, "once": 11, "doce": 12, "quince": 15, "dieciocho": 18, "veinte": 20}


def parse_sanciones(text):
    """Descuentos de puntos citados en notas: 'Nota: A Almagro se le descontaron 3 puntos por incidentes...'"""
    t = unwrap(text)
    out = []
    for m in re.finditer(r"(?:Nota:\s*)?A (?:los equipos )?(.+?) se les? (?:descontaron|descontó|restaron|restó)\s+(\w+)\s+puntos?(?:\s+(?:por|en|debido a)\s+([^.]*?))?\s*\.", t):
        n = m.group(2).lower()
        pts = int(n) if n.isdigit() else NUM.get(n)
        if pts:
            out.append({"team": m.group(1).strip(), "pts": pts, "motivo": (m.group(3) or "").strip(), "raw": m.group(0)[:300]})
    return out
