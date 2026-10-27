import { S, load, searchIndex, search } from "./store.js";
import { h, revealAll, debounce } from "./util.js";

const routes = new Map();
export const route = (name, fn) => routes.set(name, fn);

const app = document.getElementById("app");
const nav = document.getElementById("nav");
const ink = nav.querySelector(".nav__ink");
let idx = null;

async function boot() {
  app.append(h("div.wrap.page", h("p.muted", "Cargando 95 años de historia…")));
  try { await load(); } catch (e) { app.replaceChildren(h("div.wrap.page", h("h2", "No se pudieron cargar los datos"), h("p", "Probá recargar la página. Detalle: " + e.message))); return; }
  idx = searchIndex();
  await Promise.all(["home", "rivals", "matches", "players", "seasons", "records", "otd", "about"].map((v) => import(`./views/${v}.js`)));
  buildFooter(); setupFinder(); setupMenu();
  addEventListener("hashchange", go);
  go();
}

function parse() {
  const raw = location.hash.replace(/^#\/?/, "");
  const [path, qs] = raw.split("?");
  const parts = path.split("/").filter(Boolean).map(decodeURIComponent);
  return { name: parts[0] || "inicio", arg: parts[1], arg2: parts[2], q: Object.fromEntries(new URLSearchParams(qs || "")) };
}

let first = true;
async function go() {
  const r = parse();
  const fn = routes.get(r.name) || routes.get("inicio");
  document.getElementById("nav").classList.remove("open"); document.getElementById("menubtn").setAttribute("aria-expanded", "false");
  const page = h("div.pagein");
  const res = await fn(r, page);
  if (res && res.title) document.title = res.title + " · chacarita-data"; else document.title = "chacarita-data";
  app.replaceChildren(page);
  if (!first || r.name !== "inicio") scrollTo({ top: 0, behavior: "instant" });
  first = false;
  markNav(r.name);
  revealAll(page);
  if (!location.hash.startsWith("#/partidos")) app.focus({ preventScroll: true });
}

function markNav(name) {
  const key = { rivales: "rivales", partidos: "partidos", partido: "partidos", jugadores: "jugadores", temporadas: "temporadas", records: "records", efemerides: "efemerides" }[name];
  let cur = null;
  nav.querySelectorAll("a").forEach((a) => { const on = a.dataset.nav === key; a.toggleAttribute("aria-current", on); if (on) { a.setAttribute("aria-current", "page"); cur = a; } else a.removeAttribute("aria-current"); });
  if (cur) { ink.style.width = cur.offsetWidth - 24 + "px"; ink.style.transform = `translateX(${cur.offsetLeft + 12}px)`; } else ink.style.width = "0";
}

function buildFooter() {
  const m = S.meta;
  document.getElementById("foot").append(h("div.foot__in", [
    h("div", [
      h("p", [h("b", "chacarita-data"), ` reúne ${m.partidos.toLocaleString("es-AR")} partidos oficiales de Chacarita Juniors entre 1931 y 2026, con sus goles y formaciones. Datos actualizados al ${new Date(m.ultimo_partido + "T12:00").toLocaleDateString("es-AR", { day: "numeric", month: "long", year: "numeric" })}.`]),
      h("p", ["Proyecto de hinchas, sin vínculo oficial con el club. ", h("a", { href: "#/datos" }, "De dónde sale cada dato y qué falta"), "."]),
    ]),
    h("div", [h("p.muted", "Fuentes: la planilla DATACHACA Máster, Historical-Lineups y RSSSF. Fotos de Wikimedia Commons (créditos en cada imagen)."), h("p", h("a", { href: "#/datos" }, "Ver créditos y fuentes"))]),
  ]));
}

function setupMenu() {
  const b = document.getElementById("menubtn");
  b.addEventListener("click", () => { const o = nav.classList.toggle("open"); b.setAttribute("aria-expanded", String(o)); });
}

function setupFinder() {
  const dlg = document.getElementById("finder"), q = document.getElementById("finderq"), list = document.getElementById("finderlist");
  let sel = -1, res = [];
  const open = () => { if (!dlg.open) dlg.showModal(); q.value = ""; list.replaceChildren(); sel = -1; q.focus(); };
  document.getElementById("searchbtn").addEventListener("click", open);
  addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); open(); } if (e.key === "/" && !/input|textarea|select/i.test(document.activeElement.tagName)) { e.preventDefault(); open(); } });
  const draw = () => {
    res = search(q.value, idx, 12);
    list.replaceChildren(...(res.length ? res.map((r, i) => h("li", { role: "option", "aria-selected": i === sel }, h("button.sug", { type: "button", onclick: () => pick(i) }, [h("span.sug__k", r.k), h("span.sug__n", r.n), h("span.sug__d", r.d)]))) : [q.value ? h("li.finder__empty", "Sin resultados. Probá con otro nombre.") : h("li.finder__empty", "Escribí un rival (Boca), un jugador (Coll), un año (1969) o un torneo.")]));
  };
  const pick = (i) => { dlg.close(); location.hash = res[i].href; };
  q.addEventListener("input", debounce(() => { sel = res.length ? 0 : -1; draw(); }, 60));
  q.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { e.preventDefault(); sel = Math.min(res.length - 1, sel + 1); draw(); }
    else if (e.key === "ArrowUp") { e.preventDefault(); sel = Math.max(0, sel - 1); draw(); }
    else if (e.key === "Enter" && res[Math.max(sel, 0)]) { e.preventDefault(); pick(Math.max(sel, 0)); }
  });
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
}

export function suggestBox(input, onPick) {
  const box = h("ul.suggest", { hidden: true, role: "listbox" });
  let res = [], sel = 0;
  const draw = () => {
    res = search(input.value, idx, 7); sel = 0;
    box.hidden = !res.length;
    box.replaceChildren(...res.map((r, i) => h("li", h("button.sug", { type: "button", "aria-selected": i === 0, onclick: () => onPick(r) }, [h("span.sug__k", r.k), h("span.sug__n", r.n), h("span.sug__d", r.d)]))));
  };
  input.addEventListener("input", draw);
  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter" && res[sel]) { e.preventDefault(); onPick(res[sel]); }
    else if (e.key === "ArrowDown" || e.key === "ArrowUp") { e.preventDefault(); sel = (sel + (e.key === "ArrowDown" ? 1 : -1) + res.length) % res.length; [...box.querySelectorAll(".sug")].forEach((b, i) => b.setAttribute("aria-selected", i === sel)); }
    else if (e.key === "Escape") box.hidden = true;
  });
  input.addEventListener("blur", () => setTimeout(() => (box.hidden = true), 160));
  return box;
}

boot();
