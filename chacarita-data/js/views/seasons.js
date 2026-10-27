import { route } from "../app.js";
import { S, sum, topScorers, campaigns, DIV_SHORT } from "../store.js";
import { h, n, pct, dShort } from "../util.js";
import { stackBar, legendGEP, stackedColumns, hbars, divisionTimeline } from "../charts.js";
import { href, sortTable, statRow, pageHead, crumbs, matchBrowser, field, select } from "./common.js";

route("temporadas", (r, page) => (r.arg ? one(r.arg, page) : all(page)));

const posOf = (s) => s.torneos.filter((t) => t.tipo !== "Copa" && t.div === s.div).map((t) => t.pos).filter(Boolean).join(" · ") || null;

function all(page) {
  let div = "";
  const out = h("div");
  const draw = () => {
    const cs = campaigns().filter((c) => !div || c.div === div);
    const rows = cs.map((c) => ({ ...c, pos: posOf(S.seasonMap.get(c.sd)), y: S.seasonMap.get(c.sd).list[0].y }));
    out.replaceChildren(
      h("div.panel", { style: { marginBottom: "22px" } }, [h("div", { style: { marginBottom: "10px" } }, legendGEP()), stackedColumns(rows.map((c) => ({ x: c.sd, G: c.s.g, E: c.s.e, P: c.s.p, sd: c.sd })), { every: Math.max(1, Math.round(rows.length / 12)), label: (d) => "Temporada " + d.x, onpick: (d) => (location.hash = href.season(d.sd)) })]),
      sortTable([
        { t: "Temporada", v: (c) => c.y, f: (c) => h("a", { href: href.season(c.sd) }, h("b", c.sd)), desc: true },
        { t: "División", v: (c) => c.div, f: (c) => DIV_SHORT[c.div] },
        { t: "Posición", v: (c) => c.pos, f: (c) => c.pos || "—" },
        { t: "PJ", v: (c) => c.s.pj, r: true, desc: true }, { t: "G", v: (c) => c.s.g, r: true, desc: true }, { t: "E", v: (c) => c.s.e, r: true, desc: true }, { t: "P", v: (c) => c.s.p, r: true, desc: true },
        { t: "GF", v: (c) => c.s.gf, r: true, desc: true }, { t: "GC", v: (c) => c.s.gc, r: true, desc: true },
        { t: "Efectividad", v: (c) => c.s.ef, r: true, desc: true, f: (c) => pct(c.s.ef, 1) },
      ], rows, { sort: 0, dir: -1, limit: 30, rowHref: (c) => href.season(c.sd) }),
    );
  };
  page.append(h("div.wrap.page", [
    pageHead("Temporadas", "Año por año", "Cada temporada deportiva con su competencia principal (sin copas). La efectividad es la misma para todas las épocas: puntos a 3 por victoria sobre los puntos en juego."),
    h("div.filters", [field("División", select("sdiv", [["", "Todas"], ["Primera División", "Primera"], ["Segunda División", "Segunda"], ["Tercera División", "Tercera"]], "", (v) => { div = v; draw(); }), "sdiv")]),
    out,
  ]));
  draw();
  return { title: "Temporadas" };
}

function one(sd, page) {
  const s = S.seasonMap.get(sd);
  if (!s) { page.append(h("div.wrap.page", h("h1.h1", "No hay esa temporada"), h("a.link", { href: "#/temporadas" }, "Ver todas las temporadas"))); return { title: "Temporada" }; }
  const ss = sum(s.main), all = sum(s.list);
  const i = S.seasons.indexOf(s), prev = S.seasons[i - 1], next = S.seasons[i + 1];
  const sc = topScorers({ sd }).slice(0, 8);
  const dts = [...new Map(s.main.filter((m) => m.dt).map((m) => [m.dt, 0])).keys()];
  const dtCount = dts.map((d) => [d, s.main.filter((m) => m.dt === d).length]).sort((a, b) => b[1] - a[1]);
  page.append(h("div.wrap.page", [
    crumbs({ t: "Temporadas", href: "#/temporadas" }, { t: sd }),
    pageHead(null, `Temporada ${sd}`, `${s.div}${posOf(s) ? " · " + posOf(s) : ""}`),
    statRow([["Jugados", n(ss.pj), "competencia principal"], ["Ganó", ss.g], ["Empató", ss.e], ["Perdió", ss.p], ["Goles", `${ss.gf}–${ss.gc}`], ["Efectividad", pct(ss.ef, 1)]]),
    h("div.panel", { style: { marginTop: "22px" } }, [h("div.row", { style: { justifyContent: "space-between", marginBottom: "12px" } }, [h("b", "Balance"), legendGEP()]), stackBar(ss, { tall: true })]),
    h("section.sec", { "data-reveal": "" }, [h("h2", { style: { marginBottom: "12px" } }, "Torneos"), h("div.tblwrap", h("table.tbl", [
      h("thead", h("tr", ["Torneo", "División", "Del", "Al", "Resultado"].map((t) => h("th", t)))),
      h("tbody", s.torneos.map((t) => h("tr", [h("td.wrapcell", h("a", { href: `#/partidos?tn=${encodeURIComponent(t.n)}` }, h("b", t.n))), h("td", t.div), h("td", dShort(t.desde)), h("td", dShort(t.hasta)), h("td.wrapcell", [t.pos || "—", t.pos_fuente ? h("span.flag", { title: "Dato agregado: " + t.pos_fuente }, "agregado") : null, t.nota ? h("small.muted", { style: { display: "block" } }, t.nota) : null])]))),
    ]))]),
    sc.length ? h("section.sec.cols2", { "data-reveal": "" }, [h("div", [h("h2", { style: { marginBottom: "12px" } }, "Goleadores (todos los torneos)"), hbars(sc.map((x) => ({ label: x.p.name, value: x.g, href: href.player(x.p.name) })), { limit: 8 })]), dtCount.length ? h("div", [h("h2", { style: { marginBottom: "12px" } }, "Directores técnicos"), h("ul", { style: { padding: 0, listStyle: "none" } }, dtCount.map(([d, k]) => h("li", { style: { display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--line)" } }, [d, h("span.muted.num", `${k} partidos`)])))]) : null]) : null,
    h("section.sec", { "data-reveal": "" }, [h("h2", { style: { marginBottom: "10px" } }, `Los ${all.pj} partidos de la temporada`), matchBrowser(s.list, { limit: 20, order: 1 })]),
    h("div.row", { style: { justifyContent: "space-between", marginTop: "40px" } }, [prev ? h("a.link", { href: href.season(prev.sd), style: { flexDirection: "row-reverse" } }, `Temporada ${prev.sd}`) : h("span"), next ? h("a.link", { href: href.season(next.sd) }, `Temporada ${next.sd}`) : h("span")]),
  ]));
  return { title: `Temporada ${sd}` };
}
