import { route } from "../app.js";
import { S } from "../store.js";
import { h, imgSrc } from "../util.js";
import { head, sec, T, openPhoto, crest, href, helpBox, mailto } from "./common.js";
import { hasLocal } from "../store.js";
import { race } from "../race.js";

route("fotos", async () => {
  const page = h("div.wrap.page");
  const clubs = Object.entries(S.galeria.clubs || {}).map(([slug, L]) => ({ slug, ti: S.teamBy.get(slug), L })).filter((c) => c.ti != null).sort((a, b) => T(a.ti).short.localeCompare(T(b.ti).short));
  const nfotos = clubs.reduce((n, c) => n + c.L.length, 0);
  const sel = h("select#gsel", { "aria-label": "Ir a un club", onchange: (e) => { const el = document.getElementById("g-" + e.target.value); if (el) el.scrollIntoView({ behavior: "smooth", block: "start" }); } }, [h("option", { value: "" }, "Ir a un club…"), ...clubs.map((c) => h("option", { value: c.slug }, `${T(c.ti).short} (${c.L.length})`))]);
  page.append(head("Fotos", "Las fotos, club por club", `${nfotos} imágenes agrupadas por club, de Wikimedia Commons (licencia libre) y aportes de hinchas. Cada una muestra su autor y licencia al abrirla.`), h("div.gnav", [sel, h("a.btn.btn--ghost", { href: "#videos" }, "Ver videos")]));
  if (hasLocal()) page.append(h("p.adm__note", ["Estás viendo cambios locales sin publicar. ", h("a", { href: "#admin" }, "Abrir la administración")]));
  page.append(helpBox(""));
  for (const c of clubs) {
    page.append(h("section.gclub", { id: "g-" + c.slug }, [
      h("div.gclub__h", [crest(c.ti), h("h2", T(c.ti).n), h("a.link", { href: href.club(c.ti) }, "Historia del club →")]),
      h("div.gallery", c.L.map((ph) => h("figure", [h("button", { type: "button", "aria-label": "Ampliar: " + ph.caption, onclick: () => openPhoto(ph, T(c.ti).short) }, h("img", { src: imgSrc(ph.img), alt: ph.alt || ph.caption, loading: "lazy", decoding: "async" })), h("figcaption", [h("b", ph.kind === "temporada" ? "De la temporada" : ph.kind === "general" ? "Partido" : "Del club"), h("span", ph.caption)])]))),
    ]));
  }
  const sin = S.teams.map((t, ti) => ({ t, ti })).filter(({ t }) => !(S.galeria.clubs[t.s] || []).length).sort((a, b) => a.t.short.localeCompare(b.t.short));
  if (sin.length) page.append(h("details.fold.gsin", [h("summary", `${sin.length} clubes todavía no tienen fotos: ayudanos a completarlos`), h("div.cgrid", sin.map(({ t, ti }) => h("a.ccard.ccard--s", { href: mailto(t.n), title: "Mandar fotos de " + t.n }, [crest(ti), h("span.ccard__t", [h("b", t.short), h("small", "Mandar fotos ✉")])])))]));
  return { page, title: "Fotos" };
});

const TIPOS = [["goles", "Compilados de goles", "Todos los goles de cada fecha y resúmenes de la B Nacional."], ["final", "Finales, festejos y ascensos", "Los partidos que definieron los ascensos."], ["partido", "Partidos de archivo", "Encuentros completos de la historia de la categoría."]];
route("videos", async () => {
  const page = h("div.wrap.page"), vs = S.videos || [];
  page.append(head("Videos", "Goles, finales y ascensos", `${vs.length} videos. Se ven en YouTube; cada uno abre en una pestaña nueva.`));
  const card = (v) => h("a.vcard", { href: `https://www.youtube.com/watch?v=${v.id}`, target: "_blank", rel: "noopener" }, [h("div.vcard__img", [h("img", { src: imgSrc(`assets/img/videos/${v.id}.jpg`), alt: "", loading: "lazy", onerror: (e) => { if (!e.target.dataset.f) { e.target.dataset.f = 1; e.target.src = `https://i.ytimg.com/vi/${v.id}/hqdefault.jpg`; } else e.target.style.visibility = "hidden"; } }), h("span.vcard__play", { "aria-hidden": "true" }, "▶")]), h("div.vcard__txt", [h("b", v.title), h("span", [v.year, v.club && S.teamBy.get(v.club) != null ? ` · ${T(S.teamBy.get(v.club)).short}` : ""])])]);
  for (const [k, title, desc] of TIPOS) {
    const L = vs.filter((v) => v.tipo === k); if (!L.length) continue;
    if (k === "final") { // por club
      const by = new Map(); for (const v of L) { const key = v.club || "otros"; if (!by.has(key)) by.set(key, []); by.get(key).push(v); }
      page.append(h("section.vgroup", [h("h2", title), h("p.muted", desc), ...[...by.entries()].sort((a, b) => (S.teamBy.has(a[0]) ? T(S.teamBy.get(a[0])).short : "zz").localeCompare(S.teamBy.has(b[0]) ? T(S.teamBy.get(b[0])).short : "zz")).map(([club, V]) => h("div", { style: { marginTop: "22px" } }, [S.teamBy.has(club) ? h("div.gclub__h", [crest(S.teamBy.get(club)), h("h3", T(S.teamBy.get(club)).n)]) : null, h("div.vgrid", { style: { marginTop: "0" } }, V.map(card))]))]));
    } else page.append(h("section.vgroup", [h("h2", title), h("p.muted", desc), h("div.vgrid", { style: { marginTop: "0" } }, L.map(card))]));
  }
  page.append(helpBox(""), h("p.cap", "Los videos son de terceros y están en YouTube. Este sitio solo enlaza."));
  return { page, title: "Videos" };
});

route("carrera", async () => {
  const page = h("div.wrap.page");
  page.append(head("La carrera", "La tabla histórica en movimiento", "Puntos acumulados de cada club desde 1986/87. Dale al play, mové la barra o cambiá la velocidad."), h("div.sec", race({ rows: 14, autoplay: false })));
  return { page, title: "La carrera" };
});
