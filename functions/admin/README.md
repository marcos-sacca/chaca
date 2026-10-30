# Administración privada (`/admin/`)

El panel de fotos y videos **no está en el sitio público**: vive en `bnacional-data/admin/` y todo lo que cuelga de `/admin/` pasa por `_middleware.js`, que pide usuario y contraseña. Sin sesión válida no se sirve ni el HTML ni el JS del panel.

## Cómo funciona
- Usuario: el mail guardado en el secreto `ADMIN_EMAIL`. Contraseña: se guarda **solo como hash** (PBKDF2-SHA256, 100.000 vueltas) en `ADMIN_PASS_HASH`. Nada de esto está en el repo.
- Al entrar se crea una cookie firmada (`HttpOnly`, `Secure`, `SameSite=Strict`) que dura 8 horas. Cerrar sesión: `/admin/logout`.
- Frenos: 5 intentos fallidos por IP cada 15 minutos (el contador vive en la caché de cada datacenter de Cloudflare, no es global) y una demora de 0,7 s en cada error.

## Secretos del proyecto Pages `bnacional-historica`
| Secreto | Qué es |
|---|---|
| `ADMIN_EMAIL` | mail de acceso |
| `ADMIN_PASS_HASH` | `pbkdf2:100000:<sal base64>:<hash base64>` |
| `SESSION_SECRET` | 32 bytes al azar (base64); si se cambia, se cierran todas las sesiones |
| `CF_ACCOUNT_ID`, `CF_SITE_TAG`, `CF_ANALYTICS_TOKEN` | opcionales: activan la pestaña Tráfico (ver `api/stats.js`) |

## Cambiar la contraseña
1. Generar el hash (Node 18+), con la contraseña nueva en la variable `PASS`:
   ```js
   const c = require("crypto"), salt = c.randomBytes(16), pass = process.env.PASS;
   const h = c.pbkdf2Sync(pass, salt, 100000, 32, "sha256");
   console.log(`pbkdf2:100000:${salt.toString("base64")}:${h.toString("base64")}`);
   ```
2. Guardarlo (el valor se pega por stdin, no queda en el historial del comando):
   `npx wrangler pages secret put ADMIN_PASS_HASH --project-name bnacional-historica`
3. Cambiar también `SESSION_SECRET` si se sospecha que la sesión se filtró. Los secretos se aplican en el próximo despliegue.

## Límites conocidos
- Una sola cuenta, sin segundo factor. Para algo más serio, poner Cloudflare Access (login por mail con código) delante de `/admin/*`; requiere un token con permiso de Access.
- Los cambios del panel (fotos y videos) se guardan en el navegador de quien los hace y se publican exportando `extra.json`, como antes.
