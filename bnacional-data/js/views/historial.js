// historiales: cara a cara entre dos clubes y resumen de un club contra cada rival
import { route } from "../app.js";
import { S } from "../store.js";
import { h, n, fshort, imgSrc, mdate } from "../util.js";
import { head, sec, table, T, href, crest, monogram } from "./common.js";

const SEP = "_vs_";
export const hrefH2H = (a, b) => `#historial-${S.teams[a].s}${b == null ? "" : SEP + S.teams[b].s}`;

// partidos entre a y b, del más viejo al más nuevo
export function h2hMatches(a, b) {
  return S.mByTeam[a].filter((i) => { const m = S.matches[i]; return m[4] === b || m[5] === b; });
}
// resumen desde el punto de vista de a
export function h2hSummary(a, list) {
  const o = { pj: 0, pg: 0, pe: 0, pp: 0, gf: 0, gc: 0, loc: { pj: 0, pg: 0, pe: 0, pp: 0 }, vis: { pj: 0, pg: 0, pe: 0, pp: 0 } };
  for (const i of list) {
    const m = S.matches[i], home = m[4] === a, x = home ? m[6] : m[7], y = home ? m[7] : m[6], side = home ? o.loc : o.vis;
    const r = x > y ? "pg" : x === y ? "pe" : "pp";
    o.pj++; o.gf += x; o.gc += y; o[r]++; side.pj++; side[r]++;
  }
  return o;
}
// historial de a contra todos sus rivales
export function rivalsOf(a) {
  const by = new Map();
  for (const i of S.mByTeam[a]) {
    const m = S.matches[i], b = m[4] === a ? m[5] : m[4];
    if (!by.has(b)) by.set(b, []);
    by.get(b).push(i);
  }
  return [...by.entries()].map(([b, list]) => ({ b, list, ...h2hSummary(a, list), last: list[list.length - 1] }));
}

const res = (a, i) => { const m = S.matches[i], home = m[4] === a, x = home ? m[6] : m[7], y = home ? m[7] : m[6]; return x > y ? "G" : x === y ? "E" : "P"; };
const big = (ti) => { const c = S.crest(ti); return c ? h("img.h2h__crest", { src: imgSrc(c.img), alt: "Escudo de " + T(ti).short }) : monogram(ti, "mono--xl"); };
const sorted = () => S.teams.map((t, i) => i).sort((x, y) => T(x).short.localeCompare(T(y).short, "es"));

function picker(a, b) {
  const opt = (sel) => [h("option", { value: "" }, "Elegí un club"), ...sorted().map((i) => h("option", { value: S.teams[i].s, selected: i === sel }, T(i).short))];
  const go = () => {
    const x = S.teamBy.get(sa.value), y = S.teamBy.get(sb.value);
    if (x == null) { location.hash = "#historial"; return; }
    location.hash = hrefH2H(x, y != null && y !== x ? y : null);
  };
  const sa = h("select", { "aria-label": "Primer club", onchange: go }, opt(a));
  const sb = h("select", { "aria-label": "Segundo club", onchange: go }, opt(b));
  const swap = h("button.btn.btn--ghost.btn--s", { type: "button", disabled: a == null || b == null, onclick: () => { if (a != null && b != null) location.hash = hrefH2H(b, a); } }, "⇄ Invertir");
  return h("div.toolbar.h2h__pick", [sa, h("span.muted", "vs"), sb, swap]);
}

function rivalsTable(a, { limit = 0, filter = "" } = {}) {
  const f = filter.trim().toLowerCase();
  let rows = rivalsOf(a).sort((x, y) => y.pj - x.pj || y.pg - x.pg).filter((r) => !f || T(r.b).short.toLowerCase().includes(f));
  if (limit) rows = rows.slice(0, limit);
  return table([{ label: "Rival" }, ...["PJ", "PG", "PE", "PP", "GF", "GC"].map((l) => ({ label: l, cls: "num" })), { label: "Último", cls: "num" }],
    rows.map((r) => { const m = S.matches[r.last]; return h("tr", [
      h("td", h("a", { href: hrefH2H(a, r.b) }, [crest(r.b), T(r.b).short])),
      ...[r.pj, r.pg, r.pe, r.pp, r.gf, r.gc].map((v) => h("td.num", v)),
      h("td.num", [h("span.h2h__r.h2h__r--" + res(a, r.last), res(a, r.last)), " ", h("a", { href: hrefH2H(a, r.b) }, `${m[4] === a ? m[6] : m[7]}-${m[4] === a ? m[7] : m[6]}`), h("small.muted", " " + S.seasons[m[0]].label)]),
    ]); }));
}

// bloque para la ficha de cada club
export function clubRivalsSection(a) {
  const total = rivalsOf(a).length, box = h("div"), st = { all: false, q: "" };
  const more = h("button.btn.btn--ghost.btn--s", { type: "button" });
  const draw = () => {
    box.replaceChildren(rivalsTable(a, { limit: st.all || st.q ? 0 : 12, filter: st.q }));
    more.textContent = st.all ? "Ver solo los 12 más jugados" : `Ver los ${total} rivales`;
    more.hidden = total <= 12 || !!st.q;
  };
  more.onclick = () => { st.all = !st.all; draw(); };
  draw();
  return sec("Historial contra cada rival", [
    h("p.muted", `Partidos de fase regular contra los ${total} clubes que enfrentó en la categoría. Tocá un rival para ver todos los partidos.`),
    h("div.toolbar", h("input", { type: "search", placeholder: "Buscar rival", "aria-label": "Buscar rival", oninput: (e) => { st.q = e.target.value; draw(); } })),
    box, h("p", more)]);
}

// historial de todos los tiempos (fuentes externas, data/historial_completo.json); null si no hay para ese cruce
function completoBlock(a, b) {
  const sa = S.teams[a].s, sb = S.teams[b].s, e = S.completo.find((x) => (x.a === sa && x.b === sb) || (x.a === sb && x.b === sa));
  if (!e) return null;
  const same = e.a === sa, w = same ? e.ga : e.gb, l = same ? e.gb : e.ga, gf = same ? e.gfa : e.gfb, gc = same ? e.gfb : e.gfa;
  return h("section.h2h__full", [
    h("h2.h2h__sub", "Historial completo, todas las competencias oficiales"),
    h("div.h2h", [
      h("a.h2h__side", { href: href.club(a) }, [big(a), h("b", T(a).short)]),
      h("div.h2h__mid", [h("div.h2h__n", [h("span", w), h("i", "–"), h("span", e.e), h("i", "–"), h("span", l)]), h("small", `Ganó ${T(a).short} · Empates · Ganó ${T(b).short}`)]),
      h("a.h2h__side", { href: href.club(b) }, [big(b), h("b", T(b).short)]),
    ]),
    h("p.muted.h2h__note", [`${n(e.pj)} partidos hasta el ${e.corte}${gf != null ? ` · goles ${n(gf)} a ${n(gc)} (${T(a).short} a ${T(b).short})` : ""}. ${e.nota} Dato de una fuente externa, tomado tal cual: `, h("a", { href: e.fuente, target: "_blank", rel: "noopener" }, new URL(e.fuente).hostname.replace(/^es\./, "").replace("wikipedia.org", "Wikipedia")), "."]),
  ]);
}

route("historial", async (r) => {
  const page = h("div.wrap.page");
  const [sa, sb] = (r.arg || "").split(SEP);
  const a = sa ? S.teamBy.get(sa) : null, b = sb ? S.teamBy.get(sb) : null;
  page.append(head("Historiales", a != null && b != null ? `${T(a).short} vs ${T(b).short}` : "Cara a cara entre clubes", "Todos los partidos de fase regular de la B Nacional y la Primera Nacional desde 1986/87 entre dos clubes. No incluye reducidos ni promociones."));
  page.append(h("p", h("a.link", { href: "#clasicos" }, "Ver los clásicos de cada club →")));
  page.append(picker(a, b));
  if (a == null) { page.append(h("p.muted", "Elegí dos clubes para ver su historial.")); return { page, title: "Historiales" }; }
  if (b == null) { page.append(sec(`${T(a).short} contra cada rival`, rivalsTable(a))); return { page, title: `Historial de ${T(a).short}` }; }

  const list = h2hMatches(a, b), s = h2hSummary(a, list), full = completoBlock(a, b);
  if (full) page.append(full, h("h2.h2h__sub", "En la B Nacional y la Primera Nacional (fase regular)"));
  page.append(h("div.h2h", [
    h("a.h2h__side", { href: href.club(a) }, [big(a), h("b", T(a).short)]),
    h("div.h2h__mid", [h("div.h2h__n", [h("span", s.pg), h("i", "–"), h("span", s.pe), h("i", "–"), h("span", s.pp)]), h("small", `Ganó ${T(a).short} · Empates · Ganó ${T(b).short}`)]),
    h("a.h2h__side", { href: href.club(b) }, [big(b), h("b", T(b).short)]),
  ]));
  if (!list.length) { page.append(h("p.muted", "Nunca se enfrentaron en la categoría.")); return { page, title: `${T(a).short} vs ${T(b).short}` }; }

  const bar = (v, cls) => v ? h("span.h2h__seg." + cls, { style: { flex: v }, title: v }) : null;
  page.append(h("div.h2h__bar", { role: "img", "aria-label": `${s.pg} victorias de ${T(a).short}, ${s.pe} empates, ${s.pp} victorias de ${T(b).short}` }, [bar(s.pg, "is-a"), bar(s.pe, "is-e"), bar(s.pp, "is-b")].filter(Boolean)));
  const first = S.matches[list[0]], last = S.matches[list[list.length - 1]];
  page.append(h("div.stats", [["Partidos", s.pj], [`Goles ${T(a).short}`, s.gf], [`Goles ${T(b).short}`, s.gc], [`${T(a).short} de local`, `${s.loc.pg}-${s.loc.pe}-${s.loc.pp}`], [`${T(a).short} de visitante`, `${s.vis.pg}-${s.vis.pe}-${s.vis.pp}`]].map(([l, v]) => h("div.stat", [h("b", typeof v === "number" ? n(v) : v), h("span", l)]))));
  page.append(h("p.muted.h2h__note", `Primer partido: ${mdate(first) || "fecha sin confirmar"} (${S.seasons[first[0]].label}). Último: ${mdate(last) || "fecha sin confirmar"} (${S.seasons[last[0]].label}). De local y de visitante: ganados-empatados-perdidos de ${T(a).short}.`));

  // mayores goleadas de cada lado
  const margin = (i) => { const m = S.matches[i]; return (m[4] === a ? m[6] - m[7] : m[7] - m[6]); };
  const bestA = list.slice().sort((x, y) => margin(y) - margin(x))[0], bestB = list.slice().sort((x, y) => margin(x) - margin(y))[0];
  const scoreTxt = (i) => { const m = S.matches[i]; return `${T(m[4]).short} ${m[6]}-${m[7]} ${T(m[5]).short} (${S.seasons[m[0]].label})`; };
  const k = [margin(bestA) > 0 ? h("p", [h("b", `Mayor triunfo de ${T(a).short}: `), scoreTxt(bestA)]) : null, margin(bestB) < 0 ? h("p", [h("b", `Mayor triunfo de ${T(b).short}: `), scoreTxt(bestB)]) : null].filter(Boolean);
  if (k.length) page.append(h("div.kline", k));

  // lista de partidos con filtros por resultado y por condición (siempre desde el punto de vista del primer club)
  const fl = { r: "todos", c: "todas" }, box = h("div"), filt = h("div.h2h__filt");
  const isHome = (i) => S.matches[i][4] === a;
  const pass = (i) => (fl.r === "todos" || res(a, i) === fl.r) && (fl.c === "todas" || (fl.c === "loc") === isHome(i));
  const group = (key, opts) => h("div.chips.h2h__chips", { role: "group" }, opts.map(([v, l]) => {
    const cnt = list.filter((i) => (key === "r" ? (v === "todos" || res(a, i) === v) && (fl.c === "todas" || (fl.c === "loc") === isHome(i)) : (v === "todas" || (v === "loc") === isHome(i)) && (fl.r === "todos" || res(a, i) === fl.r))).length;
    return h("button.chip", { type: "button", "aria-pressed": String(fl[key] === v), disabled: !cnt && fl[key] !== v, onclick: () => { fl[key] = v; draw(); } }, [l, h("small.h2h__cnt", ` ${cnt}`)]);
  }));
  const draw = () => {
    filt.replaceChildren(
      group("r", [["todos", "Todos"], ["G", `Ganó ${T(a).short}`], ["E", "Empates"], ["P", `Ganó ${T(b).short}`]]),
      group("c", [["todas", "Local y visitante"], ["loc", `${T(a).short} de local`], ["vis", `${T(a).short} de visitante`]]));
    const rows = list.filter(pass).slice().reverse();
    box.replaceChildren(rows.length ? table([{ label: "Fecha" }, { label: "Temporada" }, { label: "Local", cls: "num" }, { label: "" }, { label: "Visitante" }, { label: "" }],
      rows.map((i) => { const m = S.matches[i], r_ = res(a, i), win = m[6] > m[7] ? 4 : m[6] < m[7] ? 5 : -1; return h("tr", [
        h("td", mdate(m)), h("td", h("a", { href: href.season(m[0]) }, S.seasons[m[0]].label)),
        h("td.num", win === 4 ? h("b", T(m[4]).short) : T(m[4]).short),
        h("td.h2h__score", `${m[6]} - ${m[7]}`),
        h("td", win === 5 ? h("b", T(m[5]).short) : T(m[5]).short),
        h("td", h("span.h2h__r.h2h__r--" + r_, { title: { G: "Ganó ", E: "Empató ", P: "Perdió " }[r_] + T(a).short }, r_)),
      ]); })) : h("p.muted", "No hay partidos con esos filtros."));
  };
  draw();
  page.append(sec("Todos los partidos", [filt, box]));
  return { page, title: `${T(a).short} vs ${T(b).short}` };
});
