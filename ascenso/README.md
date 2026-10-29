# Solo Ascenso: síntesis de partidos

Carpeta con el scraper y el normalizador de las páginas de síntesis de [Solo Ascenso](https://www.soloascenso.com.ar/) (el `robots.txt` del sitio permite el rastreo).
Cada síntesis trae fecha, hora, categoría, ronda, estadio, árbitro, formaciones con edad y puesto, DT, goles con minuto, cambios y tarjetas.

| Archivo | Qué es |
|---|---|
| `tools/sa_scrape.py` | Baja `sintesis/x/<id>` para un rango de números. Se puede cortar y retomar (salta los ids ya bajados). |
| `tools/sa_norm.py` | Une lo bajado y asigna cada gol a un lado (por la formación del jugador), marcando si los goles cierran con el marcador. |
| `data/sintesis_solo_ascenso.jsonl.gz` | 24.091 partidos normalizados (ids 5000 a 46700, desde 2014): Primera Nacional 6.639, Primera B 4.792, Primera C 4.862, Federal A 3.732, Promocional Amateur 2.274, Copa Argentina 1.384, Regional Amateur 111. |

Los ids por debajo de 5000 están vacíos y entre 5000 y 8000 casi no hay datos; la cobertura útil empieza en la Primera Nacional 2014.

## Cómo se usa

- **B Nacional** (`bnacional/`): reemplaza a Transfermarkt como fuente principal de 2017/18, 2019/20, Transición 2020 y 2021 a 2026 (con goleadores, árbitro y cancha), y sirve de control cruzado para 2014 a 2018/19 (coincide en el 99,5 % o más de los partidos).
- **Chacarita** (`chacarita-data/tools/enrich_sa.py`): valida árbitro, DT y goleadores de 2013 en adelante y propone lo que falte.

## Actualizar

```
python3 -I ascenso/tools/sa_scrape.py salida.jsonl <id_desde> <id_hasta>   # solo ids nuevos (los últimos publicados)
python3 -I ascenso/tools/sa_norm.py <carpeta_con_jsonl> ascenso/data/sintesis_solo_ascenso.jsonl.gz
python3 -I bnacional/tools/run.py
```
