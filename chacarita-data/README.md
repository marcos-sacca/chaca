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
python3 -I tools/build_data.py <DATACHACA.xlsx> data/enrichment/parche_partidos.json data/enrichment/parche_torneos.json data/enrichment/parche_torneos_1960s.json
python3 -I tools/verify_vs_excel.py <DATACHACA.xlsx>      # compara el sitio con las hojas calculadas del Excel
```

Requiere Python 3 con `pandas` y `openpyxl`, y Node 18+ para la verificación.

`verify_vs_excel.py` hoy da **1.731 comprobaciones iguales y 0 diferencias** contra las hojas CHACADATA, DATOS CURIOSOS, RACHAS Y RÉCORDS (incluidas las campañas por temporada con puntos reales), RANKING GOLEADORES, PARTIDOS JUGADOS y EFEMÉRIDES.

## Datos agregados (solo celdas vacías, nunca se pisó un dato)

- `tools/enrich_hl.py`: árbitro, director técnico y espectadores desde los PDF de Historical-Lineups (1932–1984). Solo se agrega en años/décadas donde el mismo método coincide ≥ 90 % con lo que el Excel ya tenía.
- `tools/enrich_positions.py` y `data/enrichment/parche_torneos_1960s.json`: posición final de campeonatos, desde RSSSF.
- Cada dato agregado se ve en el sitio con la marca «agregado» y su fuente.

## Fuera de alcance / pendiente

- 7 partidos con goles pero sin goleador identificado (1959 y 1982) que no se encontraron en ninguna fuente accesible.
- Árbitro, DT y espectadores de 1985 en adelante: no hay una fuente pública accesible desde acá.
- En el Excel, la hoja RANKING GOLEADORES calcula «PJ (con formación)» con `APARICIONES!B2:B1000` (solo 999 de 27.777 filas), por eso muestra 0 para jugadores recientes; el sitio cuenta todas las filas.
