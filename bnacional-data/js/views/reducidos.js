// reducidos, octogonales, finales, promociones, desempates y otras fases fuera de la fase regular
import { route } from "../app.js";
import { S } from "../store.js";
import { h, n, norm, fshort } from "../util.js";
import { head, T, href, crest } from "./common.js";

export const TIPOS = [
  ["ascenso", "Por el ascenso", /Reducido|Octogonal|Dodecagonal|Cuadrangular|Ronda Final|Final por|por el (?:1er|2do)\.? ?Ascenso|Reválida/i],
  ["promocion", "Promociones", /Promoci/i],
  ["descenso", "Por el descenso", /Descenso/i],
  ["desempate", "Desempates", /Desempate/i],
  ["otras", "Otras fases", /./],
];
export const tipoDe = (torneo) => TIPOS.find(([, , re]) => re.test(torneo))[0];
// todos los partidos extra: {si, torneo, inst, leg, date, a, b, ga, gb, tipo}
let ALL;
export function extras() {
  if (ALL) return ALL;
  ALL = [];
  S.seasons.forEach((s, si) => (s.reducidos || []).forEach((r) => ALL.push({ si, torneo: r[0], inst: r[1], leg: r[2], date: r[3], a: r[4], b: r[5], ga: r[6], gb: r[7], tipo: tipoDe(r[0] || "") })));
  return ALL;
}
// clubes que jugaron la fase regular de cada temporada (para sumar en la tabla solo a los de la categoría)
let REG;
export function regularSets() {
  if (REG) return REG;
  REG = S.seasons.map(() => new Set());
  for (const m of S.matches) { REG[m[0]].add(m[4]); REG[m[0]].add(m[5]); }
  return REG;
}

const st = { tipo: "todos", si: -1, q: "" };
route("reducidos", async (r) => {
  const page = h("div.wrap.page"), box = h("div");
  { const ti = r.arg ? S.teamBy.get(r.arg) : null; st.q = ti != null ? T(ti).short : ""; }
  const list = extras();
  const club = (ti) => ti == null ? h("span.muted", "?") : h("a", { href: href.club(ti) }, [crest(ti), T(ti).short]);
  const draw = () => {
    const f = norm(st.q.trim());
    const rows = list.filter((x) => (st.tipo === "todos" || x.tipo === st.tipo) && (st.si < 0 || x.si === st.si) && (!f || [x.a, x.b].some((t) => t != null && norm(T(t).short + " " + T(t).n).includes(f))));
    const bySeason = new Map();
    for (const x of rows) { if (!bySeason.has(x.si)) bySeason.set(x.si, []); bySeason.get(x.si).push(x); }
    const out = [h("p.muted.red__n", `${n(rows.length)} ${rows.length === 1 ? "partido" : "partidos"}`)];
    for (const [si, xs] of [...bySeason.entries()].sort((a, b) => b[0] - a[0])) {
      const groups = new Map();
      for (const x of xs) { const k = x.torneo; if (!groups.has(k)) groups.set(k, []); groups.get(k).push(x); }
      out.push(h("section.red__s", [h("h2", h("a", { href: href.season(si) }, S.seasons[si].label)),
        ...[...groups.entries()].map(([tor, ms]) => h("div.red__g", [h("h3", [tor, h("span.pill.red__t", TIPOS.find((t) => t[0] === ms[0].tipo)[1])]),
          h("div.tablewrap", h("table.tbl.red__tbl", h("tbody", ms.sort((a, b) => (a.date || "").localeCompare(b.date || "")).map((x) => h("tr", [
            h("td.red__d", x.date ? fshort(x.date) : ""), h("td.muted.red__i", [x.inst, x.leg ? ` · ${x.leg}` : ""].filter(Boolean)),
            h("td.red__a", x.ga > x.gb ? h("b", club(x.a)) : club(x.a)), h("td.h2h__score", `${x.ga} - ${x.gb}`), h("td", x.gb > x.ga ? h("b", club(x.b)) : club(x.b)),
          ])))))]))]));
    }
    if (!rows.length) out.push(h("p.muted", "No hay partidos con esos filtros."));
    box.replaceChildren(...out);
  };
  const chips = h("div.chips", [["todos", "Todos"], ...TIPOS.map(([k, l]) => [k, l])].map(([k, l]) => h("button.chip", { type: "button", "aria-pressed": String(st.tipo === k), onclick: (e) => { st.tipo = k; chips.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === e.currentTarget))); draw(); } }, l)));
  const withRed = S.seasons.map((s, si) => [si, s]).filter(([, s]) => s.reducidos && s.reducidos.length).reverse();
  page.append(head("Reducidos y promociones", "Todo lo que se jugó fuera de la fase regular", "Reducidos, octogonales y finales por el ascenso, promociones, triangulares por el descenso, desempates y otras fases. No suman en las tablas, salvo que lo elijas en la tabla histórica."),
    chips,
    h("div.toolbar", [h("input", { type: "search", placeholder: "Buscar club", "aria-label": "Buscar club", value: st.q, oninput: (e) => { st.q = e.target.value; draw(); } }),
      h("label.sel", ["Temporada ", h("select", { onchange: (e) => { st.si = Number(e.target.value); draw(); } }, [h("option", { value: -1 }, "Todas"), ...withRed.map(([si, s]) => h("option", { value: si, selected: si === st.si }, s.label))])])]), box);
  draw();
  return { page, title: "Reducidos y promociones" };
});
