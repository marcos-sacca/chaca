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
// --- llaves: cruces de un torneo (ida y vuelta o partido único) ordenados en rondas, como un cuadro de Mundial
const roundOf = (x) => x.inst || "";
export function tiesFor(ms, all) {
  const by = new Map();
  for (const x of ms) {
    if (x.a == null || x.b == null) return null;
    const k = `${Math.min(x.a, x.b)}|${Math.max(x.a, x.b)}`;
    if (!by.has(k)) by.set(k, []);
    by.get(k).push(x);
  }
  const ties = [];
  for (const L of by.values()) {
    L.sort((p, q) => (p.date || "").localeCompare(q.date || ""));
    // un mismo par puede cruzarse en dos rondas distintas: se corta cuando cambia la instancia (salvo ida y vuelta)
    let cur = [];
    const flush = () => { if (cur.length) ties.push(cur); cur = []; };
    for (const x of L) {
      const prev = cur[cur.length - 1];
      const sameTie = prev && (roundOf(prev) === roundOf(x) || (/fecha \d+/i.test(roundOf(prev)) && /fecha \d+/i.test(roundOf(x)) && cur.length === 1 && x.date && prev.date && (new Date(x.date) - new Date(prev.date)) / 864e5 <= 21));
      if (!sameTie) flush();
      cur.push(x);
      if (cur.length === 2) flush();
    }
    flush();
  }
  return ties.map((legs) => {
    const [t1, t2] = [legs[0].a, legs[0].b], g = { [t1]: 0, [t2]: 0 };
    for (const y of legs) { g[y.a] += y.ga; g[y.b] += y.gb; }
    const last = legs[legs.length - 1];
    let pasa = g[t1] > g[t2] ? t1 : g[t2] > g[t1] ? t2 : last.pen ? last.pen[0] : null, note = last.pen && g[t1] === g[t2] ? `pen. ${last.pen[1]}` : "";
    if (pasa == null && /Promoción con/i.test(legs[0].torneo) && regularSets()[legs[0].si].has(t1) !== regularSets()[legs[0].si].has(t2)) { pasa = regularSets()[legs[0].si].has(t1) ? t1 : t2; note = "conservó la categoría"; }
    // quién siguió jugando el mismo torneo: si es uno solo, ese pasó (aunque falte un partido de la serie en la base)
    const later = all.filter((y) => y.date > last.date), same = later.filter((y) => y.torneo === legs[0].torneo);
    const cont = (L) => { const p1 = L.some((y) => y.a === t1 || y.b === t1), p2 = L.some((y) => y.a === t2 || y.b === t2); return p1 !== p2 ? (p1 ? t1 : t2) : null; };
    const c = cont(same);
    if (c != null && pasa !== c) { note = pasa == null ? "ventaja deportiva" : "siguió jugando el torneo, aunque el resultado cargado no lo muestra"; pasa = c; }
    else if (pasa == null) { const c2 = cont(later); if (c2 != null) { pasa = c2; note = "ventaja deportiva"; } }
    return { round: roundOf(legs[0]), date: legs[0].date || "", legs, t1, t2, g, pasa, note };
  });
}
// rondas en orden; null si el torneo no es una llave (todos contra todos, o un club en dos cruces de la misma ronda)
export function bracketFor(ms, all) {
  let ties = tiesFor(ms, all);
  if (!ties || ties.length < 3) return null;
  // la final por el primer ascenso (los dos ganadores de zona) va aparte: es un cruce del campeón, que después no juega más
  const champ = S.seasons[ms[0].si].champion;
  const fin = champ == null ? [] : ties.filter((t) => (t.t1 === champ || t.t2 === champ) && !all.some((y) => y.date > t.legs[t.legs.length - 1].date && (y.a === champ || y.b === champ)));
  if (fin.length === 1 && ties.length > 3) { fin[0].pasa = champ; fin[0].note = fin[0].legs.some((y) => y.pen) ? `pen. ${fin[0].legs[fin[0].legs.length - 1].pen?.[1] || ""} · campeón y ascenso` : "campeón y ascenso"; ties = ties.filter((t) => t !== fin[0]); }
  else fin.length = 0;
  // cruces entre dos clubes de la mitad de abajo de su zona: no son del reducido (Solo Ascenso numera igual los partidos por la permanencia)
  const pos = new Map(), zt = (S.seasons[ms[0].si].tables || []).filter((t) => t.zona);
  for (const t of zt) for (const r of t.rows) pos.set(r[1], r[0] / t.rows.length);
  const otros = pos.size ? ties.filter((t) => (pos.get(t.t1) ?? 0) > .5 && (pos.get(t.t2) ?? 0) > .5) : [];
  ties = ties.filter((t) => !otros.includes(t));
  const rounds = new Map();
  for (const t of ties) { if (!rounds.has(t.round)) rounds.set(t.round, []); rounds.get(t.round).push(t); }
  const R = [...rounds.values()];
  R.sort((p, q) => p.reduce((m, t) => (t.date < m ? t.date : m), "9") .localeCompare(q.reduce((m, t) => (t.date < m ? t.date : m), "9")));
  if (R.length < 2) return null;
  for (const r of R) { const seen = new Set(); for (const t of r) { if (seen.has(t.t1) || seen.has(t.t2)) return null; seen.add(t.t1); seen.add(t.t2); } }
  for (let i = 1; i < R.length; i++) if (R[i].length > R[i - 1].length) return null;
  // orden: desde la final hacia atrás, cada cruce queda al lado de los que lo alimentan
  for (let i = R.length - 2; i >= 0; i--) {
    const next = R[i + 1], prev = R[i], ordered = [];
    for (const t of next) for (const team of [t.t1, t.t2]) { const f = prev.find((p) => !ordered.includes(p) && p.pasa === team); if (f) ordered.push(f); }
    R[i] = [...ordered, ...prev.filter((p) => !ordered.includes(p))];
  }
  R.final1 = fin[0] || null; R.otros = otros;
  return R;
}
const ROUND_NAMES = ["Final", "Semifinales", "Cuartos de final", "Octavos de final", "16avos de final"];
// un cruce: los dos clubes con el global, el que pasó resaltado
// un club sin ficha en el sitio (ej.: Racing Club en una promoción con Primera) se muestra con su nombre, sin link ni escudo
const teamRow = (t, tie, i) => { const nm = t == null ? (tie.names?.[i] || "?") : null; return h("div.bk__t" + (tie.pasa == null || (t == null && tie.pasa == null) ? "" : tie.pasa === t && t != null ? ".is-win" : ".is-lose") + (nm && tie.winName === nm ? ".is-win" : ""), [h("span.bk__n", nm ? nm : [crest(t), T(t).short]), h("b.bk__g", nm ? tie.gn?.[i] ?? "" : tie.g[t])]); };
export const tieCard = (tie) => h("div.bk__tie", { title: tie.legs.map((y) => `${y.date ? fshort(y.date) + " " : ""}${y.a != null ? T(y.a).short : (y.an || "?")} ${y.ga}-${y.gb} ${y.b != null ? T(y.b).short : (y.bn || "?")}`).join("\n") }, [teamRow(tie.t1, tie, 0), teamRow(tie.t2, tie, 1), h("small.bk__x", [tie.legs.length > 1 ? "ida y vuelta" : "partido único", tie.note ? ` · ${tie.note}` : ""])]);
export function bracketView(R) {
  const label = (r, i) => (/fecha \d+/i.test(r[0].round) || !r[0].round ? (R.length - 1 - i < ROUND_NAMES.length && R[R.length - 1].length === 1 ? ROUND_NAMES[R.length - 1 - i] : `Ronda ${i + 1}`) : r[0].round);
  const tieBox = tieCard;
  const fin1 = R.final1 ? h("div.bk__f1", [h("p.bk__r", "Final por el primer ascenso"), tieBox(R.final1), h("p.cap", "El que perdió la final pasó al reducido.")]) : null;
  const otros = R.otros && R.otros.length ? h("div.bk__ot", [h("p.bk__r", "Otros partidos de este torneo"), h("p.cap", "Entre clubes de la mitad de abajo de su zona: no son del reducido (probablemente por la permanencia)."), h("div.bk__otl", R.otros.map(tieBox))]) : null;
  const bk = h("div.bk", { role: "group", "aria-label": "Llave" }, R.map((r, i) => h("div.bk__col", [h("p.bk__r", label(r, i)), h("div.bk__ties", r.map(tieBox))])));
  return h("div", [fin1, R.final1 ? h("p.bk__r", "Reducido por el segundo ascenso") : null, h("div.bk__wrap", bk), otros]);
}

route("reducidos", async (r) => {
  const page = h("div.wrap.page"), box = h("div");
  { const ti = r.arg ? S.teamBy.get(r.arg) : null; st.q = ti != null ? T(ti).short : ""; if (ti != null) { st.tipo = "todos"; st.si = -1; } }
  const list = extras();
  // cada torneo: llave si se puede armar (con selector para ver los partidos), si no, la lista de partidos
  const groupBody = (ms, all) => {
    const listEl = () => h("div.tablewrap", h("table.tbl.red__tbl", h("tbody", rowsFor(ms, all))));
    const R = bracketFor(ms, all);
    if (!R) return listEl();
    const holder = h("div"), sw = h("div.chips.bk__sw");
    const show = (k) => { holder.replaceChildren(k === "llave" ? bracketView(R) : listEl()); sw.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c.dataset.k === k))); };
    sw.append(...[["llave", "Llave"], ["lista", "Partidos"]].map(([k, l]) => h("button.chip", { type: "button", "data-k": k, onclick: () => show(k) }, l)));
    show("llave");
    return h("div", [sw, holder]);
  };
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
          groupBody(ms, list.filter((y) => y.si === si && y.torneo === tor))]))]));
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
