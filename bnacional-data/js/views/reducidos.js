// reducidos, octogonales, finales, promociones, desempates y otras fases fuera de la fase regular
import { route } from "../app.js";
import { S } from "../store.js";
import { h, n, norm, fshort } from "../util.js";
import { head, T, href, crest } from "./common.js";

// el orden importa: se toma el primer tipo que coincide
export const TIPOS = [
  ["desempate", "Desempates", /Desempate/i],
  ["permanencia", "Por la permanencia", /Promoción con|Descenso|Reválida|Reclasificatorio/i],
  ["ascenso", "Por el ascenso", /Reducido|Octogonal|Dodecagonal|Cuadrangular|Ronda Final|Final por|por el (?:1er|2do)\.? ?Ascenso|por la Promoción|Fase final/i],
  ["otras", "Otras", /./],
];
export const tipoDe = (torneo) => TIPOS.find(([, , re]) => re.test(torneo))[0];
// qué estaba en juego en cada torneo
export function enJuego(t) {
  if (/Promoción con 1ra\.? ?"?B/i.test(t)) return "Promoción por la permanencia: el equipo de la B Nacional defendía la categoría contra uno de la Primera B Metropolitana. El que perdía jugaba en la B Metro.";
  if (/Promoción con Argentino/i.test(t)) return "Promoción por la permanencia: el equipo de la B Nacional defendía la categoría contra uno del Torneo Argentino A.";
  if (/Reválida/i.test(t)) return "Reválida regional: clubes del interior defendían su lugar en la categoría contra equipos de su región.";
  if (/Reclasificatorio/i.test(t)) return "Reclasificatorio: clubes de la B Nacional y del Torneo Argentino A por un lugar en la categoría.";
  if (/Descenso/i.test(t)) return "Para definir quién descendía.";
  if (/Desempate por la Promoción/i.test(t)) return "Desempate para ver quién jugaba la promoción contra un equipo de Primera División.";
  if (/Desempate/i.test(t)) return "Partido extra para desempatar una igualdad en puntos (por el ascenso, la clasificación o el descenso).";
  if (/por la Promoción/i.test(t)) return "Torneo para definir quién jugaba la promoción contra un equipo de Primera División.";
  if (/1er\.? ?Ascenso/i.test(t)) return "Por el primer ascenso a Primera División.";
  if (/2do\.? ?Ascenso/i.test(t)) return "Por el segundo ascenso a Primera División.";
  if (/Reducido y finales/i.test(t)) return "Reducido y finales por el ascenso a Primera División.";
  if (/Fase final/i.test(t)) return "Segunda fase de la Transición 2020, por los ascensos.";
  if (/^Etapa/i.test(t)) return "Partido de la fase por zonas que quedó guardado aparte: la tabla publicada de la zona ya cierra sin él, así que queda para revisar a mano.";
  return "";
}
// todos los partidos extra: {si, torneo, inst, leg, date, a, b, ga, gb, pen:[ganador, "4-3"]|null, ext, tipo}
let ALL;
export function extras() {
  if (ALL) return ALL;
  ALL = [];
  S.seasons.forEach((s, si) => (s.reducidos || []).forEach((r) => ALL.push({ si, torneo: r[0], inst: r[1], leg: r[2], date: r[3], a: r[4], b: r[5], ga: r[6], gb: r[7], pen: r[8] || null, ext: !!r[9], tipo: tipoDe(r[0] || "") })));
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
const club = (ti) => ti == null ? h("span.muted", "?") : h("a", { href: href.club(ti) }, [crest(ti), T(ti).short]);
// ganador de un partido suelto: por goles o por penales
const winner = (x) => x.ga > x.gb ? x.a : x.gb > x.ga ? x.b : x.pen ? x.pen[0] : null;
// filas de un torneo: los partidos de ida y vuelta se agrupan en una serie con el global y quién pasó
function rowsFor(ms, all) {
  ms = ms.slice().sort((a, b) => (a.date || "").localeCompare(b.date || ""));
  const key = (x) => `${x.inst}|${Math.min(x.a, x.b)}|${Math.max(x.a, x.b)}`;
  const series = new Map();
  for (const x of ms) if (/ida|vuelta/i.test(x.leg || "") && x.a != null && x.b != null) { const k = key(x); if (!series.has(k)) series.set(k, []); series.get(k).push(x); }
  const out = [];
  const matchRow = (x, inSerie) => {
    const w = inSerie ? null : winner(x);
    const side = (t) => h("span" + (w == null ? "" : w === t ? ".red__win" : ".red__lose"), club(t));
    const extra = [x.pen ? `pen. ${x.pen[1]}` : null, x.ext && !x.pen ? "con alargue" : null].filter(Boolean).join(" · ");
    return h("tr" + (inSerie ? ".red__leg" : ""), [h("td.red__d", x.date ? fshort(x.date) : ""), h("td.muted.red__i", [x.inst, x.leg ? ` · ${x.leg}` : ""].filter(Boolean)),
      h("td.red__a", side(x.a)), h("td.h2h__score", [`${x.ga} - ${x.gb}`, extra ? h("small.red__x", extra) : null]), h("td", side(x.b))]);
  };
  const done = new Set();
  for (const x of ms) {
    if (done.has(x)) continue;
    const k = x.a != null && x.b != null ? key(x) : null, ser = k && series.get(k);
    if (!ser || ser.length < 2) { out.push(matchRow(x, false)); done.add(x); continue; }
    ser.forEach((y) => { out.push(matchRow(y, true)); done.add(y); });
    const [t1, t2] = [ser[0].a, ser[0].b], g = { [t1]: 0, [t2]: 0 };
    for (const y of ser) { g[y.a] += y.ga; g[y.b] += y.gb; }
    const last = ser[ser.length - 1];
    let pasa = g[t1] > g[t2] ? t1 : g[t2] > g[t1] ? t2 : last.pen ? last.pen[0] : null, how = "";
    if (g[t1] === g[t2]) {
      if (last.pen) how = ` (penales ${last.pen[1]})`;
      else if (/Promoción con/i.test(x.torneo) && regularSets()[x.si].has(t1) !== regularSets()[x.si].has(t2)) {
        pasa = regularSets()[x.si].has(t1) ? t1 : t2; how = " (con el global igualado, el de la B Nacional conservaba la categoría)";
      } else {
        const later = all.filter((y) => y.date > last.date);
        const p1 = later.some((y) => y.a === t1 || y.b === t1), p2 = later.some((y) => y.a === t2 || y.b === t2);
        if (p1 !== p2) { pasa = p1 ? t1 : t2; how = " (por ventaja deportiva: siguió jugando)"; }
      }
    }
    out.push(h("tr.red__glob", h("td", { colspan: 5 }, [`Global: ${T(t1).short} ${g[t1]} - ${g[t2]} ${T(t2).short}`, pasa != null ? [" · ", h("b", `${(/Final/i.test(x.inst || "") && !/Semi|Cuarto|Octavo/i.test(x.inst || "")) || /Promoción con|Final por/i.test(x.torneo) ? "Ganó" : "Pasó"} ${T(pasa).short}`), how] : " · igualado, la fuente no dice quién pasó"])));
  }
  return out;
}
route("reducidos", async (r) => {
  const page = h("div.wrap.page"), box = h("div");
  { const ti = r.arg ? S.teamBy.get(r.arg) : null; st.q = ti != null ? T(ti).short : ""; if (ti != null) { st.tipo = "todos"; st.si = -1; } }
  const list = extras();
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
        ...[...groups.entries()].map(([tor, ms]) => h("div.red__g", [h("h3", [tor, h("button.pill.pill--btn.red__t", { type: "button", title: "Ver solo este tipo", onclick: () => setTipo(ms[0].tipo) }, TIPOS.find((t) => t[0] === ms[0].tipo)[1])]),
          enJuego(tor) ? h("p.muted.red__q", enJuego(tor)) : null,
          h("div.tablewrap", h("table.tbl.red__tbl", h("tbody", rowsFor(ms, list.filter((y) => y.si === si && y.torneo === tor)))))]))]));
    }
    if (!rows.length) out.push(h("p.muted", "No hay partidos con esos filtros."));
    box.replaceChildren(...out);
  };
  const chips = h("div.chips", [["todos", "Todos"], ...TIPOS.map(([k, l]) => [k, l])].map(([k, l]) => h("button.chip", { type: "button", "aria-pressed": String(st.tipo === k), onclick: () => setTipo(k) }, l)));
  const setTipo = (k) => { st.tipo = k; chips.querySelectorAll(".chip").forEach((c, i) => c.setAttribute("aria-pressed", String(["todos", ...TIPOS.map((t) => t[0])][i] === k))); draw(); };
  const withRed = S.seasons.map((s, si) => [si, s]).filter(([, s]) => s.reducidos && s.reducidos.length).reverse();
  page.append(head("Reducidos y promociones", "Todo lo que se jugó fuera de la fase regular", "Reducidos, octogonales y finales por el ascenso, promociones y reválidas por la permanencia, triangulares por el descenso y desempates. En negrita, el que ganó o pasó de ronda. No suman en las tablas, salvo que lo elijas en la tabla histórica. Las promociones contra equipos de Primera División todavía no están en la base."),
    chips,
    h("div.toolbar", [h("input", { type: "search", placeholder: "Buscar club", "aria-label": "Buscar club", value: st.q, oninput: (e) => { st.q = e.target.value; draw(); } }),
      h("label.sel", ["Temporada ", h("select", { onchange: (e) => { st.si = Number(e.target.value); draw(); } }, [h("option", { value: -1 }, "Todas"), ...withRed.map(([si, s]) => h("option", { value: si, selected: si === st.si }, s.label))])])]), box);
  draw();
  return { page, title: "Reducidos y promociones" };
});
