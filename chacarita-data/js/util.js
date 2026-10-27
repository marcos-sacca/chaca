// Utilidades chicas: DOM, formatos en español rioplatense, animaciones y tooltip.

export const MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
export const DIAS = ["domingo", "lunes", "martes", "miércoles", "jueves", "viernes", "sábado"];
const nf = new Intl.NumberFormat("es-AR");
export const n = (x) => (x == null || Number.isNaN(x) ? "—" : nf.format(x));
export const pct = (x, d = 0) => (x == null || Number.isNaN(x) ? "—" : (x * 100).toFixed(d).replace(".", ",") + "%");
export const signed = (x) => (x > 0 ? "+" + n(x) : n(x));

/** h("div.clase#id", {atributos, onclick}, ...hijos). Los textos van como texto (nunca como HTML). */
export function h(tag, attrs, ...kids) {
  const m = /^([a-z0-9]+)?((?:[.#][\w-]+)*)$/i.exec(tag);
  const el = document.createElement(m[1] || "div");
  for (const part of (m[2] || "").match(/[.#][\w-]+/g) || []) {
    if (part[0] === ".") el.classList.add(part.slice(1)); else el.id = part.slice(1);
  }
  if (attrs && (typeof attrs !== "object" || attrs instanceof Node || Array.isArray(attrs))) { kids.unshift(attrs); attrs = null; }
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v == null || v === false) continue;
    if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else if (k === "class") el.className += " " + v;
    else if (k === "html") el.innerHTML = v; // solo para HTML propio y estático
    else if (k === "style" && typeof v === "object") Object.assign(el.style, v);
    else if (k in el && k !== "list" && k !== "href" && k !== "role") { try { el[k] = v; } catch { el.setAttribute(k, v); } }
    else el.setAttribute(k, v === true ? "" : v);
  }
  const add = (c) => {
    if (c == null || c === false) return;
    if (Array.isArray(c)) c.forEach(add);
    else el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  };
  kids.forEach(add);
  return el;
}

export const svg = (tag, attrs = {}, ...kids) => {
  const el = document.createElementNS("http://www.w3.org/2000/svg", tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) el.setAttribute(k, v);
  kids.flat().forEach((c) => c != null && el.append(c instanceof Node ? c : document.createTextNode(String(c))));
  return el;
};

export const norm = (s) => String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9 ]/g, " ").replace(/\s+/g, " ").trim();
export const slug = (s) => encodeURIComponent(String(s));
export const unslug = (s) => decodeURIComponent(s);

export function parseISO(d) { const [y, m, dd] = d.split("-").map(Number); return new Date(y, m - 1, dd); }
export const dShort = (d) => { const [y, m, dd] = d.split("-"); return `${dd}/${m}/${y}`; };
export const dLong = (d) => { const [y, m, dd] = d.split("-").map(Number); return `${dd} de ${MESES[m - 1]} de ${y}`; };
export const dDay = (d) => `${DIAS[parseISO(d).getDay()]} ${Number(d.slice(8))} de ${MESES[Number(d.slice(5, 7)) - 1]}`;

export const debounce = (fn, ms = 120) => { let t; return (...a) => { clearTimeout(t); t = setTimeout(() => fn(...a), ms); }; };
export const reduced = () => matchMedia("(prefers-reduced-motion: reduce)").matches;

/** Cuenta de 0 al valor (se salta con movimiento reducido). */
export function countUp(el, to, { ms = 1100, fmt = n } = {}) {
  if (reduced() || to < 12) { el.textContent = fmt(to); return; }
  const t0 = performance.now();
  const step = (t) => {
    const k = Math.min(1, (t - t0) / ms), e = 1 - Math.pow(1 - k, 4);
    el.textContent = fmt(Math.round(to * e));
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

/** Muestra los elementos [data-reveal] a medida que entran en pantalla. */
export function revealAll(root = document) {
  const els = [...root.querySelectorAll("[data-reveal]")];
  if (!("IntersectionObserver" in window) || reduced()) { els.forEach((e) => e.classList.add("in-view")); return; }
  const io = new IntersectionObserver((es) => es.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in-view"); io.unobserve(e.target); } }), { rootMargin: "0px 0px -6% 0px" });
  els.forEach((e, i) => { e.style.setProperty("--i", Math.min(i % 8, 7)); io.observe(e); });
}

// ---- tooltip único (accesible: el mismo contenido sale por foco y por la tabla)
let tipEl, tipTimer;
export function tip(target, build) {
  tipEl ||= document.getElementById("tip");
  const show = (x, y) => {
    clearTimeout(tipTimer);
    tipEl.replaceChildren(...[].concat(build()));
    tipEl.hidden = false;
    const w = tipEl.offsetWidth;
    const cx = Math.max(w / 2 + 8, Math.min(innerWidth - w / 2 - 8, x));
    tipEl.style.left = cx + "px"; tipEl.style.top = Math.max(60, y) + "px";
  };
  const hide = () => { tipTimer = setTimeout(() => (tipEl.hidden = true), 40); };
  target.addEventListener("pointermove", (e) => show(e.clientX, e.clientY));
  target.addEventListener("pointerleave", hide);
  target.addEventListener("focus", () => { const r = target.getBoundingClientRect(); show(r.left + r.width / 2, r.top); });
  target.addEventListener("blur", hide);
}

export const resLabel = { G: "Ganó", E: "Empató", P: "Perdió" };
export const resChip = (r, extra = "") => h(`span.res.res--${r}`, { title: resLabel[r], "aria-label": resLabel[r] }, r, extra);
