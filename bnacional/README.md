# B Nacional histórica (1986/87 → hoy)

Base de partidos, goleadores y tablas de la Primera B Nacional, armada con scripts a partir de fuentes públicas y con **control cruzado** entre ellas.
Sigue la estructura de la planilla «B Nacional histórica» (hojas `partidos`, `goleadores`, `reducidos`, `sanciones`, `equipos`, `estadios`, `control fuente`, `fuentes`) y le suma las tablas ya calculadas.

## Qué hay en `data/`

| Archivo | Contenido |
|---|---|
| `B_Nacional_historico.xlsx` | Todo junto en un libro de Excel (una hoja por CSV, con filtros). |
| `tabla_general.csv` | **Tabla histórica**: PJ, PG, PE, PP, GF, GC, DG, descuentos y puntos (con el sistema de cada temporada y a 3 por victoria). |
| `tabla_temporada.csv` | Tabla de cada temporada y de cada fase (zonas, Apertura/Clausura, etapas). |
| `ranking_goleadores.csv` | Goleadores históricos (de las crónicas, 1986/87 a 2018/19). |
| `partidos.csv`, `goleadores.csv`, `reducidos.csv` | Un partido / un gol por fila. Los de reducidos, promociones y cruces fuera de zona están en `reducidos.csv` y no suman en las tablas. |
| `temporadas.csv`, `sanciones.csv`, `equipos.csv`, `estadios.csv` | Datos de cada temporada, descuentos de puntos (leídos de las notas de la fuente), clubes y canchas. |
| `control_fuente.csv` | Puntos de cada equipo según la crónica vs. puntos calculados con los partidos cargados (`OK` / `Revisar`). |
| `diferencias_entre_fuentes.csv`, `resumen_control_cruzado.csv`, `correcciones_aplicadas.csv` | Cruce de cada marcador con una segunda fuente y qué se corrigió. |
| `errores_de_lectura.csv` | Líneas de la fuente que el script no pudo interpretar (errores de tipeo de la página original). |
| `fuentes.csv`, `fuentes/` | De dónde sale cada dato. |

## Fuentes

1. **Crónicas de José Carluccio, «Historia y Fútbol»** (josecarluccio.blogspot.com): resultados, goleadores, ciudades y notas de 1986/87 a 2018/19. Es la misma fuente de la planilla original.
2. **RSSSF – Argentina Second Level**: segunda fuente de resultados 1986/87 a 2007/08.
3. **Transfermarkt**: segunda fuente 2008/09 a 2018/19 y única fuente de resultados de 2017/18 y de 2019/20 en adelante (sin goleadores).

## Cómo se controla

* Se calcula la tabla de cada fase con los partidos cargados y se compara con las **posiciones que publica la propia crónica** (`control_fuente.csv`).
* Cada marcador se compara con RSSSF / Transfermarkt. Si un marcador difiere y **al corregirlo los puntos coinciden con la tabla publicada**, se corrige y queda anotado en `correcciones_aplicadas.csv` y en las observaciones del partido. Lo mismo con partidos que faltaban o estaban rotos en la crónica.
* Los descuentos de puntos se leen de las notas («A Almirante Brown se le descontaron 18 puntos…»).
* Cuando ni así cuadra, queda en `Revisar`: son los casos para mirar a mano.

## Cómo actualizarla

```
python3 -I bnacional/tools/run.py --actual     # baja de Transfermarkt la temporada en curso y reconstruye todo
python3 -I bnacional/tools/run.py              # solo reconstruye con lo que ya está bajado
python3 -I bnacional/tools/run.py --bajar      # baja todo desde cero (lento: ~200 crónicas, RSSSF y Transfermarkt)
```

Hace falta Python 3 con `beautifulsoup4`, `lxml` y `openpyxl`. Lo bajado se guarda en `bnacional/cache/` (no se sube a Git).

Para corregir o agregar algo a mano: editar el CSV correspondiente en `data/` **no alcanza** (se regeneran). Los arreglos manuales van en `tools/jc_parse.py` (errores de tipeo de la fuente) o en `tools/clubes.py` / `tools/names_ext.py` (nombres de clubes). Si preferís mantener la planilla a mano a partir de acá, usá `B_Nacional_historico.xlsx` como punto de partida y dejá de correr los scripts.

## Límites conocidos

* **Goleadores**: solo hasta 2018/19 (la crónica no sigue). 2017/18 y 2019/20 en adelante tienen solo resultados.
* **Formatos con zonas desde 2021**: los partidos están, pero la tabla de temporada de esos años mezcla las zonas (hace falta cargar a qué zona pertenece cada equipo).
* **Transición 2014** no está en Transfermarkt: solo crónica.
* **1996/97 y otros formatos con etapas**: algunas tablas publicadas incluyen puntos extra o arrastran puntos de etapas anteriores; figuran como `Revisar`.
* **Canchas**: se asumen como la del local salvo que la nota diga otra cosa (`Origen dato cancha`).
* **Jugadores**: los nombres se unifican por equipo (iniciales, tildes, apellido); puede haber duplicados que revisar.
