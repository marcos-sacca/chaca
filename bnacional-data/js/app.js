import { S, load, search } from "./store.js";
import { h, el$, debounce } from "./util.js";
import { supportButtons, mailto } from "./views/common.js";

const routes = new Map();
export const route = (name, fn) => routes.set(name, fn);
const app = el$("app"), nav = el$("nav");

async function boot() {
  app.append(h("div.wrap.page", h("p.muted", "Cargando 40 años de ascensos…")));
  try { await load(); } catch (e) { app.replaceChildren(h("div.wrap.page", h("h2", "No se pudieron cargar los datos"), h("p", e.message))); return; }
  await Promise.all(["home", "ascensos", "seasons", "clubs", "tabla", "scorers", "gallery", "about", "admin"].map((v) => import(`./views/${v}.js`)));
  footer(); finder(); menu();
  addEventListener("hashchange", go); go();
}
function parse() {
  const raw = location.hash.replace(/^#/, ""), m = /^([a-z]+)(?:-(.+))?$/.exec(raw);
  return { name: m ? m[1] : "inicio", arg: m ? m[2] : undefined };
}
let first = true;
async function go() {
  const r = parse(); let fn = routes.get(r.name) || routes.get("inicio");
  el$("lightbox").open && el$("lightbox").close();
  nav.classList.remove("open"); el$("menubtn").setAttribute("aria-expanded", "false");
  const res = await fn(r);
  const page = res.page; page.classList.add("pagein");
  [...page.children].slice(0, 14).forEach((c, i) => c.style.setProperty("--i", i));
  app.replaceChildren(page);
  document.title = (res.title ? res.title + " · " : "") + "B Nacional Histórica";
  if (!first) scrollTo({ top: 0, behavior: "instant" }); first = false;
  const key = { inicio: "inicio", ascensos: "ascensos", temporadas: "temporadas", t: "temporadas", clubes: "clubes", c: "clubes", tabla: "tabla", goleadores: "goleadores", fotos: "fotos", videos: "fotos", admin: "fotos", carrera: "carrera", datos: "datos" }[routes.has(r.name) ? r.name : "inicio"];
  nav.querySelectorAll("a").forEach((a) => { if (a.dataset.nav === key) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current"); });
}
function footer() {
  const m = S.meta;
  el$("foot").append(h("div.wrap.foot__in", [h("p", [h("b", "B Nacional Histórica"), ` reúne ${m.partidos.toLocaleString("es-AR")} partidos de la Primera B Nacional y la Primera Nacional, de 1986/87 a ${m.ultimo.slice(0, 4)}.`]), h("p.muted", ["Proyecto de hinchas, sin vínculo con la AFA. ", h("a", { href: "#datos" }, "Fuentes, controles y créditos de las fotos"), "."]), h("div.foot__help", [h("span", "¿Tenés material de tu club?"), h("a.btn.btn--ghost.btn--s", { href: mailto("") }, "Mandalo por mail"), ...supportButtons().map((b) => { b.classList.add("btn--s"); return b; }), h("a.foot__adm", { href: "#admin" }, "Admin")])]));
}
function menu() { const b = el$("menubtn"); b.addEventListener("click", () => { const o = nav.classList.toggle("open"); b.setAttribute("aria-expanded", String(o)); }); }
function finder() {
  const dlg = el$("finder"), q = el$("finderq"), list = el$("finderlist"); let res = [];
  const open = () => { if (!dlg.open) dlg.showModal(); q.value = ""; list.replaceChildren(); q.focus(); };
  el$("searchbtn").addEventListener("click", open);
  addEventListener("keydown", (e) => { if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") { e.preventDefault(); open(); } });
  q.addEventListener("input", debounce(() => {
    res = search(q.value, 12);
    list.replaceChildren(...(res.length ? res.map((r) => h("li", h("a.sug", { href: r.href, onclick: () => dlg.close() }, [h("span.sug__k", r.k), h("span.sug__n", r.n), h("span.sug__d", r.d)]))) : [h("li.finder__empty", q.value ? "Sin resultados." : "Escribí un club, una temporada o un goleador.")]));
  }, 60));
  dlg.addEventListener("click", (e) => { if (e.target === dlg) dlg.close(); });
}
el$("lightbox").addEventListener("click", (e) => { if (e.target === e.currentTarget || e.target.closest("[data-close]")) e.currentTarget.close(); });
// progreso de lectura e inclinación de las tarjetas
const prog = el$("progress");
const onScroll = () => { const d = document.documentElement; prog.style.setProperty("--p", (scrollY / Math.max(1, d.scrollHeight - innerHeight)).toFixed(4)); };
addEventListener("scroll", onScroll, { passive: true }); addEventListener("resize", onScroll);
if (!matchMedia("(prefers-reduced-motion: reduce)").matches && matchMedia("(hover: hover)").matches) {
  addEventListener("pointermove", (e) => {
    const c = e.target.closest?.(".acard, .scard"); if (!c) return;
    const r = c.getBoundingClientRect(), x = (e.clientX - r.left) / r.width, y = (e.clientY - r.top) / r.height;
    c.style.setProperty("--ry", ((x - .5) * 9).toFixed(2) + "deg"); c.style.setProperty("--rx", ((.5 - y) * 9).toFixed(2) + "deg"); c.style.setProperty("--mx", x * 100 + "%"); c.style.setProperty("--my", y * 100 + "%");
  }, { passive: true });
  addEventListener("pointerout", (e) => { const c = e.target.closest?.(".acard, .scard"); if (c && !c.contains(e.relatedTarget)) { c.style.removeProperty("--rx"); c.style.removeProperty("--ry"); } });
}
boot();
