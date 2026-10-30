"""Resuelve nombres de equipos de fuentes externas (RSSSF, Transfermarkt) a los nombres canónicos de clubes.py."""
import re
import unicodedata
from clubes import R, nkk

EXP = [(r"\bAlte\.?", "Almirante"), (r"\bAt\.?(?=\s)", "Atlético"), (r"\bAtl\.?(?=\s)", "Atlético"), (r"\bDep\.?(?=\s)", "Deportivo"), (r"\bDepor\.?(?=\s)", "Deportivo"), (r"\bInd\.?(?=\s)", "Independiente"),
       (r"\bGim\.?(?=\s)", "Gimnasia"), (r"\bGimn\.?(?=\s)", "Gimnasia"), (r"\bSp\.?(?=\s)", "Sportivo"), (r"\bSport\.?(?=\s)", "Sportivo"), (r"\bCent\.?(?=\s)", "Central"), (r"\bDef\.?(?=\s)", "Defensores"),
       (r"\bArg\.?(?=\s)", "Argentino"), (r"\bJrs\.?", "Juniors"), (r"\bSgo\.?\s*(del)?\s*Estero", "Santiago del Estero"), (r"\bSdE\b", "Santiago del Estero"), (r"\bCba\.", "Córdoba"), (r"\bMza\.", "Mendoza"),
       (r"\bCtes\.", "Corrientes"), (r"\bSta\.?\s*Fe", "Santa Fe"), (r"\bTuc\.", "Tucumán"), (r"\bR\.\s*Negro", "Río Negro"), (r"\bRdE\b", "Remedios de Escalada"), (r"\bC\.A\.I\.?", "Comisión de Actividades Infantiles"),
       (r"\bCAI\b", "Comisión de Actividades Infantiles"), (r"\bBs\.?\s*As\.?", "Buenos Aires"), (r"\bRC\b", "Río Cuarto"), (r"\bGral\.\s*", "General "), (r"\bF\.?C\.?\s?Oeste", "Ferro Carril Oeste"), (r"\bFerro C\.O\.", "Ferro Carril Oeste"), (r"\bJuv\.", "Juventud"), (r"\bJ\.\s", "Juventud "), (r"\bMdP\b", "Mar del Plata"), (r"\bTA\b", "Tres Arroyos"), (r"\bBA\b", "Buenos Aires"), (r"\bRN\b", "Río Negro"), (r"\bER\b", "Entre Ríos"), (r"\bCU\b", "Concepción del Uruguay"), (r"\bMis\.", "Misiones"), (r"Talleres \(R\.\s?E\.?\)", "Talleres de Remedios de Escalada")]
STOP = {"de", "del", "la", "el", "club", "ca", "csd", "cd", "fc", "ac", "atletico", "social", "y", "deportivo", "sportivo", "juniors", "athletic"}


def clean(name):
    n = name
    for a, b in EXP:
        n = re.sub(a, b, n)
    n = re.sub(r"\s+", " ", n).strip()
    return n


def toks(s):
    return {t for t in nkk(s).split() if t not in STOP and len(t) > 1}


def canon_set():
    return {v[0]: v for v in R.values()}


class ExtResolver:
    def __init__(self, extra=None, alias=None):
        self.canon = canon_set()
        for n, v in (extra or {}).items():
            self.canon[n] = v
        self.alias = {nkk(k): v for k, v in (alias or {}).items()}
        self.cache = {}

    def __call__(self, name, hint=None):
        k = nkk(name)
        if k in self.alias:
            return self.alias[k]
        if k in self.cache:
            return self.cache[k]
        c = clean(name)
        ck = nkk(c)
        best = []
        for canon, v in self.canon.items():
            cc = nkk(canon)
            if cc == ck or nkk(v[1]) == ck:
                best = [(9, canon)]
                break
            a, b = toks(c), toks(canon) | toks(v[1])
            if not a:
                continue
            j = len(a & b) / len(a | b)
            full = len(a & toks(canon)) / max(len(a), 1)
            best.append((j + 0.2 * full, canon))
        best.sort(reverse=True)
        res = None
        if best and best[0][0] >= 0.99 or (best and (best[0][0] >= 0.6) and (len(best) == 1 or best[0][0] - best[1][0] >= 0.2)):
            res = best[0][1]
        self.cache[k] = res
        return res


def best_among(name, cands):
    """Elige, entre los equipos de esa temporada (cands), el que mejor coincide con el nombre externo. -> (canónico, puntaje)"""
    al = alias_lookup(name)
    if al and al in cands:
        return al, 10
    c = clean(name)
    a = toks(c)
    ck = nkk(c)
    scored = []
    for canon in cands:
        v = R_BY_CANON.get(canon)
        names = {canon} | ({v[1]} if v else set())
        if ck in {nkk(n) for n in names}:
            return canon, 9
        b = set().union(*[toks(n) for n in names])
        if not a or not b:
            continue
        j = len(a & b) / len(a | b)
        cover = len(a & b) / len(a)
        scored.append((j * 0.6 + cover * 0.4, canon))
    scored.sort(reverse=True)
    if scored and scored[0][0] >= 0.5 and (len(scored) == 1 or scored[0][0] - scored[1][0] >= 0.12):
        return scored[0][1], scored[0][0]
    return None, (scored[0][0] if scored else 0)


R_BY_CANON = {v[0]: v for v in R.values()}


ALIAS_EXT = {
    "colon sta fe": "Colón", "colon santa fe": "Colón", "colon sta fe": "Colón",
    "alte brown arrecifes": "Almirante Brown de Arrecifes", "alte brown arr": "Almirante Brown de Arrecifes", "almirante brown arr": "Almirante Brown de Arrecifes", "almirante brown arrecifes": "Almirante Brown de Arrecifes",
    "brown arr": "Almirante Brown de Arrecifes", "brown arrecifes": "Almirante Brown de Arrecifes", "a brown": "Almirante Brown", "alte brown": "Almirante Brown", "brown a": "Brown de Adrogué", "brown adrogue": "Brown de Adrogué",
    "instituto acc": "Instituto de Córdoba", "instituto cba": "Instituto de Córdoba", "instituto cordoba": "Instituto de Córdoba", "intituto cba": "Instituto de Córdoba", "instituto cordoaba": "Instituto de Córdoba",
    "estudiantes sl": "Sportivo Estudiantes de San Luis", "talleres re": "Talleres de Remedios de Escalada", "union san juan": "Unión de Villa Krause", "union villa krause": "Unión de Villa Krause",
    "racing cba": "Racing de Córdoba", "racing c": "Racing de Córdoba", "racing": "Racing de Córdoba", "racing club": "Racing de Córdoba",
    "huracan ba": "Huracán", "huracan buenos aires": "Huracán", "huracan ta": "Huracán de Tres Arroyos", "huracan tres arroyos": "Huracán de Tres Arroyos", "huracan corrientes": "Huracán Corrientes", "huracan ctes": "Huracán Corrientes",
    "gimnasia er": "Gimnasia y Esgrima de Concepción del Uruguay", "gimnasia entre rios": "Gimnasia y Esgrima de Concepción del Uruguay", "gimnasia cu": "Gimnasia y Esgrima de Concepción del Uruguay", "gimnasia y esgrima cu": "Gimnasia y Esgrima de Concepción del Uruguay",
    "gimnasia j": "Gimnasia y Esgrima de Jujuy", "gimnasia juj": "Gimnasia y Esgrima de Jujuy", "gimnasia y esgrima j": "Gimnasia y Esgrima de Jujuy", "gimnasia y esgrima jujuy": "Gimnasia y Esgrima de Jujuy", "gimnasia jujuy": "Gimnasia y Esgrima de Jujuy",
    "gimnasia m": "Gimnasia y Esgrima de Mendoza", "gimnasia y esgrima m": "Gimnasia y Esgrima de Mendoza", "gimnasia y t": "Gimnasia y Tiro de Salta", "gimnasia y tiro": "Gimnasia y Tiro de Salta",
    "gimnasia lp": "Gimnasia y Esgrima La Plata", "san martin m": "San Martín de Mendoza", "san martin mendoza": "San Martín de Mendoza", "san martin tucuman": "San Martín de Tucumán", "san martin t": "San Martín de Tucumán",
    "san martin sj": "San Martín de San Juan", "san martin san juan": "San Martín de San Juan", "c cordoba ros": "Central Córdoba de Rosario", "c cordoba r": "Central Córdoba de Rosario", "central cordoba ros": "Central Córdoba de Rosario", "central cordoba r": "Central Córdoba de Rosario",
    "c cordoba sde": "Central Córdoba de Santiago del Estero", "central cordoba sde": "Central Córdoba de Santiago del Estero", "c cordoba": "Central Córdoba de Santiago del Estero",
    "f c oeste gral pico": "Ferro Carril Oeste de General Pico", "ferro c o": "Ferro Carril Oeste", "aldosivi mdp": "Aldosivi de Mar del Plata", "cipolletti rn": "Cipolletti de Río Negro", "cipolletti rio negro": "Cipolletti de Río Negro", "cipolleti rio negro": "Cipolletti de Río Negro",
    "com de act infantiles": "Comisión de Actividades Infantiles", "c de act infantiles": "Comisión de Actividades Infantiles", "cai": "Comisión de Actividades Infantiles",
    "guarani a f mis": "Guaraní Antonio Franco de Posadas", "guarani a franco mis": "Guaraní Antonio Franco de Posadas", "guarani antonio franco": "Guaraní Antonio Franco de Posadas", "guarani": "Guaraní Antonio Franco de Posadas",
    "desamparados": "Sportivo Desamparados de San Juan", "sportivo desamparados": "Sportivo Desamparados de San Juan", "j antoniana": "Juventud Antoniana de Salta", "juv antoniana": "Juventud Antoniana de Salta", "juventud antoniana": "Juventud Antoniana de Salta", "antoniana": "Juventud Antoniana de Salta",
    "indep rivadavia": "Independiente Rivadavia de Mendoza", "i rivadavia": "Independiente Rivadavia de Mendoza", "rivadavia": "Independiente Rivadavia de Mendoza", "independiente rivadavia": "Independiente Rivadavia de Mendoza",
    "argentino r": "Argentino de Rosario", "argentino rosario": "Argentino de Rosario", "gral paz juniors": "General Paz Juniors", "godoy cruz mza": "Godoy Cruz Antonio Tomba", "godoy cruz mendoza": "Godoy Cruz Antonio Tomba", "godoy cruz": "Godoy Cruz Antonio Tomba",
    "atletico tucuman": "Atlético Tucumán", "atl tucuman": "Atlético Tucumán", "atletico tucuman tucuman": "Atlético Tucumán", "atletico rafaela": "Atlético de Rafaela", "atletico de rafaela": "Atlético de Rafaela",
    "atletico concepcion": "Atlético Concepción de Tucumán", "atletico concepcion tucuman": "Atlético Concepción de Tucumán", "atl concepcion": "Atlético Concepción de Tucumán", "olimpo bb": "Olimpo de Bahía Blanca", "olimpo": "Olimpo de Bahía Blanca",
    "unioan sf": "Unión de Santa Fe", "union sf": "Unión de Santa Fe", "union santa fe": "Unión de Santa Fe", "union": "Unión de Santa Fe", "union juj": "Unión de Santa Fe", "dep mandiyu ctes": "Deportivo Mandiyú de Corrientes", "dep maipu mza": "Deportivo Maipú de Mendoza",
    "defensa y justicia": "Defensa y Justicia", "def y justicia": "Defensa y Justicia", "guillermo brown": "Guillermo Brown de Puerto Madryn", "godoy cuz": "Godoy Cruz Antonio Tomba", "brown": "Brown de Adrogué", "estudiantes": "Estudiantes de Buenos Aires",
    "talleres cordoba": "Talleres de Córdoba", "talleres cba": "Talleres de Córdoba", "talleres": "Talleres de Córdoba", "sarmiento": "Sarmiento de Junín", "sarmiento j": "Sarmiento de Junín", "sarmiento junin": "Sarmiento de Junín", "tiro federal": "Tiro Federal de Rosario",
    "barracas c": "Barracas Central", "ca alvarado": "Alvarado de Mar del Plata", "alvarado": "Alvarado de Mar del Plata", "cadu zarate": "Defensores Unidos de Zárate", "ciudad bolivar": "Ciudad de Bolívar", "dep riestra": "Deportivo Riestra",
    "estudiantes rc": "Estudiantes de Río Cuarto", "midland": "Ferrocarril Midland", "ferrocarril midland": "Ferrocarril Midland", "atlanta": "Atlanta", "dep madryn": "Deportivo Madryn",
    "dock sud": "Sportivo Dock Sud", "def unidos": "Defensores Unidos", "estudiantes bs as": "Estudiantes de Buenos Aires", "estudiantes ba": "Estudiantes de Buenos Aires", "estudiantes bsas": "Estudiantes de Buenos Aires",
}


def alias_lookup(name):
    k = nkk(re.sub(r"\bCA\b|\bC\.A\.\s*", "", clean(name)))
    return ALIAS_EXT.get(k) or ALIAS_EXT.get(nkk(name))
