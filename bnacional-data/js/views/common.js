import { h, imgSrc, el$ } from "../util.js";
import { S } from "../store.js";

export const T = (i) => S.teams[i];
export const href = { club: (i) => `#c-${S.teams[i].s}`, season: (si) => `#t-${S.seasons[si].id}` };
export const initials = (name) => { const w = name.replace(/\(.*?\)/g, "").split(/\s+/).filter((x) => x.length > 2 && !/^(de|del|la|el|los|las|club|atl[eé]tico|deportivo)$/i.test(x)); return (w.length > 1 ? w[0][0] + w[1][0] : (w[0] || name).slice(0, 2)).toUpperCase(); };

export function crest(ti, cls = "") {
  const c = S.crest(ti);
  return c ? h("img.crest" + (cls ? "." + cls : ""), { src: imgSrc(c.img), alt: "Escudo de " + T(ti).short, loading: "lazy", decoding: "async" }) : monogram(ti, "mono--s");
}
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
  const t = T(a.t);
  const champ = a.how === "Campeón";
  const cr = S.crest(a.t);
  const media = cr ? h("div.acard__crest", h("img", { src: imgSrc(cr.img), alt: "Escudo de " + t.short, loading: "lazy", decoding: "async" })) : monogram(a.t);
  const card = h("button.acard" + (compact ? ".acard--c" : ""), { type: "button", "aria-label": `${t.n}, ${champ ? "campeón" : "ascenso"} ${a.season.label}`, onclick: () => openCard(a) }, [
    h("div.acard__img", [media, h("span.acard__badge" + (champ ? ".is-champ" : ""), champ ? "Campeón" : "Ascenso")]),
    h("div.acard__txt", [h("b", t.short), h("span", a.season.label)]),
  ]);
  return card;
}
export function openCard(a) {
  const t = T(a.t), dlg = el$("lightbox"), body = el$("lightbody"), cr = S.crest(a.t);
  const champ = a.how === "Campeón";
  body.replaceChildren(
    h("div.lb__media", cr ? h("div.lb__crest", h("img", { src: imgSrc(cr.img), alt: "Escudo de " + t.short })) : monogram(a.t, "mono--xl")),
    h("div.lb__info", [
      h("p.eyebrow", `${champ ? "Campeón y ascenso" : "Ascenso a Primera División"} · ${a.season.label}`),
      h("h3", t.n),
      h("p.lb__cap", `${t.short} ${champ ? "fue campeón de" : "ascendió a Primera en"} la temporada ${a.season.label}${champ ? " y ascendió a Primera División" : ""}.`),
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

const POSN = { arquero: "Arqueros", defensor: "Defensores", mediocampista: "Mediocampistas", delantero: "Delanteros", null: "Otros" };
// plantel del club que ascendió: formación de Solo Ascenso (2014 en adelante) o, antes, los goleadores del equipo
export function plantelBox(a) {
  const pl = S.planteles[a.key], t = T(a.t);
  if (pl) {
    const groups = new Map();
    for (const j of pl.jug) { const k = j[1] || "null"; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(j); }
    return h("details.plantel", [h("summary", `Plantel de ${t.short} ${a.season.label}`), h("div.plantel__in", [
      h("p.cap", `${pl.dt ? "DT: " + pl.dt + ". " : ""}${pl.jug.length} jugadores usados en ${pl.pj} partidos de la fase regular. Datos de Solo Ascenso.`),
      ...["arquero", "defensor", "mediocampista", "delantero", "null"].filter((k) => groups.has(k)).map((k) => h("div.plantel__g", [h("h4", POSN[k]), h("ul", groups.get(k).map((j) => h("li", [h("span", j[0]), h("small", `${j[2]} PJ${j[4] ? ` · ${j[4]} ${j[4] === 1 ? "gol" : "goles"}` : ""}`)])))]))])]);
  }
  const si = S.seasonBy.get(a.season.id), sc = Object.values(S.scBySeason[si] || {}).filter((o) => o.team === a.t).sort((x, y) => y.g - x.g);
  if (!sc.length) return null;
  return h("details.plantel", [h("summary", `Goleadores de ${t.short} ${a.season.label}`), h("div.plantel__in", [h("p.cap", "De esta temporada no hay formaciones publicadas; estos son los jugadores que convirtieron."), h("div.plantel__g", h("ul", sc.map((o) => h("li", [h("span", o.name), h("small", `${o.g} ${o.g === 1 ? "gol" : "goles"}`)]))))])]);
}
