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

## Administración de la galería y pedido de recursos

- `#admin` (link «Admin» al pie) abre un panel para **agregar o sacar** fotos y videos. Los cambios se guardan en el navegador de quien los hace; no hace falta contraseña porque nada se publica solo.
- Para publicarlos: **Exportar para publicar** baja un `extra.json`; se reemplaza `data/extra.json` y se sube al repositorio. Ese archivo se suma a la galería de todos (`fotos`, `videos` y `ocultos` para lo que se saca de la base). Las fotos subidas desde el panel viajan dentro del JSON, achicadas.
- `js/config.js` guarda los mails a los que la gente manda recursos, el link de Cafecito y un segundo link de apoyo (`apoyo.url`, vacío = no se muestra).
- Descensos: no hay lista oficial en la base. Se calculan como «el club jugó la temporada, no ascendió y no figura en la siguiente». Los reducidos salen de `reducidos.csv` (torneos por el ascenso; las promociones y reválidas se cuentan aparte).
