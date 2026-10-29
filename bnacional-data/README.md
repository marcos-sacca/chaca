# B Nacional Histórica

Sitio estático (HTML + CSS + módulos ES, sin framework) con los partidos, tablas, goleadores y ascensos de la Primera B Nacional y la Primera Nacional desde 1986/87, más fotos y videos de la categoría.

| Carpeta | Qué hay |
|---|---|
| `index.html`, `css/`, `js/` | El sitio. Las direcciones usan `#nombre` (por ejemplo `#t-1996-97`, `#c-banfield`). |
| `data/` | JSON que lee el sitio. Se generan con `tools/build_data.py` a partir de `../bnacional/data/*.csv`. |
| `assets/img/ascensos/` | Fotos de clubes y partidos (Wikimedia Commons, achicadas). Cada una con autor y licencia en `data/fotos.json`. |
| `assets/img/videos/` | Miniaturas de los videos (los videos se ven en YouTube). |
| `tools/` | `build_data.py` (datos), `fetch_photos2.py` + `pick_photos.py` (fotos), `make_artifact.py` (página única para publicar como Artifact). |

## Regenerar

```
python3 -I bnacional/tools/run.py                 # tablas, partidos y goleadores
python3 -I bnacional-data/tools/build_data.py     # JSON del sitio
python3 -m http.server -d bnacional-data 8000     # verlo en http://localhost:8000
```

Las fotos se buscan sin usar la API de Commons (que limita los pedidos): `fetch_photos2.py` lee el artículo de Wikipedia de cada club y su categoría de Commons, y `pick_photos.py` elige una foto por club y, cuando el nombre del archivo trae el año, una por temporada. Solo se aceptan archivos con licencia libre declarada.

## Qué foto es cada una

Una tarjeta muestra la foto de **la temporada** si Commons tiene un archivo con ese año en el nombre; si no, una foto **del club** (estadio, plantel o hinchada); si tampoco hay, el club aparece con sus iniciales. La ventana de cada foto lo aclara.
