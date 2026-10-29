# chacarita-data

Sitio estático e interactivo con toda la base «DATACHACA Máster»: 3.535 partidos de Chacarita Juniors (1931–2026), goles, formaciones, rachas, récords, canchas y efemérides.

Sin framework ni paso de compilación del sitio: HTML + CSS + módulos ES nativos, gráficos en SVG hechos a mano y fuentes alojadas en el propio sitio (Archivo e Inter, licencia OFL). Se publica tal cual en cualquier hosting estático (Cloudflare Pages, GitHub Pages, Netlify…): la carpeta `chacarita-data/` es la raíz.

## Probarlo en local

```
cd chacarita-data
python3 -m http.server 8000     # y abrir http://localhost:8000
```

(No se puede abrir `index.html` con doble clic: el navegador bloquea `fetch` de los JSON desde `file://`.)

## Estructura

| Carpeta | Contenido |
|---|---|
| `index.html`, `css/`, `js/` | El sitio. `js/store.js` tiene todos los cálculos; `js/views/` una vista por sección. |
| `data/*.json` | Datos generados desde el Excel (no se editan a mano). |
| `data/enrichment/` | Datos completados desde fuentes públicas y `parche_datos.csv` con **cada celda agregada y su fuente**. |
| `assets/img/` | Fotos (Wikimedia Commons) y `credits.json` con autor, licencia y enlace de cada una. `camiseta.svg` es ilustración propia. |
| `tools/` | Scripts para regenerar y verificar los datos. |

## Actualizar los datos cuando cambie el Excel

```
python3 -I tools/build_data.py <DATACHACA.xlsx> data/enrichment/parche_*.json   # todos los parches, en este orden de prioridad: Historical-Lineups, Chacarita Digital, Transfermarkt, rivales, Solo Ascenso, Infobae
python3 -I tools/verify_vs_excel.py <DATACHACA.xlsx>      # compara el sitio con las hojas calculadas del Excel
```

Requiere Python 3 con `pandas` y `openpyxl`, y Node 18+ para la verificación.

`verify_vs_excel.py` hoy da **1.731 comprobaciones iguales y 0 diferencias** contra las hojas CHACADATA, DATOS CURIOSOS, RACHAS Y RÉCORDS (incluidas las campañas por temporada con puntos reales), RANKING GOLEADORES, PARTIDOS JUGADOS y EFEMÉRIDES.

## Datos agregados (solo celdas vacías, nunca se pisó un dato)

| Fuente | Script | Qué aporta |
|---|---|---|
| Historical-Lineups (PDF 1932–1984) | `enrich_hl.py` | árbitro, DT, espectadores, formaciones de Primera |
| Chacarita Digital (144 notas) | `scrape_cd.py`, `parse_cd.py`, `enrich_cd.py` | árbitro, DT, espectadores, cancha y formaciones; coincide 99 % (árbitro) y 96 % (DT) con lo ya cargado |
| Transfermarkt | `scrape_tm.py`, `enrich_tm.py` | árbitro, DT, espectadores y formaciones desde 1995 |
| Museo Granate, La Historia River, El Sitio de Almagro | `scrape_museogranate.py`, `scrape_lahistoriariver.py`, `scrape_almagro.py`, `enrich_rivals.py` | árbitro y DT de los partidos contra esos rivales (coincide 99,5 %) |
| Solo Ascenso (carpeta `ascenso/`) | `enrich_sa.py` | control de árbitro, DT y goleadores desde 2013; aporta lo que falte |
| Infobae (2004–2008) | `scrape_infobae.py`, `enrich_infobae.py` | árbitro y DT de crónicas con «Síntesis» |
| Crónicas de Historia y Fútbol | `enrich_jc.py` | nombres de goles en contra (54) y 234 diferencias de goleadores para revisar |
| RSSSF | `enrich_positions.py` | posición final de campeonatos |

Cada dato agregado se ve en el sitio con la marca «agregado» y su fuente (`data/enrichment_index.json`).

**Listas para revisar a mano** (la planilla y la fuente no coinciden; no se tocó nada):
`data/enrichment/revisar_arbitro_dt_planilla_vs_fuentes.csv` (44), `revisar_goleadores_planilla_vs_solo_ascenso.csv` (7), `hallazgos_goleadores_planilla_vs_cronica.csv` (234) y `revisar_partidos_solo_ascenso_sin_par_en_planilla.csv` (29 partidos de Solo Ascenso sin par en la planilla, entre ellos un posible partido faltante: Chacarita 1-0 Gimnasia de Jujuy, 18/11/2018).

## Qué sigue faltando

Sobre 3.535 partidos: sin árbitro 1.080, sin DT 1.888, sin espectadores 2.892, sin formación 1.092.
Se concentra en 1980–83, 1986/87 a 1998/99 (toda la B Nacional y la Primera B de esa época), 2004/05 a 2007/08, 2012/13–2013/14 y, en espectadores, casi todo.

- 7 partidos con goles pero sin goleador identificado (1959 y 1982) que no se encontraron en ninguna fuente accesible.
- Fuentes que bloquean el acceso: SofaScore, fbref, worldfootball/ceroacero, mundoascenso y el sitio oficial del club (Vercel).
- En el Excel, la hoja RANKING GOLEADORES calcula «PJ (con formación)» con `APARICIONES!B2:B1000` (solo 999 de 27.777 filas), por eso muestra 0 para jugadores recientes; el sitio cuenta todas las filas.
