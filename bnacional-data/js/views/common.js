import { h, imgSrc, el$ } from "../util.js";
import { S } from "../store.js";

export const T = (i) => S.teams[i];
export const href = { club: (i) => `#c-${S.teams[i].s}`, season: (si) => `#t-${S.seasons[si].id}` };
export const initials = (name) => { const w = name.replace(/\(.*?\)/g, "").split(/\s+/).filter((x) => x.length > 2 && !/^(de|del|la|el|los|las|club|atl[eé]tico|deportivo)$/i.test(x)); return (w.length > 1 ? w[0][0] + w[1][0] : (w[0] || name).slice(0, 2)).toUpperCase(); };

export function monogram(ti, cls = "") {
  return h("div.mono" + (cls ? "." + cls : ""), { "aria-hidden": "true" }, h("span", initials(T(ti).short)));
}
export function pill(text, kind = "") { return h("span.pill" + (kind ? "." + kind : ""), text); }
export function head(eyebrow, title, lead) {
  return h("header.phead", [eyebrow ? h("p.eyebrow", eyebrow) : null, h("h1", title), lead ? h("p.lead", lead) : null]);
}
export function sec(title, kids, right) {
  return h("section.sec", [h("div.sec__head", [h("h2", title), right || null]), kids]);
}
export function photoFor(a) {
  // foto de la temporada si existe; si no, la del club
  return S.photo(a.key) || S.clubPhoto(S.teams[a.t].s) || null;
}
export function ascCard(a, { compact = false } = {}) {
  const ph = photoFor(a), t = T(a.t);
  const champ = a.how === "Campeón";
  const media = ph ? h("img", { src: imgSrc(ph.img), alt: ph.alt || `${t.n}`, loading: "lazy", decoding: "async" }) : monogram(a.t);
  const card = h("button.acard" + (compact ? ".acard--c" : ""), { type: "button", "aria-label": `${t.n}, ${champ ? "campeón" : "ascenso"} ${a.season.label}`, onclick: () => openCard(a) }, [
    h("div.acard__img", [media, h("span.acard__badge" + (champ ? ".is-champ" : ""), champ ? "Campeón" : "Ascenso")]),
    h("div.acard__txt", [h("b", t.short), h("span", a.season.label)]),
  ]);
  return card;
}
export function openCard(a) {
  const ph = photoFor(a), t = T(a.t), dlg = el$("lightbox"), body = el$("lightbody");
  const champ = a.how === "Campeón";
  body.replaceChildren(
    h("div.lb__media", ph ? h("img", { src: imgSrc(ph.img), alt: ph.alt || t.n }) : monogram(a.t, "mono--xl")),
    h("div.lb__info", [
      h("p.eyebrow", `${champ ? "Campeón y ascenso" : "Ascenso a Primera División"} · ${a.season.label}`),
      h("h3", t.n),
      ph ? h("p.lb__cap", ph.caption) : h("p.lb__cap", "Todavía no hay una foto libre de este club."),
      ph ? h("p.lb__cred", [ph.kind === "temporada" ? "Foto de la temporada. " : "Foto del club. ", ph.author ? ph.author + " · " : "", ph.lic, " · ", h("a", { href: ph.page, target: "_blank", rel: "noopener" }, "Wikimedia Commons")]) : null,
      h("div.lb__links", [h("a.btn", { href: href.season(a.si), onclick: () => dlg.close() }, `Temporada ${a.season.label}`), h("a.btn.btn--ghost", { href: href.club(a.t), onclick: () => dlg.close() }, `Historia de ${t.short}`)]),
    ]));
  if (!dlg.open) dlg.showModal();
}
export function openPhoto(ph, title) {
  const dlg = el$("lightbox"), body = el$("lightbody");
  body.replaceChildren(h("div.lb__media", h("img", { src: imgSrc(ph.img), alt: ph.alt || title || "" })), h("div.lb__info", [
    title ? h("p.eyebrow", title) : null, h("p.lb__cap", ph.caption),
    h("p.lb__cred", [ph.author ? ph.author + " · " : "", ph.lic, " · ", h("a", { href: ph.page, target: "_blank", rel: "noopener" }, "Wikimedia Commons")])]));
  if (!dlg.open) dlg.showModal();
}
export function table(cols, rows, { cls = "" } = {}) {
  return h("div.tablewrap", h("table.tbl" + (cls ? "." + cls : ""), [
    h("thead", h("tr", cols.map((c) => h("th", { class: c.cls || "", scope: "col", title: c.title || null }, c.label)))),
    h("tbody", rows),
  ]));
}
