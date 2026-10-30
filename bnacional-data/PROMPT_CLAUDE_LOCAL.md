Tu tarea: publicar en Cloudflare Pages el sitio estático que está en la carpeta `bnacional-data/` de este repositorio (`marcos-sacca/chaca`) y verificar que funcione. No hay build ni dependencias: el directorio a subir es `bnacional-data`, con `index.html` en la raíz.

## Credenciales
- El API token y el Account ID de Cloudflare los voy a exportar como variables de entorno: `CLOUDFLARE_API_TOKEN` y `CLOUDFLARE_ACCOUNT_ID`. Leélas del entorno; si no están, pedímelas y esperá.
- No las escribas en ningún archivo, no las imprimas, no las pases en la línea de comandos si hay otra forma, y no las incluyas en commits, logs ni mensajes. Si wrangler muestra el token en una salida, tapalo al resumirme.
- Usá wrangler sin login interactivo (con las variables alcanza). Si falla por permisos, decime exactamente qué permiso le falta al token (hace falta "Cloudflare Pages: Edit").

## Pasos
1. Cloná el repo si no está y pasate a la rama `claude/hallazgos-datos-bnacional` (`git fetch origin` y `git checkout claude/hallazgos-datos-bnacional`). Confirmá que existe `bnacional-data/index.html`.
2. Verificá que haya Node 18 o más (`node -v`) y usá `npx wrangler@latest` (no instales nada global).
3. Si el proyecto `bnacional-historica` no existe, crealo: `npx wrangler@latest pages project create bnacional-historica --production-branch main`. Si el nombre está tomado, probá `bnacional-historica-2027` y avisame cuál usaste.
4. Desplegá: `npx wrangler@latest pages deploy bnacional-data --project-name <nombre> --branch main --commit-dirty=true`. Para que no suba basura, antes borrá de una copia temporal (no del repo) las carpetas `tools/` y los `.md` de `bnacional-data`, y desplegá desde esa copia.
5. Verificación (obligatoria, no des por bueno el deploy solo porque wrangler diga OK). Con la URL `https://<nombre>.pages.dev`:
   - `curl -sI` a `/`, `/data/meta.json`, `/data/teams.json`, `/data/extra.json` y `/assets/img/crests/banfield.png`: todos deben dar 200.
   - Abrí el sitio con un navegador headless (Playwright o Chrome headless) y revisá sin errores de consola estas rutas: `/`, `/#ascensos`, `/#clubes`, `/#c-banfield`, `/#t-1996-97`, `/#fotos`, `/#videos`, `/#admin`. Sacá una captura de la portada y de `/#ascensos`.
   - En `/#ascensos` tienen que verse escudos (no fotos) como carátula de cada club.
   - En `/#admin`, agregá una foto de prueba y comprobá que aparece; después tocá "Descartar cambios" para dejarlo limpio.
6. Si algo falla, arreglalo si es del despliegue (rutas, tipos MIME, archivos que faltan). Si el problema está en el código del sitio, no lo toques: describímelo.

## Qué NO hacer
- No cambies código del sitio ni hagas commits o push al repositorio.
- No configures dominios personalizados ni DNS.
- No borres proyectos ni despliegues existentes de la cuenta.

## Al terminar
Mostrame: la URL final, el nombre del proyecto, el resultado de cada chequeo (200 o error) y las capturas. Recordame que (1) cambie el usuario de Cafecito en `bnacional-data/js/config.js` y (2) borre o rote el API token ahora que terminó el deploy. Para futuras actualizaciones alcanza con repetir el paso 4, o conectar el repo a Pages desde el panel para que se actualice con cada push.
