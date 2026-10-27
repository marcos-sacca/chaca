import { route } from "../app.js";
import { S, sum, STREAKS, longestRun, campaigns, topScorers, title, score } from "../store.js";
import { h, n, pct, dShort, signed } from "../util.js";
import { hbars, legendGEP } from "../charts.js";
import { href, field, select, segmented, sortTable, pageHead, matchRow, setQuery, rowsTable } from "./common.js";

route("records", (r, page) => {
  const f = { s: r.q.s || "rachas", min: r.q.min || "10" };
  const out = h("div");
  const draw = () => {
    setQuery("records", f);
    out.replaceChildren(({ rachas, curiosidades, temporadas, canchas })[f.s](f));
  };
  const tabs = h("div.tabs", [["rachas", "Rachas"], ["curiosidades", "Marcas"], ["temporadas", "Temporadas"], ["canchas", "Canchas"]].map(([k, t]) => h("button", { type: "button", "aria-pressed": String(f.s === k), onclick: (e) => { f.s = k; tabs.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", "false")); e.currentTarget.setAttribute("aria-pressed", "true"); draw(); } }, t)));
  page.append(h("div.wrap.page", [pageHead("Récords", "Marcas y rachas", "Las rachas siguen aunque cambie el torneo y se cuentan en orden de fecha. Si dos rachas empatan, mostramos la primera."), tabs, out]));
  draw();
  return { title: "Récords" };
});

function rachas() {
  return h("div.cols2", STREAKS.map(([name, test]) => {
    const x = longestRun(S.matches, test);
    return h("div.strk", [
      h("b", name), h("span.strk__v.num", x.len),
      h("small", x.first ? [`${dShort(x.first.d)} (${x.first.l} ${score(x.first)} ${x.first.v}) a ${dShort(x.last.d)}`, x.cutter ? ` · la cortó ${x.cutter.r} el ${dShort(x.cutter.d)}` : " · sigue vigente"] : "—"),
      x.now ? h("small", { style: { gridColumn: "1 / -1" } }, [h("b", `Racha actual: ${x.now}`), x.now >= x.len ? " (¡es el récord!)" : ` · le faltan ${x.len - x.now + 1} para superar el récord`]) : h("small", { style: { gridColumn: "1 / -1", color: "var(--ink-3)" } }, "Racha actual: 0"),
    ]);
  }));
}

function curiosidades() {
  const M = S.matches, F = S.facts;
  const best = (list, key) => list.reduce((a, m) => (key(m) > key(a) ? m : a), list[0]);
  const wins = M.filter((m) => m.res === "G" && m.gf != null), loss = M.filter((m) => m.res === "P" && m.gf != null);
  const withEsp = M.filter((m) => m.esp != null);
  const topEsp = withEsp.slice().sort((a, b) => b.esp - a.esp).slice(0, 5);
  const hat = [];
  M.forEach((m) => { const c = new Map(); (m.g || []).forEach((g) => { if (g.p && !g.ec) c.set(g.p, (c.get(g.p) || 0) + 1); }); c.forEach((k, p) => { if (k >= 3) hat.push({ m, p, k }); }); });
  hat.sort((a, b) => b.k - a.k || b.m.d.localeCompare(a.m.d));
  const block = (t, list, extra) => h("section.sec", { style: { marginTop: "36px" } }, [h("h2", { style: { marginBottom: "10px", fontSize: "1.9rem" } }, t), h("div.mlist", list.map((m) => { const r = matchRow(m); if (extra) { const e = extra(m); if (e) r.querySelector(".m__t").append(e); } return r; }))]);
  const top = (list, k) => list.slice().sort(k).slice(0, 5);
  return h("div", [
    block("Mayores goleadas a favor", top(wins, (a, b) => (b.gf - b.gc) - (a.gf - a.gc) || b.gf - a.gf || a.d.localeCompare(b.d))),
    block("Mayores derrotas", top(loss, (a, b) => (b.gc - b.gf) - (a.gc - a.gf) || b.gc - a.gc || a.d.localeCompare(b.d))),
    block("Partidos con más goles", top(M.filter((m) => m.gf != null), (a, b) => (b.gf + b.gc) - (a.gf + a.gc) || b.gf - a.gf || a.d.localeCompare(b.d))),
    withEsp.length ? block("Más espectadores", topEsp, (m) => h("span.mark", n(m.esp))) : null,
    hat.length ? h("section.sec", { style: { marginTop: "36px" } }, [h("h2", { style: { marginBottom: "10px", fontSize: "1.9rem" } }, "Goleadores con tres o más en un partido"), h("div.mlist", hat.slice(0, 12).map(({ m, p, k }) => { const r = matchRow(m); r.querySelector(".m__t").append(h("span.mark", `${p}: ${k}`)); return r; })), hat.length > 12 ? h("p.cap", `Se muestran 12 de ${hat.length}.`) : null]) : null,
    h("p.cap", { style: { marginTop: "24px" } }, "El dato de espectadores y los goleadores están cargados solo en una parte de los partidos."),
  ]);
}

function temporadas(f) {
  const min = +f.min || 10;
  const cs = campaigns().filter((c) => c.s.pj >= min);
  const set = (v) => { f.min = v; location.hash = `#/records?s=temporadas&min=${v}`; };
  const rank = (title, keyf, fmt, desc = true, limit = 5) => h("div", [h("h3", { style: { marginBottom: "10px" } }, title), hbars(cs.slice().sort((a, b) => (desc ? keyf(b) - keyf(a) : keyf(a) - keyf(b)) || a.sd.localeCompare(b.sd)).slice(0, limit).map((c) => ({ label: c.sd + " · " + c.div.split(" ")[0], value: keyf(c), href: href.season(c.sd) })), { limit, fmt, max: desc ? undefined : undefined })]);
  return h("div", [
    h("div.filters", [field("Mínimo de partidos", select("rmin", [["5", "5"], ["10", "10"], ["20", "20"], ["30", "30"]], f.min, set), "rmin"), h("p.muted", { style: { alignSelf: "center", margin: 0 } }, "Competencia principal de cada temporada (sin copas).")]),
    h("div.cols2", [
      rank("Mejor efectividad", (c) => c.s.ef, (v) => pct(v, 1)),
      rank("Peor efectividad", (c) => 1 - c.s.ef, (v) => pct(1 - v, 1)),
      rank("Más victorias", (c) => c.s.g, n), rank("Más derrotas", (c) => c.s.p, n),
      rank("Más goles a favor", (c) => c.s.gf, n), rank("Más goles en contra", (c) => c.s.gc, n),
      rank("Mejor diferencia de gol", (c) => c.s.dg, signed), rank("Peor diferencia de gol", (c) => -c.s.dg, (v) => signed(-v)),
      h("div", [h("h3", { style: { marginBottom: "10px" } }, "Goleador de una temporada"), hbars(seasonScorers(), { limit: 5 })]),
    ].map((x) => h("section.sec", { style: { marginTop: "28px" } }, x))),
  ]);
}

function seasonScorers() {
  const out = [];
  S.seasons.forEach((se) => { const t = topScorers({ sd: se.sd })[0]; if (t) out.push({ label: `${t.p.name} · ${se.sd}`, value: t.g, href: href.player(t.p.name) }); });
  return out.sort((a, b) => b.value - a.value || a.label.localeCompare(b.label, "es")).slice(0, 5);
}

function canchas() {
  const by = new Map();
  S.matches.forEach((m) => { if (!m.cd) return; if (!by.has(m.cd)) by.set(m.cd, []); by.get(m.cd).push(m); });
  const rows = [...by].map(([name, list]) => ({ name, list, s: sum(list) }));
  const tot = S.matches.filter((m) => m.cd).length;
  return h("div", [
    h("p.muted", { style: { marginBottom: "12px" } }, `${n(rows.length)} canchas. Se agrupan por el club dueño de la cancha y cuentan solo los partidos con estadio cargado (${n(tot)} de ${n(S.matches.length)}).`),
    sortTable([
      { t: "Cancha", v: (x) => x.name, f: (x) => h("b", x.name) },
      { t: "PJ", v: (x) => x.s.pj, r: true, desc: true }, { t: "G", v: (x) => x.s.g, r: true, desc: true }, { t: "E", v: (x) => x.s.e, r: true, desc: true }, { t: "P", v: (x) => x.s.p, r: true, desc: true },
      { t: "Goles", v: (x) => x.s.gf, r: true, desc: true, f: (x) => `${x.s.gf}–${x.s.gc}` },
      { t: "Efectividad", v: (x) => x.s.ef, r: true, desc: true, f: (x) => pct(x.s.ef, 0) },
      { t: "Primero", v: (x) => x.list[0].d, r: true, f: (x) => x.list[0].y }, { t: "Último", v: (x) => x.list[x.list.length - 1].d, r: true, f: (x) => x.list[x.list.length - 1].y },
    ], rows, { sort: 1, dir: -1, limit: 25, rowHref: (x) => `#/partidos?cd=${encodeURIComponent(x.name)}` }),
  ]);
}
