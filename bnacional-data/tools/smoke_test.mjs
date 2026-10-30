// Prueba de humo del sitio: abre cada ruta (claro y oscuro, escritorio y celular) y avisa de errores de JS, desbordes y páginas vacías.
//   npm i playwright && npx playwright install chromium     (una sola vez, en cualquier carpeta)
//   node bnacional-data/tools/smoke_test.mjs [carpeta_de_capturas]
//   $env:SITE_URL = "https://bnacional-historica.pages.dev"   (opcional: prueba el sitio publicado en vez de la copia local)
import { chromium } from "playwright";
import http from "node:http";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const root = process.env.SITE_ROOT || path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const out = process.argv[2];
const MIME = { ".html": "text/html", ".js": "text/javascript", ".css": "text/css", ".json": "application/json", ".jpg": "image/jpeg", ".png": "image/png", ".svg": "image/svg+xml", ".woff2": "font/woff2" };
const routes = ["", "#ascensos", "#temporadas", "#t-1996-97", "#t-transicion-2014", "#clubes", "#c-banfield", "#tabla", "#reducidos", "#historial", "#historial-banfield_vs_quilmes", "#clasicos", "#goleadores", "#juegos", "#jugador", "#grilla", "#contrarreloj", "#masgoles", "#carrera", "#fotos", "#videos", "#datos"];

const srv = http.createServer((q, r) => {
  let p = path.join(root, decodeURIComponent(q.url.split("?")[0])); if (p.endsWith(path.sep) || p.endsWith("/")) p += "index.html";
  fs.readFile(p, (e, d) => { if (e) { r.writeHead(404); r.end(); return; } r.writeHead(200, { "content-type": (MIME[path.extname(p)] || "application/octet-stream") + "; charset=utf-8" }); r.end(d); });
}).listen(0, async () => {
  const base = process.env.SITE_URL ? process.env.SITE_URL.replace(/\/$/, "") + "/" : `http://localhost:${srv.address().port}/index.html`; // SITE_URL: probar el sitio publicado
  const b = await chromium.launch(), errs = [];
  if (out) fs.mkdirSync(out, { recursive: true });
  for (const scheme of ["light", "dark"]) for (const [i, hash] of routes.entries()) for (const w of [1280, 390]) {
    if (scheme === "dark" && w === 390) continue;
    const tag = `${hash || "#inicio"} ${scheme} ${w}px`, ctx = await b.newContext({ viewport: { width: w, height: 900 }, colorScheme: scheme }), pg = await ctx.newPage();
    pg.on("pageerror", (e) => errs.push(`${tag}: ${e.message}`)); pg.on("console", (m) => m.type() === "error" && errs.push(`${tag}: ${m.text().slice(0, 140)}`));
    pg.on("response", (r) => r.status() >= 400 && !r.url().includes("ytimg") && errs.push(`${tag}: HTTP ${r.status()} ${r.url()}`));
    await pg.goto(base + hash); await pg.waitForTimeout(800);
    if (await pg.evaluate(() => document.documentElement.scrollWidth > innerWidth + 1)) errs.push(`${tag}: desborde horizontal`);
    if (await pg.evaluate(() => document.querySelector("#app").innerText.trim().length < 40)) errs.push(`${tag}: página vacía`);
    if (out) await pg.screenshot({ path: path.join(out, `${String(i).padStart(2, "0")}_${scheme}_${w}.png`) });
    await ctx.close();
  }
  console.log(errs.length ? errs.join("\n") : `Sin errores en ${routes.length} rutas.`);
  await b.close(); srv.close(); process.exit(errs.length ? 1 : 0);
});
