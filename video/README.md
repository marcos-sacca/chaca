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

## Estado de los datos (21-oct-2026)

La cache de Sofascore es del 6-sep (hasta la fecha 28). Para las fechas **29 a 34** solo
se conocen los resultados de Chacarita (pegados a mano) y no los del resto de la zona,
así que esas 6 pantallas **no se generan** hasta correr `refresh_data.py`.

Los marcadores de ese JSON son **local-visitante**: el título de las fichas pone al
visitante primero y confunde. Se verificó sumando a la cache: Chacarita termina con
36 pts y DG -9 (puesto 16), igual que la tabla de las fichas; con el orden inverso el DG
daría -13.

Datos de Sofascore: uso interno, ver `informe_datos_chacarita.html` para el encuadre legal.
