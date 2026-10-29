import { route } from "../app.js";
import { S } from "../store.js";
import { h, imgSrc } from "../util.js";
import { head, sec, T, openPhoto } from "./common.js";
import { race } from "../race.js";

route("fotos", async () => {
  const page = h("div.wrap.page");
  const seen = new Set(), items = [];
  const add = (ph, title) => { if (!ph || seen.has(ph.img)) return; seen.add(ph.img); items.push({ ph, title }); };
  (S.fotos.general || []).forEach((p) => add(p, "La categoría"));
  S.ascensos.slice().reverse().forEach((a) => add(S.photo(a.key), `${T(a.t).short} · ${a.season.label}`));
  Object.entries(S.fotos.clubs || {}).forEach(([slug, p]) => add(p, T(S.teamBy.get(slug))?.short));
  page.append(head("Fotos", "La categoría en imágenes", "Imágenes libres de Wikimedia Commons. Cada una muestra su autor y licencia al abrirla."));
  page.append(items.length ? h("div.gallery", items.map(({ ph, title }) => h("figure", [h("button", { type: "button", "aria-label": "Ampliar: " + ph.caption, onclick: () => openPhoto(ph, title) }, h("img", { src: imgSrc(ph.img), alt: ph.alt || ph.caption, loading: "lazy", decoding: "async" })), h("figcaption", [h("b", title), h("span", ph.caption)])]))) : h("p.muted", "Todavía no hay fotos cargadas."));
  return { page, title: "Fotos" };
});

route("videos", async () => {
  const page = h("div.wrap.page");
  page.append(head("Videos", "Finales, festejos y ascensos", "Los videos se ven en YouTube; el botón abre cada uno en una pestaña nueva."));
  const vs = S.videos || [];
  page.append(vs.length ? h("div.vgrid", vs.map((v) => h("a.vcard", { href: `https://www.youtube.com/watch?v=${v.id}`, target: "_blank", rel: "noopener" }, [h("div.vcard__img", [h("img", { src: imgSrc(`assets/img/videos/${v.id}.jpg`), alt: "", loading: "lazy" }), h("span.vcard__play", { "aria-hidden": "true" }, "▶")]), h("div.vcard__txt", [h("b", v.title), h("span", v.year)])]))) : h("p.muted", "Todavía no hay videos cargados."));
  page.append(h("p.cap", "Los videos son de terceros y están en YouTube. Este sitio solo enlaza."));
  return { page, title: "Videos" };
});

route("carrera", async () => {
  const page = h("div.wrap.page");
  page.append(head("La carrera", "La tabla histórica en movimiento", "Puntos acumulados de cada club desde 1986/87. Dale al play, mové la barra o cambiá la velocidad."), h("div.sec", race({ rows: 14, autoplay: false })));
  return { page, title: "La carrera" };
});
