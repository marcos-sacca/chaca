import { route } from "../app.js";
import { S, clubSeason } from "../store.js";
import { h, n, norm, imgSrc } from "../util.js";
import { ascCard, head, sec, table, T, href, monogram, crest, plantelBox, openPhoto, helpBox } from "./common.js";
import { effLine } from "../charts.js";

const st = { q: "" };
route("clubes", async () => {
  const page = h("div.wrap.page"), grid = h("div.cgrid");
  const rows = S.general.map((r) => ({ ti: r[1], seasons: r[2], pj: r[3], pts3: r[12], asc: r[13], desc: r[14], red: r[15] }));
  const draw = () => {
    const f = norm(st.q), list = rows.filter((r) => !f || norm(T(r.ti).n).includes(f));
    grid.replaceChildren(...list.map((r) => h("a.ccard", { href: href.club(r.ti) }, [crest(r.ti), h("span.ccard__t", [h("b", T(r.ti).short), h("small", `${r.seasons} ${r.seasons === 1 ? "temporada" : "temporadas"} · ${n(r.pj)} partidos`), h("span.ccard__k", [h("i.k.k--up", { title: "Ascensos" }, `↑ ${r.asc}`), h("i.k.k--down", { title: "Descensos" }, `↓ ${r.desc}`), h("i.k.k--red", { title: "Reducidos jugados" }, `⟳ ${r.red}`)])])])));
    if (!list.length) grid.append(h("p.muted", "Ningún club coincide."));
  };
  page.append(head("Clubes", `${S.teams.length} clubes pasaron por la categoría`, "Ordenados por partidos jugados en la tabla histórica."), h("div.toolbar", h("input#cq", { type: "search", placeholder: "Buscar club", value: st.q, "aria-label": "Buscar club", oninput: (e) => { st.q = e.target.value; draw(); } })), grid);
  draw();
  return { page, title: "Clubes" };
});

route("c", async (r) => {
  const ti = S.teamBy.get(r.arg); if (ti == null) return { page: h("div.wrap.page", h("h1", "No encontré ese club")), title: "" };
  const t = T(ti), page = h("div.wrap.page");
  const g = S.general.find((x) => x[1] === ti);
  const asc = S.ascensos.filter((a) => a.t === ti);
  const cr = S.crest(ti);
  page.append(h("nav.crumbs", [h("a", { href: "#clubes" }, "Clubes"), " / ", t.short]));
  page.append(h("header.chead", [
    cr ? h("div.chead__crest", h("img", { src: imgSrc(cr.img), alt: "Escudo de " + t.short })) : monogram(ti, "mono--xl"),
    h("div", [h("p.eyebrow", t.prov || "Primera Nacional"), h("h1", t.n), h("p.lead", g ? `${g[2]} ${g[2] === 1 ? "temporada" : "temporadas"} en la categoría desde ${t.first || "1986/87"}${asc.length ? `, ${asc.length} ${asc.length === 1 ? "ascenso" : "ascensos"} a Primera` : ""}.` : "")]),
  ]));
  const cs = S.cs[ti];
  page.append(h("div.stats.stats--hi", [["Temporadas", g ? g[2] : 0, "En la categoría"], ["Ascensos", cs.asc.length, cs.champ ? `${cs.champ} como campeón` : "a Primera"], ["Descensos", cs.desc.length, "salidas de la categoría"], ["Reducidos", cs.red.length, cs.promo.length ? `y ${cs.promo.length} promociones` : "por el ascenso"]].map(([l, v, sub]) => h("div.stat", [h("b", n(v)), h("span", l), h("small", sub)]))));
  const seasonLine = (arr) => arr.map((si) => h("a.chipl", { href: href.season(si) }, S.seasons[si].label));
  if (cs.desc.length || cs.red.length || cs.promo.length) page.append(h("div.kline", [cs.desc.length ? h("p", [h("b", "Descendió en: "), ...seasonLine(cs.desc)]) : null, cs.red.length ? h("p", [h("b", "Jugó el reducido en: "), ...seasonLine(cs.red)]) : null, cs.promo.length ? h("p", [h("b", "Jugó promoción en: "), ...seasonLine(cs.promo)]) : null].filter(Boolean)));
  if (g) page.append(h("div.stats", [["PJ", g[3]], ["Ganados", g[4]], ["Empatados", g[5]], ["Perdidos", g[6]], ["Goles a favor", g[7]], ["Goles en contra", g[8]], ["Puntos (3 x victoria)", g[12]]].map(([l, v]) => h("div.stat", [h("b", n(v)), h("span", l)]))));
  // camino por temporadas
  const rows = [], pts = [];
  S.seasons.forEach((s, si) => { const c = clubSeason(ti, si); if (!c.pj) return; const up = asc.find((a) => a.si === si); rows.push({ si, s, c, up }); pts.push({ label: s.label.replace("Transición ", "T"), v: c.eff, up: !!up, si }); });
  page.append(sec("Camino por temporadas", [h("p.muted", "Puntos obtenidos sobre puntos posibles. El punto grande marca un ascenso."), effLine(pts, { onpick: (p) => (location.hash = `#t-${S.seasons[p.si].id}`) })]));
  page.append(sec("Temporada por temporada", table([{ label: "Temporada" }, ...["PJ", "PG", "PE", "PP", "GF", "GC"].map((l) => ({ label: l, cls: "num" })), { label: "Pts", cls: "num" }, { label: "" }],
    rows.slice().reverse().map(({ si, s, c, up }) => h("tr" + (up ? ".is-up" : ""), [h("td", h("a", { href: href.season(si) }, s.label)), ...[c.pj, c.pg, c.pe, c.pp, c.gf, c.gc].map((v) => h("td.num", v)), h("td.num", h("b", c.pts)), h("td", [up ? h("span.pill" + (up.how === "Campeón" ? ".pill--champ" : ""), up.how === "Campeón" ? "Campeón y ascenso" : "Ascenso") : null, S.cs[ti].desc.includes(si) ? h("span.pill.pill--down", "Descenso") : null, S.cs[ti].red.includes(si) ? h("span.pill.pill--red", "Reducido") : null, S.cs[ti].promo.includes(si) ? h("span.pill.pill--red", "Promoción") : null].filter(Boolean))])))));
  if (asc.length) page.append(sec("Ascensos", [h("div.agrid", asc.map((a) => ascCard(a))), h("div.plantels", asc.map((a) => plantelBox(a)))]));
  const gal = S.galeria.clubs?.[t.s] || [];
  if (gal.length) page.append(sec("Fotos", [h("div.rail", gal.slice(0, 12).map((ph) => h("button.acard.acard--c", { type: "button", onclick: () => openPhoto(ph, t.n), "aria-label": ph.caption }, [h("div.acard__img", h("img", { src: imgSrc(ph.img), alt: ph.alt || t.n, loading: "lazy" })), h("div.acard__txt", [h("b", (ph.caption || "").slice(0, 38)), h("span", "")])]))), h("a.link", { href: "#fotos" }, "Toda la galería →")]));
  page.append(helpBox(t.short));
  const sc = new Map(); for (const [, p, tt, goals] of S.scorers_raw) if (tt === ti) sc.set(p, (sc.get(p) || 0) + goals);
  const top = [...sc.entries()].sort((a, b) => b[1] - a[1]).slice(0, 8);
  if (top.length) page.append(sec("Máximos goleadores del club", h("ol.rank", top.map(([p, v], i) => h("li", [h("span.rank__pos", i + 1), h("span.rank__n", h("b", S.players[p])), h("span.rank__v", v)])))));
  return { page, title: t.short };
});
