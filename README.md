# Chacarita Data Project

Proyecto de ciencia de datos aplicado a CA Chacarita Juniors (Primera Nacional,
Argentina). Armado en la sesión del 06-sep-2026.

## Los dos documentos

- **`informe_datos_chacarita.html`** — investigación de fuentes: qué APIs y
  datasets de fútbol argentino existen, cuáles funcionan de verdad (probado en
  vivo), costos, y el encuadre legal de cada uno.
- **`situacion_chacarita.html`** — el análisis en sí: probabilidad de descenso
  (modelo propio), qué hace falta en las 8 fechas que quedan, dossier de
  rivales, y scouting real para 2027.

Ambos están publicados como Artifact (pedile el link a Claude si lo perdiste,
o `/artifacts` en la terminal).

## Estructura de carpetas

```
scripts/            Todo el código, reutilizable y ya corrido con éxito
  sofa_lib.py                        librería base: cache en disco + manejo de rate-limit
  fetch_zone_b.py                    calendario y stats de la Zona B 2026
  simulate_zone_b.py                 modelo Poisson + Monte Carlo de descenso
  fetch_scouting.py                  transfer-history de los planteles de Zona B
  fetch_primera_b_metro_scouting.py  goleadores reconstruidos (destino real si desciende)
  fetch_federal_a_scouting.py        mismo extractor, aplicado por error a la liga equivocada (ver abajo)
  fetch_chacarita_historia.py        historial completo 2009-2026
  fetch_transfermarkt_squad.py       valores de mercado de planteles

data/raw/            Datos crudos tal como vienen de la fuente
data/processed/       Datos ya cruzados/calculados (lo que alimenta los informes)
data/cache/           Cache de requests a Sofascore (no tocar; acelera re-correr los scripts)
```

## Cómo seguir mañana

1. **Revisar si Sofascore ya no bloquea:**
   ```
   curl -A "Mozilla/5.0" https://api.sofascore.com/api/v1/team/3214/players
   ```
   Si devuelve 200 (no 403), ya se puede seguir.

2. **Completar lo que quedó pendiente por el bloqueo** (ver "Qué falta" abajo):
   ```
   python scripts/fetch_primera_b_metro_scouting.py
   python scripts/fetch_chacarita_historia.py
   ```

3. **Actualizar todo después de cada fecha del torneo** (recomendado, cada
   sábado/domingo): volver a correr `fetch_zone_b.py` y `simulate_zone_b.py`
   para tener la probabilidad de descenso al día.

## Qué falta (por el bloqueo 403 de Sofascore a mitad de sesión)

- Goleadores/asistentes reales de Primera B Metropolitana 2026 (el script ya
  está listo y corregido, ver `fetch_primera_b_metro_scouting.py`).
- Estadísticas (xG) del historial completo de Chacarita 2009-2026 — el
  calendario ya está bajado (`chacarita_historia_completa.csv`), falta la
  fase de estadísticas por partido.
- Extender el scouting a Uruguay/Chile/Paraguay (quedó en "decidilo vos según
  cómo rinda la noche" — no se llegó por el bloqueo, no por falta de tiempo).

## Un error real que se cometió y corrigió esta noche

Se asumió primero que Chacarita, de descender, caería a **Federal A**. Es
incorrecto: por ser club de Capital Federal con afiliación **directa** a AFA,
el destino real es **Primera B Metropolitana** (Federal A es para clubes de
afiliación indirecta, del interior del país). Ver el callout correspondiente
en `situacion_chacarita.html` para el detalle completo. El trabajo ya hecho en
Federal A no se descartó — quedó como base técnica, y `fetch_federal_a_scouting.py`
es exactamente el mismo código apuntado a la liga incorrecta.
