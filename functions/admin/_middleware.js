// Login y protección de /admin/* (Cloudflare Pages Functions).
// Todo lo que cuelga de /admin/ (la página, el JS del panel y /admin/api/*) pasa por acá: sin sesión válida no se sirve nada.
// Secretos del proyecto (nunca en el repo): ADMIN_EMAIL, ADMIN_PASS_HASH ("pbkdf2:<iteraciones>:<sal b64>:<hash b64>") y SESSION_SECRET.
// Para cambiar la contraseña: functions/admin/README.md.
const COOKIE = "bn_admin";
const SESSION_SECS = 8 * 3600;
const MAX_FAILS = 5; // intentos fallidos por IP en 15 min (el contador vive en la caché del datacenter: frena el golpeteo, no es global)
const enc = new TextEncoder();

const b64 = (buf) => btoa(String.fromCharCode(...new Uint8Array(buf)));
const unb64 = (s) => Uint8Array.from(atob(s), (c) => c.charCodeAt(0));
const b64url = (buf) => b64(buf).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
const unb64url = (s) => unb64(s.replace(/-/g, "+").replace(/_/g, "/") + "=".repeat((4 - (s.length % 4)) % 4));

async function hmacKey(secret) { return crypto.subtle.importKey("raw", enc.encode(secret), { name: "HMAC", hash: "SHA-256" }, false, ["sign", "verify"]); }
async function sign(secret, text) { return b64url(await crypto.subtle.sign("HMAC", await hmacKey(secret), enc.encode(text))); }
async function safeEq(a, b) { // comparación en tiempo constante (compara los SHA-256 de ambos)
  const [x, y] = await Promise.all([crypto.subtle.digest("SHA-256", enc.encode(a)), crypto.subtle.digest("SHA-256", enc.encode(b))]);
  const u = new Uint8Array(x), v = new Uint8Array(y); let d = 0; for (let i = 0; i < u.length; i++) d |= u[i] ^ v[i]; return d === 0;
}
async function checkPassword(pass, stored) {
  const [alg, iter, salt, hash] = String(stored || "").trim().split(":");
  if (alg !== "pbkdf2" || !iter || !salt || !hash) return false;
  const key = await crypto.subtle.importKey("raw", enc.encode(pass), "PBKDF2", false, ["deriveBits"]);
  const bits = await crypto.subtle.deriveBits({ name: "PBKDF2", hash: "SHA-256", salt: unb64(salt), iterations: +iter }, key, 256);
  return safeEq(b64(bits), hash);
}
const getCookie = (req, name) => (req.headers.get("Cookie") || "").split(/;\s*/).map((c) => c.split("=")).find(([k]) => k === name)?.[1];
async function validSession(req, env) {
  const tok = getCookie(req, COOKIE); if (!tok || !env.SESSION_SECRET) return false;
  const [exp, sig] = tok.split("."); if (!exp || !sig || !(+exp > Date.now() / 1000)) return false;
  return crypto.subtle.verify("HMAC", await hmacKey(env.SESSION_SECRET), unb64url(sig), enc.encode("v1." + exp));
}
const setCookie = (value, maxAge) => `${COOKIE}=${value}; Path=/; Max-Age=${maxAge}; HttpOnly; Secure; SameSite=Strict`;
// contador de fallos por IP: si la caché no responde (por ejemplo en desarrollo local) no se cuenta, pero el login sigue funcionando
const failKey = (req) => new Request("https://bn-admin-fails.example.com/" + encodeURIComponent(req.headers.get("CF-Connecting-IP") || "local"));
async function fails(req) { try { const r = await caches.default.match(failKey(req)); return r ? +(await r.text()) || 0 : 0; } catch { return 0; } }
async function addFail(req) { try { await caches.default.put(failKey(req), new Response(String((await fails(req)) + 1), { headers: { "Cache-Control": "max-age=900" } })); } catch { /* sin contador */ } }

const SEC = { "Cache-Control": "no-store", "X-Robots-Tag": "noindex, nofollow", "X-Content-Type-Options": "nosniff", "X-Frame-Options": "DENY", "Referrer-Policy": "same-origin" }; // con no-referrer el navegador manda "Origin: null" en el formulario y el chequeo anti-CSRF lo rechazaría
function loginPage(msg = "", status = 200) {
  const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  return new Response(`<!doctype html><html lang="es"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><title>Administración</title>
<style>:root{color-scheme:light dark;--bg:#f5f7fb;--card:#fff;--ink:#0b2447;--mut:#5b6b85;--line:#d5dcea;--btn:#123a6b;--err:#b3261e}@media(prefers-color-scheme:dark){:root{--bg:#08172b;--card:#0e2240;--ink:#e8eefb;--mut:#9db0cf;--line:#244069;--btn:#5fb4e6;--err:#ff8a80}}
body{margin:0;min-height:100vh;display:grid;place-items:center;background:var(--bg);color:var(--ink);font:16px/1.5 system-ui,sans-serif}main{width:min(380px,92vw);background:var(--card);border:1px solid var(--line);border-radius:14px;padding:28px}h1{font-size:1.2rem;margin:0 0 4px}p{margin:0 0 18px;color:var(--mut);font-size:.9rem}label{display:block;font-size:.85rem;margin:12px 0 4px}input{width:100%;box-sizing:border-box;height:44px;padding:0 12px;border:1px solid var(--line);border-radius:10px;background:transparent;color:inherit;font:inherit}button{margin-top:18px;width:100%;height:46px;border:0;border-radius:10px;background:var(--btn);color:#fff;font:inherit;font-weight:600;cursor:pointer}@media(prefers-color-scheme:dark){button{color:#08172b}}.err{color:var(--err);margin:14px 0 0;font-size:.9rem}</style></head>
<body><main><h1>Administración</h1><p>B Nacional Histórica</p><form method="post" action="/admin/login"><label for="e">Usuario (mail)</label><input id="e" name="email" type="email" autocomplete="username" required autofocus><label for="p">Contraseña</label><input id="p" name="password" type="password" autocomplete="current-password" required><button type="submit">Entrar</button>${msg ? `<p class="err" role="alert">${esc(msg)}</p>` : ""}</form></main></body></html>`,
    { status, headers: { ...SEC, "Content-Type": "text/html; charset=utf-8", "Content-Security-Policy": "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; frame-ancestors 'none'; base-uri 'none'" } });
}

export async function onRequest(context) {
  const { request, env, next } = context, url = new URL(request.url), path = url.pathname.replace(/\/+$/, "");
  if (!env.ADMIN_EMAIL || !env.ADMIN_PASS_HASH || !env.SESSION_SECRET) return new Response("Administración sin configurar.", { status: 503, headers: SEC });

  if (path === "/admin/login") {
    if (request.method === "GET") return (await validSession(request, env)) ? Response.redirect(url.origin + "/admin/", 302) : loginPage();
    if (request.method !== "POST") return new Response("Método no permitido", { status: 405, headers: SEC });
    const origin = request.headers.get("Origin"); if (origin && origin !== url.origin) return new Response("Origen no permitido", { status: 403, headers: SEC });
    if ((await fails(request)) >= MAX_FAILS) return loginPage("Demasiados intentos. Probá de nuevo en 15 minutos.", 429);
    let email = "", pass = ""; try { const f = await request.formData(); email = String(f.get("email") || "").trim().toLowerCase(); pass = String(f.get("password") || ""); } catch { /* formulario inválido */ }
    const okMail = await safeEq(email, String(env.ADMIN_EMAIL).trim().toLowerCase()), okPass = await checkPassword(pass.slice(0, 200), env.ADMIN_PASS_HASH); // las dos siempre se calculan
    if (!(okMail && okPass)) { await addFail(request); await new Promise((r) => setTimeout(r, 700)); return loginPage("Usuario o contraseña incorrectos.", 401); }
    const exp = Math.floor(Date.now() / 1000) + SESSION_SECS;
    return new Response(null, { status: 302, headers: { ...SEC, Location: "/admin/", "Set-Cookie": setCookie(`${exp}.${await sign(env.SESSION_SECRET, "v1." + exp)}`, SESSION_SECS) } });
  }
  if (path === "/admin/logout") return new Response(null, { status: 302, headers: { ...SEC, Location: "/admin/login", "Set-Cookie": setCookie("", 0) } });

  if (!(await validSession(request, env))) {
    if (path.startsWith("/admin/api")) return new Response(JSON.stringify({ error: "no autorizado" }), { status: 401, headers: { ...SEC, "Content-Type": "application/json" } });
    return Response.redirect(url.origin + "/admin/login", 302);
  }
  const res = await next(); // sesión válida: se sirve el archivo o la API
  const out = new Response(res.body, res); for (const [k, v] of Object.entries(SEC)) out.headers.set(k, v);
  return out;
}
