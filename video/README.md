# Video "Chacarita fecha por fecha"

Recorrido vertical (720×1280, ~80 s) de la Zona B de la Primera Nacional 2026:
una pantalla por partido de Chacarita, con el resultado arriba y la tabla de la
zona al cierre de esa fecha (PTS, J, Gol, +/-, G, E, P y últimas 5, con el más
reciente a la izquierda). Imita el formato del recorrido que hizo la comunidad de
Nueva Chicago: misma grilla, colores y tipografía medidos sobre sus fotogramas.

## Cómo se regenera

```bash
python video/refresh_data.py     # opcional: baja fechas nuevas (necesita api.sofascore.com)
python video/build_data.py       # cache de Sofascore -> video/out/steps.json
python video/render.py           # steps.json -> video/out/chacarita_fecha_por_fecha.mp4
```

`render.py` usa Chromium headless (el de Playwright, `/opt/pw-browsers`, o el
que indique `CHROME_BIN`) y `ffmpeg`. Fuente: Liberation Sans.

## Qué hay en cada archivo

| Archivo | Para qué |
|---|---|
| `build_data.py` | Lee `data/cache/*events_round_*.json`, descarta duplicados de partidos reprogramados, suma las interzonales (fechas 7 y 25) y calcula la tabla al cierre de cada fecha. **No inventa**: si faltan resultados del resto de la zona, no genera esa pantalla. |
| `render.py` | Dibuja cada pantalla en HTML/CSS, la captura y arma el mp4. |
| `extract_crests.py` | Saca los escudos de un video de referencia (Sofascore los sirve desde `api.sofascore.app`, bloqueado en el entorno cloud) y los deja en `crests/<team_id>.png`. Si se consiguen los originales, alcanza con pisar esos PNG. |
| `refresh_data.py` | Vuelve a pedir a Sofascore solo las fechas con partidos sin terminar. |
| `data/chacarita_f29_f34_manual.json` | Resultados de Chacarita de la fecha 29 a la 34, cargados a mano (ver abajo). |

## Criterios (verificados contra el video original)

- Tabla **al cierre de la fecha** (con tope de 3 días), no al cierre del día del partido.
  La fecha del encabezado es la del cierre; debajo va la fecha del partido.
- Desempate: puntos, diferencia de gol, goles a favor, orden alfabético.
- Partidos postergados que se juegan mucho después: una pantalla "PARTIDO PENDIENTE AL
  CIERRE DE ESTA FECHA" en su fecha, y otra "RECUPERADA" el día que se juega.
- Comprobado contra el original: la tabla completa de la fecha 5 (18 filas) coincide
  posición por posición, con puntos, partidos y goles. En la fecha 1 coinciden puntos,
  partidos y goles, pero el original ordena de otra forma algunos **empates exactos**
  (mismos puntos, DG y GF; p. ej. Chicago antes que Atlanta): su criterio no se puede
  deducir, así que acá van en orden alfabético.

## Estado de los datos (21-oct-2026): completo, fechas 1 a 34

- **Fechas 1 a 27**: cache de Sofascore del 6-sep (`data/cache`).
- **Fechas 29 a 34**: resultados pegados de una pagina de resultados
  (`data/fuente_resultados_f29_f34.txt`), cargados con `parse_resultados.py` en
  `data/resultados_faltantes.csv`. Los 6 partidos de Chacarita estan ademas en
  `data/chacarita_f29_f34_manual.json` y ambas fuentes coinciden.
- **Derivados de las tablas del video de referencia** (no estaban en ninguna fuente de texto;
  cada uno lleva su nota en el CSV): los 6 partidos de la fecha 28 que faltaban
  (Chicago 1-0 Quilmes sale del encabezado de ese video), el San Martin 1-0 Chicago de la
  fecha 17 (abandonado el 6/06; el video lo cuenta entre el 24/08 y el 31/08, por eso el dia
  26/08 es aproximado) y el San Martin 0-0 Tristan Suarez de la fecha 21 (reprogramado).
  Se obtienen restando, equipo por equipo, lo calculado a la tabla del video: cada partido
  aparece espejado en los dos equipos, y los puntos, partidos y goles de ambos cierran.

### Verificacion contra el video original

- **Fecha 34** (tabla final): las 18 filas coinciden en posicion, puntos, partidos y goles.
- **Fecha 30**: las 18 filas coinciden (confirma que el reprogramado de la F21 ya esta jugado).
- **Fecha 28**: coincide por construccion (de ahi se derivaron los 6 partidos).
- Fechas 5 y 29 a 34 de Chacarita: ver mas arriba; los datos de Chacarita (36 pts, DG -9,
  puesto 16) coinciden con las fichas de partido.

Los marcadores de las fuentes son **local-visitante**; el titulo de las fichas de partido
pone al visitante primero y confunde. Con el orden inverso Chacarita terminaria con DG -13.

Datos de Sofascore: uso interno, ver `informe_datos_chacarita.html` para el encuadre legal.
