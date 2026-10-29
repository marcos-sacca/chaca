// helpers de DOM y formato
export function h(sel, attrs, kids) {
  const m = /^([a-z0-9]+)?((?:[.#][\w-]+)*)$/i.exec(sel);
  const el = document.createElement(m[1] || "div");
  for (const t of (m[2].match(/[.#][\w-]+/g) || [])) t[0] === "." ? el.classList.add(t.slice(1)) : (el.id = t.slice(1));
  if (attrs !== undefined && (typeof attrs !== "object" || attrs === null || Array.isArray(attrs) || attrs instanceof Node)) { kids = attrs; attrs = {}; }
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "style" && typeof v === "object") { for (const [kk, vv] of Object.entries(v)) kk.startsWith("--") ? el.style.setProperty(kk, vv) : (el.style[kk] = vv); }
    else if (k === "html") el.innerHTML = v;
    else if (v === true) el.setAttribute(k, "");
    else el.setAttribute(k, v);
  }
  for (const c of [].concat(kids ?? []).flat(Infinity)) if (c != null && c !== false) el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  return el;
}
export const n = (x) => (x ?? 0).toLocaleString("es-AR");
export const norm = (s) => String(s).normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
export const imgSrc = (p) => (window.__IMG && window.__IMG[p]) || p;
export const el$ = (id) => document.getElementById(id);
export function debounce(fn, ms) { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; }
export const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
export const fdate = (iso) => { const [y, m, d] = iso.split("-").map(Number); return `${d} de ${MESES[m - 1]} de ${y}`; };
export const fshort = (iso) => { const [y, m, d] = iso.split("-"); return `${d}/${m}/${y.slice(2)}`; };
export function countUp(el, to, ms = 900) {
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) { el.textContent = n(to); return; }
  const t0 = performance.now();
  const f = (t) => { const k = Math.min(1, (t - t0) / ms); el.textContent = n(Math.round(to * (1 - Math.pow(1 - k, 3)))); if (k < 1) requestAnimationFrame(f); };
  requestAnimationFrame(f);
}
