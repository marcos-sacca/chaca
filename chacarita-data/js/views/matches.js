import { route } from "../app.js";
import { S, sum, filterMatches, DIVS, DIV_SHORT, condName, title } from "../store.js";
import { h, n, pct, dShort, dLong, dDay, resChip, resLabel } from "../util.js";
import { stackBar, legendGEP } from "../charts.js";
import { href, field, select, segmented, sortTable, statRow, pageHead, crumbs, setQuery } from "./common.js";

route("partidos", (r, page) => {
  const f = { q: r.q.q || "", div: r.q.div || "", rival: r.q.rival || "", res: r.q.res || "", cond: r.q.cond || "", y0: r.q.y0 || "", y1: r.q.y1 || "", tn: r.q.tn || "", sd: r.q.sd || "", cd: r.q.cd || "" };
  const out = h("div");
  const years = [...new Set(S.matches.map((m) => m.y))];
  const draw = () => {
    setQuery("partidos", f);
    const list = filterMatches({ q: f.q, div: f.div, rival: f.rival, res: f.res, cond: f.cond, y0: +f.y0 || 0, y1: +f.y1 || 0, tn: f.tn, sd: f.sd, cd: f.cd });
    const s = sum(list);
    out.replaceChildren(
      f.cd ? h("p", { style: { margin: "0 0 12px" } }, h("span.pill.pill--red", ["Cancha: " + f.cd, h("button", { type: "button", "aria-label": "Quitar filtro de cancha", style: { border: 0, background: "none", color: "inherit", padding: "0 0 0 6px", fontWeight: 800 }, onclick: () => { f.cd = ""; draw(); } }, "×")])) : null,
      h("div.row", { style: { justifyContent: "space-between", margin: "4px 0 14px" } }, [
        h("p", { style: { margin: 0 } }, [h("b.num", n(list.length)), list.length === 1 ? " partido" : " partidos", list.length ? h("span.muted", ` · ${n(s.g)} G, ${n(s.e)} E, ${n(s.p)} P · goles ${n(s.gf)}–${n(s.gc)} · efectividad ${pct(s.ef, 1)}`) : null]),
        h("div.row", [legendGEP(), list.length && !window.__EMBEDDED__ ? h("button.btn.btn--ghost.btn--sm", { type: "button", onclick: () => csv(list) }, "Descargar CSV") : null]),
      ]),
      list.length ? h("div", { style: { marginBottom: "20px" } }, stackBar(s, { tall: true })) : null,
      sortTable([
        { t: "Fecha", v: (m) => m.d, f: (m) => dShort(m.d), desc: true },
        { t: "Partido", v: (m) => `${m.l} ${m.v}`, wrap: true, f: (m) => h("a", { href: href.match(m) }, [m.l === "Chacarita" ? h("b", m.l) : m.l, " – ", m.v === "Chacarita" ? h("b", m.v) : m.v]) },
        { t: "Marcador", v: (m) => (m.gl ?? 0) * 100 + (m.gv ?? 0), r: true, f: (m) => h("b.num", `${m.gl ?? "?"}-${m.gv ?? "?"}`) },
        { t: "Res.", v: (m) => m.res, f: (m) => resChip(m.res) },
        { t: "Torneo", v: (m) => m.tn, f: (m) => `${m.tn}${m.j ? " · " + (/^\d+$/.test(String(m.j)) ? "f. " : "") + m.j : ""}` },
        { t: "Condición", v: (m) => m.c, f: (m) => condName[m.c] },
      ], list, { sort: 0, dir: -1, limit: 50, rowHref: (m) => href.match(m), empty: "Ningún partido coincide con esos filtros. Probá sacar alguno." }),
    );
  };
  const set = (k) => (v) => { f[k] = v; draw(); };
  const text = h("input.in", { id: "pq", type: "search", value: f.q, placeholder: "Rival, DT, árbitro, estadio…", style: { minWidth: "240px" }, autocomplete: "off" });
  let tm; text.addEventListener("input", () => { clearTimeout(tm); tm = setTimeout(() => { f.q = text.value; draw(); }, 140); });
  const rival = h("input.in", { id: "pr", type: "text", list: "rivlist", value: f.rival, placeholder: "Cualquiera", autocomplete: "off" });
  rival.addEventListener("change", () => { f.rival = S.rivalMap.has(rival.value) ? rival.value : ""; if (f.rival === "") rival.value = ""; draw(); });
  const yin = (k, id, ph) => { const i = h("input.in.in--sm", { id, type: "number", min: years[0], max: years[years.length - 1], value: f[k], placeholder: ph }); i.addEventListener("change", () => { f[k] = i.value; draw(); }); return i; };
  const torneos = [["", "Todos"], ...S.torneos.map((t) => t.n).filter((v, i, a) => a.indexOf(v) === i).sort((a, b) => a.localeCompare(b, "es", { numeric: true })).map((t) => [t, t])];
  page.append(h("div.wrap.page", [
    pageHead("Partidos", "Todos los partidos", "Filtrá lo que quieras: cada combinación se guarda en la dirección, así podés compartirla."),
    h("div.filters", [
      field("Buscar", text, "pq"),
      field("Rival", rival, "pr"),
      field("División", select("pd", [["", "Todas"], ...DIVS.map((d) => [d, DIV_SHORT[d]])], f.div, set("div")), "pd"),
      field("Desde", yin("y0", "py0", "1931"), "py0"), field("Hasta", yin("y1", "py1", "2026"), "py1"),
      field("Torneo", select("pt", torneos, f.tn, set("tn")), "pt"),
    ]),
    h("div.filters", [
      h("div.field", [h("span.lab", "Resultado"), segmented([["", "Todos"], ["G", "Ganó"], ["E", "Empató"], ["P", "Perdió"]], f.res, set("res"), "Resultado")]),
      h("div.field", [h("span.lab", "Condición"), segmented([["", "Todas"], ["L", "Local"], ["V", "Visitante"]], f.cond, set("cond"), "Condición")]),
      h("button.btn.btn--ghost.btn--sm", { type: "button", style: { alignSelf: "end", marginBottom: "4px" }, onclick: () => (location.hash = "#/partidos") }, "Limpiar filtros"),
    ]),
    h("datalist", { id: "rivlist" }, S.rivals.map((x) => h("option", { value: x.name }))),
    out,
  ]));
  draw();
  return { title: "Partidos" };
});

function csv(list) {
  const cols = [["fecha", (m) => m.d], ["torneo", (m) => m.tn], ["fecha_nro", (m) => m.j ?? ""], ["local", (m) => m.l], ["visitante", (m) => m.v], ["goles_local", (m) => m.gl ?? ""], ["goles_visitante", (m) => m.gv ?? ""], ["resultado_chacarita", (m) => m.res], ["condicion", (m) => condName[m.c]], ["estadio", (m) => m.e ?? ""], ["arbitro", (m) => m.arb ?? ""], ["dt", (m) => m.dt ?? ""], ["espectadores", (m) => m.esp ?? ""]];
  const q = (v) => `"${String(v).replace(/"/g, '""')}"`;
  const txt = [cols.map((c) => c[0]).join(","), ...list.map((m) => cols.map((c) => q(c[1](m))).join(","))].join("\n");
  const a = h("a", { href: URL.createObjectURL(new Blob(["﻿" + txt], { type: "text/csv;charset=utf-8" })), download: "chacarita-partidos.csv" });
  document.body.append(a); a.click(); a.remove();
}

// ───────── ficha de un partido
let SRC = null;
async function fuentes() {
  if (SRC) return SRC;
  SRC = {};
  try { SRC = await (await fetch("data/enrichment_index.json")).json(); } catch { /* sin detalle de fuente */ }
  return SRC;
}

route("partido", async (r, page) => {
  const m = S.byId.get(+r.arg);
  if (!m) { page.append(h("div.wrap.page", h("h1.h1", "No encontramos ese partido"), h("a.link", { href: "#/partidos" }, "Ir a la lista de partidos"))); return { title: "Partido" }; }
  const src = (await fuentes())[m.id] || {};
  const enr = (k) => (m.enr || []).includes(k) ? h("span.flag", { title: "Dato agregado: " + (src[k] || "fuente en la página de datos") }, "agregado") : null;
  const lu = (S.lineups[m.id] || []).map(([pid, rol]) => ({ name: S.players[pid], rol }));
  const idx = S.matches.indexOf(m), prev = S.matches[idx - 1], next = S.matches[idx + 1];
  const goals = (m.g || []);
  const me = (nm, right) => h("div.score__team" + (nm === "Chacarita" ? ".me" : ""), nm);
  const kvs = [
    ["Fecha", `${dDay(m.d)} de ${m.y}`],
    ["Torneo", m.tn + (m.j ? ` · ${/^\d+$/.test(String(m.j)) ? "fecha " : ""}${m.j}` : "")],
    ["División", m.div],
    ["Estadio", m.e ? m.e : null],
    ["Condición de Chacarita", condName[m.c]],
    ["Árbitro", m.arb ? [m.arb, enr("arb")] : null],
    ["Director técnico", m.dt ? [m.dt, enr("dt")] : null],
    ["Espectadores", m.esp != null ? [n(m.esp), enr("esp")] : null],
    ["Puntos", m.pt != null ? `${m.pt}${m.y < 1995 ? " (2 por victoria)" : ""}` : null],
  ].filter(([, v]) => v);
  const tit = (arr) => arr.map(({ name, rol }) => h("li", [h("a", { href: href.player(name) }, name), rol ? h("small", "suplente") : null]));
  const tits = lu.filter((x) => !x.rol), sups = lu.filter((x) => x.rol);
  const mkGoal = (g) => h("li", [h("span.min", g.m != null ? `${g.m}'` : "—"), g.ec ? (/gol en contra/i.test(g.p || "") ? "Gol en contra" : h("span", [g.p, h("small.muted", " (rival)")])) : g.p ? h("a", { href: href.player(g.p) }, g.p) : "Sin dato", g.pen ? h("span.pill", "penal") : null, g.ec ? h("span.pill", "en contra") : null, g.ec ? enr("ec") : null]);
  page.append(h("div.wrap.page", [
    crumbs({ t: "Partidos", href: "#/partidos" }, { t: m.tn, href: `#/partidos?tn=${encodeURIComponent(m.tn)}` }, { t: dShort(m.d) }),
    h("div.score", { style: { paddingBottom: "6px" } }, [
      me(m.l), h("div.score__n", [m.gl ?? "?", h("span", "-"), m.gv ?? "?"]), me(m.v),
    ]),
    h("div.row", { style: { justifyContent: "center", gap: "14px", marginBottom: "6px" } }, [resChip(m.res), h("b", resLabel[m.res] + " Chacarita"), m.pen ? h("span.muted", `Penales ${m.pen[0]}-${m.pen[1]}`) : null]),
    h("dl.kv", { style: { marginTop: "26px" } }, kvs.map(([k, v]) => h("div", [h("dt", k), h("dd", v)]))),
    m.nt ? h("p.callout", { style: { marginTop: "22px" } }, m.nt) : null,
    h("section.sec.cols2", { "data-reveal": "" }, [
      h("div", [h("h2", { style: { marginBottom: "14px" } }, "Goles"), goals.length ? h("ul.goals", goals.map(mkGoal)) : h("p.muted", (m.gf ?? 0) + (m.gc ?? 0) === 0 ? "Sin goles." : "Los goleadores de este partido todavía no están cargados.")]),
      h("div", [h("h2", { style: { marginBottom: "14px" } }, ["Formación de Chacarita", enr("lu")]), lu.length ? [h("ul.lineup", tit(tits)), sups.length ? [h("p.eyebrow", { style: { margin: "14px 0 6px" } }, "Ingresaron"), h("ul.lineup", tit(sups))] : null] : h("p.muted", "La formación de este partido todavía no está cargada.")]),
    ]),
    h("div.row", { style: { justifyContent: "space-between", marginTop: "44px", borderTop: "1px solid var(--line-2)", paddingTop: "18px" } }, [
      prev ? h("a.link", { href: href.match(prev), style: { flexDirection: "row-reverse" } }, `Anterior: ${prev.l} ${prev.gl ?? "?"}-${prev.gv ?? "?"} ${prev.v}`) : h("span"),
      h("a.link", { href: href.rival(m.r) }, `Historial contra ${m.r}`),
      next ? h("a.link", { href: href.match(next) }, `Siguiente: ${next.l} ${next.gl ?? "?"}-${next.gv ?? "?"} ${next.v}`) : h("span"),
    ]),
    Object.keys(src).length ? h("p.src", { style: { marginTop: "14px" } }, "Datos marcados como «agregado»: " + [...new Set(Object.values(src))].join("; ") + ".") : null,
  ]));
  return { title: title(m) };
});
