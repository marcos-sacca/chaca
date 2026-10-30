# Guía del proyecto (para Claude Code)

Leé esto entero antes de tocar nada. Es el traspaso completo de una sesión larga en la nube: qué hay, cómo se corre, qué se decidió, qué falta.
Idioma: **español rioplatense** (voseo) en todo lo que ve el público y en commits, README y notas.

## 1. Qué es este repositorio

Proyecto de hinchas de datos de fútbol del ascenso argentino. Cuatro piezas:

| Carpeta | Qué es | Estado |
|---|---|---|
| `bnacional/` | **Base histórica de la B Nacional / Primera Nacional (1986/87 → hoy)**: scripts que arman CSV y Excel desde crónicas, RSSSF, Transfermarkt y Solo Ascenso. | Hecha y controlada. Ver §4. |
| `bnacional-data/` | **Sitio estático «B Nacional Histórica»** (el proyecto principal hoy). Se publica en **Cloudflare Pages**. | En producción; sigue creciendo. Ver §3 y §5. |
| `chacarita-data/` | Sitio estático con los 3.535 partidos de Chacarita Juniors (1931–2026) + scripts de enriquecimiento de datos. | Completo; faltan datos en fuentes cerradas. Ver §8. |
| `ascenso/` | Scraper y datos normalizados de **Solo Ascenso** (24.091 síntesis de partidos, desde 2014). Lo usan los otros dos proyectos. | Hecho. |
| `scripts/`, `data/`, `*.html` de la raíz, `video/`, `setup-pc/` | Análisis de Chacarita 2026 (modelo de descenso, informes), video «fecha por fecha» y prompts de instalación. | Aparte; no hace falta para el sitio. |

Personas: **Marcos Sacca** (dueño del repo, `marcos-sacca`) y **Nico** (`sorren96`, trabaja con su propio Claude). Los mails de contacto del sitio están en `bnacional-data/js/config.js`.

## 2. Ramas y despliegue

- Rama de trabajo del sitio: **`claude/hallazgos-datos-bnacional`**. `main` todavía **no tiene** `bnacional-data/` (39+ commits de diferencia). Antes de tocar ramas, preguntale a Marcos si Cloudflare mira `main` o la rama de trabajo; la idea acordada es **mergear a `main`** y dejar `main` como rama de producción.
- Cloudflare Pages (cuenta de Marcos): proyecto conectado al repo, **sin comando de compilación**, **directorio de salida `bnacional-data`**. Cada push a la rama de producción publica solo. Detalles y alternativas en `bnacional-data/DEPLOY.md` y `bnacional-data/PROMPT_CLAUDE_LOCAL.md`.
- Ya **no se usa el Artifact de claude.ai** (`make_artifact.py` queda obsoleto pero funciona). No hace falta embeber imágenes ni datos: el sitio sirve archivos normales.
- Regla de colaboración acordada: **arreglos chicos del sitio** (CSS, textos, un bug de pantalla) se pueden pushear directo; **todo lo que toque `bnacional/data/*.csv`, `consistencia.py` o regenere datos va por pull request**, para revisarlo.
- Nunca guardes tokens, contraseñas ni claves en el repo ni en commits. Si hace falta un token de Cloudflare, va en variable de entorno (`CLOUDFLARE_API_TOKEN`, `CLOUDFLARE_ACCOUNT_ID`) y se borra al terminar.
- Antes de cualquier cosa que no se pueda deshacer (merge a `main`, borrar ramas, force push, borrar proyectos de Cloudflare, publicar algo nuevo): **preguntá**.

## 3. Cómo correr todo

```bash
# datos de la B Nacional (usa bnacional/cache; no está en Git, ver §4 "Reproducibilidad")
python3 -I bnacional/tools/run.py                  # crónicas + cruces + consistencia.py + Excel  (~1,5 min)
python3 -I bnacional-data/tools/build_data.py      # JSON del sitio en bnacional-data/data/
python3 -m http.server -d bnacional-data 8000      # http://localhost:8000
# prueba de humo del sitio (23 rutas, claro/oscuro, escritorio/celular):
npm i playwright && npx playwright install chromium     # una vez
node bnacional-data/tools/smoke_test.mjs [carpeta_capturas]
```

- En Windows usá `python` en vez de `python3` y PowerShell (un comando por línea, sin `&&`).
- Siempre `python -I` en los scripts que leen archivos descargados.
- **Antes de cada push al sitio corré `smoke_test.mjs`**: tiene que decir «Sin errores en 23 rutas».
- No se puede abrir `index.html` con doble clic (el navegador bloquea `fetch` desde `file://`): usá el servidor local.

## 4. Datos de la B Nacional (`bnacional/`)

**Cifras actuales:** 42 temporadas, 112 clubes, **18.823 partidos**, **42.913 goles**, 97 ascensos, 584 partidos de reducidos/promociones/desempates (`reducidos.csv`).

**Fuentes** (todas públicas): crónicas de *Historia y Fútbol* (José Carluccio, 1986/87–2018/19, fuente principal), RSSSF (control), Transfermarkt (control, 2008+), **Solo Ascenso** (2014+, y principal desde 2017/18), Wikipedia (lista de ascensos y campeones, `bnacional/data/fuentes/wikipedia_primera_b_nacional.wiki`).

**Pipeline** (`bnacional/tools/run.py`): `bn_build.py` (lee crónicas) → `bn_export.py` (CSV) → `crosscheck.py` (cruza con RSSSF/TM/SA, tabla por tabla) → **`consistencia.py`** (corrige y deja registro) → `xlsx_make.py` (Excel `bnacional/data/B_Nacional_historico.xlsx`, 15 hojas).

**`consistencia.py`** (agregado por Nico, 585 cambios, cada uno en `correcciones_consistencia.csv`): orden de temporadas, clubes mal asignados (Talleres R.E vs Córdoba, Independiente vs Independiente Rivadavia, Unión MdP vs Santa Fe…), reducidos/finales/desempates que estaban en fase regular, interzonales 1996/97, partidos faltantes/repetidos (RSSSF, TM, SA), 241 jugadores unificados. Solo corrige si la fase queda pareja y no empeora una tabla que ya cerraba. Control contra las tablas publicadas: **130 → 87 casos «Revisar»**. Lo que queda: **161 casos en `pendientes_consistencia.csv`** (74 posibles duplicados de jugadores con apellido común, 47 fases/temporadas con partidos desparejos —sobre todo 1995–2008 y 2018/19—, 40 explicados por el formato o revisados a mano).

**Verificado a mano contra fuentes (10 correcciones al azar):** todas coinciden. Rarezas conocidas: 19 partidos agregados desde RSSSF tienen **fecha aproximada** (marcada en `Observaciones`; ej. varios de Argentinos Jrs. el 22/10/1997); el PR de Nico decía 621 reducidos y son 584; los **descensos no existen en la base**: el sitio los *calcula* («el club jugó la temporada, no ascendió y no figura en la siguiente»), y lo aclara en pantalla.

**⚠ Reproducibilidad (tarea abierta, importante):** `bnacional/cache/` y `bnacional/data/_crudo.json` están en `.gitignore`. Correr `run.py` **desde cero** con el caché da un resultado **distinto** a lo commiteado: 7 partidos de 18.823 (1991/92–1998/99) se resuelven de otra manera y quedan 89 «Revisar» en vez de 87, porque las reglas se fueron sumando de a una y el orden importa. Sobre los CSV ya commiteados, `consistencia.py` es **determinista e idempotente** (segunda pasada: «0 cambios nuevos, 161 pendientes», sin diferencias de archivos). Mientras no se arregle: **los CSV commiteados son la fuente de verdad; no los regeneres desde cero ni pises con una corrida nueva**. Para arreglarlo: hacer que las reglas converjan al mismo estado sin importar el orden (y comparar con los 7 partidos en disputa, que RSSSF 1992/93 respalda en la versión commiteada), y subir `bnacional/cache` (~2 MB) al repo para que otros puedan regenerar.

**Pendientes de datos, en orden sugerido:**
1. Volver reproducible `run.py` (arriba).
2. Cerrar los 161 pendientes: primero los duplicados de jugadores con más goles (verificar en Wikipedia/Transfermarkt; los dudosos van a `NO_UNIFICAR`), después las fases desparejas contra RSSSF/Wikipedia, y anotar el motivo de cada decisión.
3. Las **promociones contra equipos de Primera División** no están (las crónicas son de la B Nacional). Acordado: **hacerlo en otra rama**, desde RSSSF u otra fuente, como archivo aparte (`promociones.csv`) sin tocar lo corregido.
4. Fechas reales de los 14 partidos con fecha aproximada (observación «fecha aproximada»; de los 19 agregados por consistencia, 5 tienen fecha de fuente), si aparece una fuente. El sitio ya no muestra esa fecha (`mdate()` en `util.js`; `build_data.py` marca el partido con un 9.º valor en `matches.json`).

## 5. Sitio `bnacional-data/`

HTML + CSS + módulos ES nativos, **sin framework ni build**. Fuentes Archivo (variable, ancho 62–125) e Inter, licencia OFL, alojadas en `assets/fonts`.

**Estructura:** `index.html` (menú, `#app`, pie, diálogos `#lightbox` y `#finder`), `css/main.css` (todo el estilo; tokens en `:root`), `js/app.js` (router por hash, menú, buscador, progreso), `js/store.js` (carga de JSON y cálculos derivados: `S.teamBy`, `S.mByTeam`, `S.cs` = ascensos/descensos/reducidos por club, recursos de la galería), `js/util.js` (`h()` para crear DOM, `n`, `norm`, `fdate`, `imgSrc`), `js/views/*.js` (una vista por sección), `js/race.js`, `js/charts.js`, `js/config.js`.

**Rutas** (`#nombre` o `#nombre-argumento`): `inicio`, `ascensos`, `temporadas`, `t-<temporada>` (ej. `t-1996-97`, `t-transicion-2014`), `clubes`, `c-<slug>`, `tabla`, `reducidos`, `historial` y `historial-<slug>_vs_<slug>`, `clasicos`, `goleadores`, `juegos` (+ `jugador`, `grilla`, `contrarreloj`, `masgoles`), `carrera`, `fotos`, `videos`, `datos`, `admin`. Para agregar una vista: archivo en `js/views/`, `route("nombre", fn)` y sumarlo a la lista de `import()` de `app.js` y al mapa `key` del menú.

**Datos** (`bnacional-data/data/*.json`, no se editan a mano salvo los marcados): `build_data.py` genera `meta, teams, seasons, phases, players, matches, scorers, general` desde `bnacional/data/*.csv`. Otros archivos tienen su propio script o se editan a mano: `crests.json` (escudos), `fotos.json` + `galeria.json` (fotos), `videos.json` (a mano), `planteles.json` (`build_planteles.py`), `titulares.json` (partidos de titular, de Nico), **`extra.json`** (recursos del panel admin), **`clasicos.json`** (a mano), **`historial_completo.json`** (a mano: historial de todos los tiempos de 8 clásicos, de Wikipedia, con fuente y fecha de corte; `historial.js` lo muestra arriba y deja los datos de la B Nacional abajo; las cifras son de la fuente, con sus inconsistencias anotadas). Los **juegos** tienen filtros de época (10 años) y club favorito solo en la práctica libre (`juegos.js`: `ERAS`, `fil`, `filterBar`); el desafío del día no los usa, para que sea igual para todos, y la contrarreloj solo filtra por club porque las formaciones son desde 2014.

**Decisiones de diseño tomadas por Marcos (no las cambies sin preguntar):**
- Estética **sobria**, azules oscuros (navy `#0b2447`, `#123a6b`, `#1b4f8f`, celeste `#5fb4e6`), tipografía de `chacarita-data`. Nada de «juego» ni de «tecnológico». La interactividad y las animaciones **le encantan**: mantenelas.
- **«Los que subieron» (ascensos, temporadas, clubes, portada): SIEMPRE el escudo como carátula, jamás una foto.** Las fotos viven **solo en la Galería** (y en la sección «Fotos» de la ficha de cada club). Si falta el escudo, monograma con iniciales.
- Portada «Todos los ascendidos»: campeón destacado, resto como complemento, y **desplegable si son muchos** (Transición 2014: 10 ascendidos, sin campeón).
- Galería: fotos **agrupadas por club**; videos agrupados por tipo (compilados de goles, finales —por club—, partidos).
- La **tabla histórica** cuenta por defecto **solo fase regular**, con casilla para sumar reducidos.
- Modo oscuro: se resuelve **con tokens** (`--deep`, etc.) bajo `prefers-color-scheme` y `[data-theme]`; no escribas selectores sueltos de sobreescritura (en una ocasión aplicaron en modo claro).
- No uses animaciones que dejen el contenido en `opacity: 0` hasta hacer scroll (rompen capturas): la entrada es `animation: up` visible en reposo.
- `h()` aplana arrays anidados y soporta `style` con propiedades `--custom`.

**Gotchas ya vividos:** `parse()` del router solo acepta `^([a-z]+)(?:-(.+))?$`; si agregás columnas a `S.general`, las usa `tabla.js` por índice (13 asc., 14 desc., 15 red.); las vistas nuevas se cargan por `import()` dinámico y un error de sintaxis deja el sitio con «No se pudieron cargar los datos» (el mensaje real está en consola); al editar `store.js` la lista de JSON cargados es una sola línea larga (agregar el nombre en **dos** lugares: la lista y la desestructuración).

**Secciones de Nico:** historiales cara a cara (`historial.js`, exporta `h2hMatches`, `h2hSummary`, `rivalsOf`, `hrefH2H`), reducidos con qué estaba en juego y quién pasó (`reducidos.js`), cuatro juegos con desafío del día y resultado para compartir (`juegos.js`, estado en `localStorage`, el día cambia a medianoche de Argentina).

**Clásicos (`clasicos.js` + `data/clasicos.json`):** página con «Armá tu cruce» (dos selects, resumen G-E-P, guardar en «Mis cruces» en `localStorage`) y una tarjeta por club. **Solo 16 cruces (32 clubes) están cargados a mano, de memoria, sin verificar** (Banfield–Lanús, Estudiantes–Gimnasia LP, Colón–Unión, Rafaela–Ben Hur, Belgrano–Talleres, San Martín T–Atlético Tucumán, San Martín SJ–Desamparados, Godoy Cruz–Indep. Rivadavia, Patronato–Atlético Paraná, Central Córdoba SdE–Mitre, Crucero–Guaraní, Madryn–Guillermo Brown, Olimpo–Villa Mitre, Aldosivi–Alvarado, Gimnasia y Tiro–Juventud Antoniana, Chacarita–Atlanta). Los otros 80 clubes muestran el **rival más enfrentado** (de su zona si hay), marcado como tal para no hacerlo pasar por clásico. **Tarea:** revisar los 16 con una fuente y completar el resto con Marcos (formato: `["slug","slug","Nombre del clásico"]`).

## 6. Escudos, fotos, videos y planteles

- **Escudos:** 112 de 112. Fuentes: TheSportsDB (API gratuita, clave de prueba `123`, `fetch_crests_tsdb.py`) y Wikipedia/Wikidata (`fetch_crests.py`, `fetch_crests_html.py`), unidos por `merge_crests.py` (prefiere TheSportsDB). Cuatro clubes salieron mal por homónimos y se corrigieron a mano; 5 (Deportivo Italiano, Estación Quequén, Racing de Nueva Italia, Sacachispas, Tiro Federal) los pasó Marcos. **Racing de Nueva Italia usa el escudo de Racing de Córdoba** (y en los datos siguen como dos clubes) y **Deportivo Italiano usa el de Sportivo Italiano**: si se confirma que son otro club, buscar sus escudos. Son marcas de cada club, mostradas solo para identificarlos (está dicho en «Datos»). Archivos en `assets/img/crests/`, procedencia en `crests.json`; fuentes crudas en `data/fuentes/`.
- **Fotos:** 90 fotos de 55 clubes, de Wikimedia Commons con licencia libre verificada (CC BY, BY-SA, CC0, dominio público; se rechazó todo lo no libre). **57 clubes todavía no tienen fotos** (la Galería los lista con un mail pre-armado para pedirlas). Scripts: `fetch_photos2.py` (baja candidatos sin usar la API), `pick_photos.py` (filtro de relevancia: rugby y retratos se descartaron), `group_fotos.py` (arma `galeria.json`). **Wikimedia limita los pedidos (HTTP 429)**: la API `api.php` no sirve; se usa `index.php?action=raw`, páginas de categoría, miniaturas de `upload.wikimedia.org` en tamaños estándar (500/960) y ≥1,6 s entre pedidos, con reintentos.
- **Videos:** 25 en `videos.json` (compilados de goles, finales, partidos), con miniatura local en `assets/img/videos/<id>.jpg`; abren YouTube en pestaña nueva. Se editan a mano o desde `#admin`.
- **Planteles:** 31 ascensos, **desde 2014** (formaciones de Solo Ascenso: titulares y suplentes que entraron, PJ, goles, DT). Antes de 2014 no hay formaciones: se muestran los goleadores del club esa temporada. **No se muestran edades** (Solo Ascenso da la edad *actual*). Script: `build_planteles.py`.

## 7. Panel de administración y configuración (`#admin`, `js/config.js`)

- `#admin` (link «Admin» en el pie): agregar/sacar **fotos** (archivo, que se achica a 1000 px, o URL) y **videos** (link de YouTube). Los cambios quedan **en el navegador de quien los hace** (`localStorage`, clave `bn_admin_v1`); sin contraseña porque nada se publica solo. **Exportar para publicar** baja `extra.json`; hay que reemplazar `bnacional-data/data/extra.json` y pushear. Formato: `{fotos:[], videos:[], ocultos:{fotos:[], videos:[]}}`; `ocultos` esconde recursos de la base por su `img` o `id`.
- Si algún día hace falta que **otras personas** carguen recursos directo, se necesita un backend (Cloudflare Workers/KV o D1 + una clave de admin). No existe todavía.
- `js/config.js`: `emails` (reciben los recursos: desde el 30/10/2026 un solo mail de la página, `bnpagina2027@gmail.com`), **`cafecito`** (`https://cafecito.app/b_nacional`) y `apoyo` (segundo botón «Ayudá al proyecto»; vacío = no aparece). Los mails abren un correo ya armado con asunto y formulario.

## 8. `chacarita-data/` y lo demás

- Sitio con 3.535 partidos de Chacarita (1931–2026). `tools/build_data.py <DATACHACA.xlsx> data/enrichment/parche_*.json` lo regenera; `verify_vs_excel.py` da 1.731 comprobaciones iguales y 0 diferencias (necesita el Excel «DATACHACA Máster», que **no** está en el repo). Cada dato agregado de fuentes públicas está marcado «agregado» con su fuente (`data/enrichment/parche_datos.csv`). Detalle en `chacarita-data/README.md`.
- **Faltan** (sobre 3.535): árbitro 1.080, DT 1.888, espectadores 2.892, formación 1.092; se concentra en 1980–83, 1986/87–1998/99, 2004/05–2007/08, 2012/13–2013/14. Fuentes que bloquean: SofaScore, fbref, worldfootball, mundoascenso, sitio oficial del club. Listas para revisar a mano en `data/enrichment/revisar_*.csv` y `hallazgos_goleadores_planilla_vs_cronica.csv` (234).
- Posibles fuentes nuevas ya identificadas: Solo Ascenso por categoría, sitios de historia de clubes rivales (Museo Granate, La Historia River, El Sitio de Almagro ya usados), Infobae 2004–2008, diarios digitalizados.

## 9. Backlog priorizado (lo que sigue)

1. **Despliegue:** confirmar con Marcos qué rama mira Cloudflare; mergear `claude/hallazgos-datos-bnacional` → `main` (con su OK); verificar el sitio publicado con el smoke test apuntando a la URL `*.pages.dev`.
2. **Cafecito:** pedirle a Marcos su usuario y ponerlo en `js/config.js`; ver si quiere el segundo link («Ayudá al proyecto»).
3. Reproducibilidad de `run.py` + subir `bnacional/cache` (§4).
4. Cerrar los 161 pendientes (§4).
5. Revisar y completar los **clásicos** (§5).
6. **Promociones contra Primera** en otra rama (§4).
7. Fotos para los 57 clubes sin fotos (Commons; también pedir a la gente por mail) y revisar los dos escudos compartidos.
8. Conseguir formaciones/planteles anteriores a 2014 (no hay fuente conocida: ver RSSSF, Wikipedia por club, libros digitalizados).
9. Chacarita: revisar las listas `revisar_*.csv` y seguir completando huecos (§8).
10. Mejoras del sitio que se hablaron (la fecha «aproximada» ya se oculta): `Menú` en una línea con 11 secciones (Nico ya lo ajustó; si se suma una sección más, revisar a 1280 px).

## 10. Cómo trabajar acá

- Cambios chicos y probados: corré `smoke_test.mjs` y mirá capturas de lo que tocaste en **claro y oscuro y a 390 px**.
- Cada dato que agregues a mano tiene que poder rastrearse a una fuente (archivo + motivo).
- Sé honesto en pantalla con lo que es calculado, aproximado o de memoria (ej.: descensos, fechas aproximadas, clásicos sin verificar).
- Commits en español, descriptivos, de a un tema. Una rama por tema; PR para datos.
- Si algo del hosting o de una fuente falla, no insistas en bucle: describí el problema y proponé alternativa.
