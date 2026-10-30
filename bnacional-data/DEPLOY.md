# Publicar el sitio en Cloudflare Pages

El sitio es estático: no hay nada que compilar. Todo lo que sirve está en esta carpeta (`bnacional-data/`), salvo `tools/` y `README.md`, que no hacen falta.

## Opción A: conectar el repositorio (recomendada, se actualiza sola)
1. Cloudflare → **Workers y Pages** → **Crear** → pestaña **Pages** → **Conectar con Git**.
2. Elegir `marcos-sacca/chaca` y autorizar a Cloudflare.
3. Rama de producción: la que tenga el sitio (hoy `claude/hallazgos-datos-bnacional`; si se mergea, `main`).
4. **Comando de compilación:** vacío. **Directorio de salida:** `bnacional-data`.
5. Guardar y desplegar. Cada `git push` a esa rama vuelve a publicar. Para sumar fotos o videos desde `#admin`, se reemplaza `bnacional-data/data/extra.json` y se sube.

## Opción B: subir la carpeta a mano
**Workers y Pages** → **Crear** → **Pages** → **Cargar activos**: arrastrar la carpeta `bnacional-data` (con `index.html` en la raíz). No hace falta Git.

## Opción C: que lo haga un Claude Code local
Pegarle esto en una carpeta con el repo clonado:

> Publicá el sitio estático de `bnacional-data/` en Cloudflare Pages. No hay build: el directorio a subir es `bnacional-data` (con `index.html` en la raíz). Instalá `wrangler` si falta, iniciá sesión con `wrangler login` (me abre el navegador) y corré `wrangler pages deploy bnacional-data --project-name bnacional-historica --branch main`. Después abrime la URL `*.pages.dev`, verificá que carguen la portada, `#ascensos`, `#clubes`, `#fotos` y `#admin`, y avisame si algo falla. No pidas ni guardes tokens en el repositorio.

## Después de publicar
- En `js/config.js` poner el usuario real de Cafecito (hoy apunta a `https://cafecito.app/`) y, si se quiere, `apoyo.url`.
- Con dominio propio: Pages → **Dominios personalizados**.
