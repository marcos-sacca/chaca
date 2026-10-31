// «Cómo se definió»: el camino de cada ascendido y todo lo que se jugó después de la fase regular de una temporada
// (finales, reducidos, promociones con categorías de abajo, desempates y promociones contra Primera División), en orden.
import { S } from "../store.js";
import { h, fshort } from "../util.js";
import { sec, T, href, crest } from "./common.js";
import { extras, tiesFor, bracketFor, bracketView, enJuego, tieCard } from "./reducidos.js";

const PRIMERA = "Promoción con Primera División";
let byName = null;
const tiOf = (name) => { byName ||= new Map(S.teams.map((t, i) => [t.n, i])); return byName.get(name) ?? null; };

// promociones contra Primera (data/promociones.json, de Marcos) con la misma forma que los cruces de los reducidos
function primeraTies(si) {
  return (S.promos || []).filter((p) => p.s === si).map((p) => {
    const legs = p.legs.map(([leg, date, a, b, ga, gb]) => ({ si, torneo: PRIMERA, inst: "", leg, date, a: tiOf(a), b: tiOf(b), ga, gb, pen: null }));
    const tp = tiOf(p.p), tb = tiOf(p.b), m = /\(([^)]+)\)/.exec(p.res || "");
    const pasa = m ? tiOf(m[1]) : null;
    const legs2 = legs.map((y, k) => ({ ...y, a: y.a, b: y.b, an: p.legs[k][2], bn: p.legs[k][3] }));
    return { torneo: PRIMERA, round: "", date: legs[0]?.date || "", legs: legs2, t1: tb, t2: tp, g: { [tb]: p.gb, [tp]: p.gp }, gn: [p.gb, p.gp], names: [p.b, p.p], winName: m ? m[1] : null, pasa, note: /ventaja/i.test(p.res) ? "ventaja deportiva" : "", res: p.res, obs: p.obs, primera: tp };
  });
}

const tname = (t, tie) => (t == null ? (tie?.names?.[tie.t1 === t ? 0 : 1] || "un equipo de Primera") : T(t).short);
const glob = (tie, t) => { const o = tie.t1 === t ? tie.t2 : tie.t1; return `${tie.g[t]}-${tie.g[o]}`; };
// «en la final del octogonal», «en un desempate», «en la promoción con la Primera B»
function where(tie) {
  if (tie.where) return tie.where;
  const t = tie.torneo || "";
  const tor = t === PRIMERA ? "la promoción con Primera" : /Final por el 1er/i.test(t) ? "la final por el primer ascenso" : /Final por el 2do/i.test(t) ? "la final por el segundo ascenso"
    : /Reducido/i.test(t) ? "el reducido" : /Octogonal/i.test(t) ? "el octogonal" : /Dodecagonal/i.test(t) ? "el dodecagonal" : /Cuadrangular/i.test(t) ? "el cuadrangular" : /Ronda Final/i.test(t) ? "la ronda final"
    : /^por la Promoción/i.test(t) ? "el torneo por la promoción" : /Desempate/i.test(t) ? "un desempate" : /Promoción con 1ra/i.test(t) ? "la promoción con la Primera B" : /Promoción con Argentino/i.test(t) ? "la promoción con el Argentino A"
    : /Reválida/i.test(t) ? "la reválida" : /Reclasificatorio/i.test(t) ? "el reclasificatorio" : /Descenso/i.test(t) ? "el triangular por el descenso" : /Fase final/i.test(t) ? "la fase final" : "un partido extra";
  const r = tie.round || "";
  const rp = /semifinal/i.test(r) ? "las semifinales" : /cuartos/i.test(r) ? "los cuartos de final" : /octavos/i.test(r) ? "los octavos de final" : /^final(es)?$/i.test(r.trim()) ? "la final" : /1ra\.? fase/i.test(r) ? "la primera fase" : /2da\.? fase/i.test(r) ? "la segunda fase" : "";
  if (!rp || /^(la final|un desempate)/.test(tor)) return `en ${tor}`;
  return `en ${rp} ${tor.startsWith("el ") ? "del " + tor.slice(3) : "de " + tor}`;
}

// frase con el recorrido de un club: «perdió con X en … (1-2), le ganó a Y en … (1-0) y ascendió»
function story(t, ties, how) {
  const mine = ties.filter((x) => x.t1 === t || x.t2 === t).sort((a, b) => a.date.localeCompare(b.date));
  if (!mine.length) return how === "Campeón" ? "Salió campeón y ascendió directo." : "Ascendió directo por su lugar en la tabla.";
  const parts = mine.map((x) => { const o = x.t1 === t ? x.t2 : x.t1; return x.pasa === t ? `le ganó a ${tname(o, x)} ${where(x)} (${glob(x, t)}${x.note ? `, ${x.note}` : ""})` : x.pasa == null ? `igualó con ${tname(o, x)} ${where(x)} (${glob(x, t)})` : `perdió con ${tname(o, x)} ${where(x)} (${glob(x, t)})`; });
  const s = parts.length > 1 ? parts.slice(0, -1).join(", ") + " y " + parts[parts.length - 1] : parts[0];
  return `${s.charAt(0).toUpperCase() + s.slice(1)}. ${how === "Campeón" ? "Campeón y ascenso." : "Ascendió a Primera."}`;
}

export function caminoSection(si) {
  const s = S.seasons[si], all = extras().filter((x) => x.si === si);
  const groups = new Map();
  for (const x of all) { if (!groups.has(x.torneo)) groups.set(x.torneo, []); groups.get(x.torneo).push(x); }
  const blocks = [], everyTie = [];
  for (const [tor, ms] of groups) {
    const R = bracketFor(ms, all), ties = tiesFor(ms, all) || [];
    ties.forEach((t) => (t.torneo = tor)); everyTie.push(...ties);
    const first = ms.reduce((m, x) => (x.date && x.date < m ? x.date : m), "9999");
    blocks.push({ date: first, tor, el: h("div.cm__b", [h("h3", tor), enJuego(tor) ? h("p.muted.red__q", enJuego(tor)) : null, R ? bracketView(R) : ties.length ? h("div.bk__otl", ties.sort((a, b) => a.date.localeCompare(b.date)).map(tieCard)) : h("p.muted", "Sin datos de los cruces.")]) });
  }
  // el campeón gana su último cruce (la final por el primer ascenso, aunque la fuente no traiga los penales)
  if (s.champion != null) { const mine = everyTie.filter((x) => x.t1 === s.champion || x.t2 === s.champion).sort((a, b) => a.date.localeCompare(b.date)); const last = mine[mine.length - 1]; if (last && last.pasa !== s.champion) { last.pasa = s.champion; last.note = ""; last.where = "en la final por el primer ascenso"; } }
  const pt = primeraTies(si); everyTie.push(...pt);
  if (pt.length) blocks.push({ date: pt.reduce((m, x) => (x.date && x.date < m ? x.date : m), "9999"), tor: PRIMERA, el: h("div.cm__b", [h("h3", "Promociones con Primera División"), h("p.muted.red__q", "El equipo de Primera defendía la categoría contra uno de la B Nacional: si perdía, descendía y el de la B Nacional ascendía. Fuente: RSSSF y Wikipedia (archivo promociones.csv)."), h("div.bk__otl", pt.map((x) => h("div", [tieCard(x), h("small.cm__res", x.res)])))]) });
  if (!blocks.length && !s.promoted.length) return null;
  blocks.sort((a, b) => a.date.localeCompare(b.date));
  // los ascendidos de la temporada con su camino; también los que subieron por promoción contra Primera
  const subieron = s.promoted.map(([t, how]) => ({ t, how }));
  const viaPromo = pt.filter((x) => x.pasa === x.t1 && !subieron.some((u) => u.t === x.t1)).map((x) => ({ t: x.t1, how: "Promoción" }));
  const cards = [...subieron, ...viaPromo].filter((u) => u.t != null).map(({ t, how }) => h("div.cm__s", [crest(t), h("div", [h("a", { href: href.club(t) }, h("b", T(t).short)), h("p", story(t, everyTie, how))])]));
  return sec("Cómo se definió", [
    cards.length ? h("div.cm__stories", cards) : null,
    blocks.length ? h("div.cm__timeline", [h("p.cap", "Todo lo que se jugó después de la fase regular, en orden. En verde, el que ganó o pasó."), ...blocks.map((b) => b.el)]) : null,
  ]);
}
