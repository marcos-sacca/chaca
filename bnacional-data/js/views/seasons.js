import { route } from "../app.js";
import { S } from "../store.js";
import { h, n, fshort, fdate } from "../util.js";
import { ascCard, head, sec, table, T, href, pill, crest, plantelBox } from "./common.js";
import { imgSrc } from "../util.js";

route("temporadas", async () => {
  const page = h("div.wrap.page");
  page.append(head("Temporadas", "42 torneos, de 1986/87 a hoy", "Desde 2015 el torneo es anual. Antes se jugaba de agosto a junio, a veces con Apertura y Clausura o con zonas."));
  page.append(h("div.sgrid", [...S.seasons.keys()].reverse().map((si) => {
    const s = S.seasons[si], ch = s.champion != null ? T(s.champion).short : "Sin campeón";
    return h("a.scard", { href: href.season(si) }, [h("div", { style: { display: "flex", justifyContent: "space-between", alignItems: "center" } }, [h("b.scard__y", s.label), s.champion != null && S.crest(s.champion) ? h("img.scard__crest", { src: imgSrc(S.crest(s.champion).img), alt: "", loading: "lazy" }) : null]), h("span.scard__c", [h("small", s.champion != null ? "Campeón" : "Torneo"), ch]), h("span.scard__m", `${s.teams || "?"} equipos · ${n(s.played)} partidos`), s.promoted.length ? h("span.scard__p", `Subieron: ${s.promoted.map((p) => T(p[0]).short).join(", ")}`) : (si === S.seasons.length - 1 ? h("span.scard__p", "En disputa") : null)]);
  })));
  return { page, title: "Temporadas" };
});

route("t", async (r) => {
  const si = S.seasonBy.get(r.arg); if (si == null) return { page: h("div.wrap.page", h("h1", "No encontré esa temporada")), title: "" };
  const s = S.seasons[si], page = h("div.wrap.page");
  page.append(h("nav.crumbs", [h("a", { href: "#temporadas" }, "Temporadas"), " / ", s.label]));
  page.append(head(s.label, s.champion != null ? `Campeón: ${T(s.champion).n}` : "Primera Nacional", `${s.teams || ""} equipos · ${n(s.played)} partidos de fase regular${s.sanciones.length ? " · con descuentos de puntos" : ""}.`));
  // quienes subieron
  if (s.promoted.length) { const as = s.promoted.map(([t, how]) => ({ si, t, how, season: s, key: `${s.id}|${S.teams[t].s}` })); page.append(sec("Subieron a Primera", [h("div.agrid", as.map((a) => ascCard(a))), h("div.plantels", as.map((a) => plantelBox(a)))])); }
  else if (si === S.seasons.length - 1) page.append(sec("Ascensos", h("p.muted", "El torneo está en juego. Los ascensos se definen al final de la temporada.")));
  // descensos y reducidos de la temporada
  const clubList = (ids) => h("div.cgrid", ids.map((t) => h("a.ccard.ccard--s", { href: href.club(t) }, [crest(t), h("span.ccard__t", h("b", T(t).short))])));
  if (s.desc && s.desc.length) page.append(sec("Descendieron", [clubList(s.desc), h("p.cap", "Clubes que jugaron esta temporada, no ascendieron y no figuran en la siguiente. Se calcula así: la base no trae una lista oficial de descensos.")]));
  if (s.red && s.red.length) page.append(sec("Jugaron el reducido por el ascenso", clubList(s.red)));
  if (s.promo && s.promo.length) page.append(sec("Promociones y reválidas", clubList(s.promo)));
  // tablas
  if (s.tables.length) {
    let cur = 0; const box = h("div");
    const tabs = h("div.chips", s.tables.map((t, i) => h("button.chip", { type: "button", "aria-pressed": String(i === 0), onclick: (e) => { cur = i; tabs.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === e.currentTarget))); drawT(); } }, t.fase.replace(/^1ra "B" Nacional AFA - /, ""))));
    const promoted = new Set(s.promoted.map((p) => p[0])), ded = new Map(s.sanciones.map((x) => [x.club, x.pts]));
    const drawT = () => {
      const t = s.tables[cur];
      box.replaceChildren(table([{ label: "Pos." }, { label: "Club" }, ...["PJ", "PG", "PE", "PP", "GF", "GC", "DG"].map((l) => ({ label: l, cls: "num" })), { label: "Pts", cls: "num" }],
        t.rows.map(([pos, ti, pj, pg, pe, pp, gf, gc, dg, dd, pts]) => h("tr" + (promoted.has(ti) ? ".is-up" : ""), [h("td.num", pos), h("td", [crest(ti), h("a", { href: href.club(ti) }, T(ti).short)]), ...[pj, pg, pe, pp, gf, gc].map((v) => h("td.num", v)), h("td.num", (dg > 0 ? "+" : "") + dg), h("td.num", h("b", pts + (dd ? ` (−${dd})` : "")))]))));
    };
    drawT();
    page.append(sec("Tabla de posiciones", [s.tables.length > 1 ? tabs : null, box, h("p.cap", promoted.size ? "Las filas celestes son clubes que ascendieron." : ""), s.sanciones.length ? h("p.cap", "Descuentos de puntos: " + s.sanciones.filter((x) => x.club != null).map((x) => `${T(x.club).short} −${x.pts}`).join(", ") + ".") : null]));
  }
  // goleadores de la temporada
  const top = Object.values(S.scBySeason[si] || {}).sort((a, b) => b.g - a.g).slice(0, 10);
  if (top.length) page.append(sec("Goleadores de la temporada", h("ol.rank", top.map((o, i) => h("li", [h("span.rank__pos", i + 1), h("span.rank__n", [h("b", o.name), h("small", T(o.team).short)]), h("span.rank__v", o.g)])))));
  // resultados por fecha
  const ms = S.mBySeason[si].map((i) => S.matches[i]);
  const phases = [...new Set(ms.map((m) => m[1]))];
  const results = h("div.results"); let ph = phases[0], rd = null;
  const phSel = h("select#rph", { "aria-label": "Fase", onchange: (e) => { ph = Number(e.target.value); rd = null; fillRd(); drawR(); } }, phases.map((p) => h("option", { value: p }, S.phases[p])));
  const rdSel = h("select#rrd", { "aria-label": "Fecha", onchange: (e) => { rd = Number(e.target.value); drawR(); } });
  const fillRd = () => { const fs = [...new Set(ms.filter((m) => m[1] === ph).map((m) => m[2]))].sort((a, b) => a - b); rd = rd ?? fs[0]; rdSel.replaceChildren(...fs.map((f) => h("option", { value: f, selected: f === rd }, f ? `Fecha ${f}` : "Sin número"))); };
  const drawR = () => { results.replaceChildren(...ms.filter((m) => m[1] === ph && m[2] === rd).map((m) => h("div.res", [h("span.res__d", fshort(m[3])), h("a.res__h", { href: href.club(m[4]) }, T(m[4]).short), h("b.res__s", `${m[6]} - ${m[7]}`), h("a.res__a", { href: href.club(m[5]) }, T(m[5]).short)]))); };
  fillRd(); drawR();
  page.append(sec("Resultados", [h("div.toolbar", [phases.length > 1 ? phSel : null, rdSel]), results]));
  if (s.reducidos.length) {
    const rows = s.reducidos.map((r) => h("div.res.res--red", [h("span.res__d", r[3] ? fshort(r[3]) : ""), h("a.res__h", { href: r[4] != null ? href.club(r[4]) : "#" }, r[4] != null ? T(r[4]).short : "?"), h("b.res__s", `${r[6]} - ${r[7]}`), h("a.res__a", { href: r[5] != null ? href.club(r[5]) : "#" }, r[5] != null ? T(r[5]).short : "?"), h("span.res__t", `${r[0]} · ${r[1]}`)]));
    page.append(sec("Reducido y promociones", rows.length > 14 ? h("details.fold", [h("summary", `Ver los ${rows.length} partidos`), h("div.results", rows)]) : h("div.results", rows)));
  }
  return { page, title: s.label };
});
