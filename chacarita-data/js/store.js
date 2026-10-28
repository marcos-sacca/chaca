// Datos y cálculos. Las reglas replican las del Excel "DATACHACA Máster":
//  · % de efectividad = puntos a 3 por victoria / puntos en juego (se compara bien entre épocas).
//  · Rachas en orden de fecha, siguen aunque cambie el torneo; si dos rachas empatan el récord, se muestra la primera.
//  · Récords por temporada: solo la competencia principal (liga + definiciones, sin copas) y con un mínimo de partidos.
import { norm, parseISO } from "./util.js";

export const DIVS = ["Primera División", "Segunda División", "Tercera División", "Copa Argentina", "Copas nacionales"];
export const DIV_SHORT = { "Primera División": "Primera", "Segunda División": "Segunda", "Tercera División": "Tercera", "Copa Argentina": "Copa Argentina", "Copas nacionales": "Otras copas" };
export const S = {};

const J = (f) => fetch(`data/${f}.json`).then((r) => { if (!r.ok) throw new Error(f); return r.json(); });

export async function load() {
  const [matches, torneos, players, lineups, estadios, meta] = await Promise.all(["matches", "torneos", "players", "lineups", "estadios", "meta"].map(J));
  Object.assign(S, { matches, torneos, players, lineups, estadios, meta });
  const byId = new Map();
  for (const m of matches) {
    const t = torneos[m.t];
    m.tn = t.n; m.div = t.div; m.tipo = t.tipo; m.sd = t.sd; m.y = +m.d.slice(0, 4); m.md = m.d.slice(5);
    m.dec = Math.floor(m.y / 10) * 10; m.main = t.tipo !== "Copa";
    byId.set(m.id, m);
  }
  S.byId = byId;

  // rivales
  const rv = new Map();
  for (const m of matches) { if (!rv.has(m.r)) rv.set(m.r, []); rv.get(m.r).push(m); }
  S.rivals = [...rv].map(([name, list]) => ({ name, list, s: sum(list) })).sort((a, b) => b.s.pj - a.s.pj || a.name.localeCompare(b.name, "es"));
  S.rivalMap = new Map(S.rivals.map((r) => [r.name, r]));

  // temporadas (temporada deportiva + división principal)
  const sm = new Map();
  for (const m of matches) {
    const key = m.sd;
    if (!sm.has(key)) sm.set(key, { sd: key, list: [], torneos: new Set() });
    const o = sm.get(key); o.list.push(m); o.torneos.add(m.t);
  }
  S.seasons = [...sm.values()].map((o) => {
    const main = o.list.filter((m) => m.main);
    const cnt = {}; main.forEach((m) => (cnt[m.div] = (cnt[m.div] || 0) + 1));
    const div = Object.entries(cnt).sort((a, b) => b[1] - a[1])[0]?.[0] || o.list[0].div;
    return { sd: o.sd, div, list: o.list, main: main.filter((m) => m.div === div), torneos: [...o.torneos].map((i) => torneos[i]), y0: o.list[0].y };
  }).sort((a, b) => a.list[0].d.localeCompare(b.list[0].d));
  S.seasonMap = new Map(S.seasons.map((s) => [s.sd, s]));

  // jugadores: goles (de GOLES) y apariciones (de APARICIONES)
  const pm = new Map();
  const P = (name) => { if (!pm.has(name)) pm.set(name, { name, goals: [], ownGoals: 0, apps: [] }); return pm.get(name); };
  for (const m of matches) for (const g of m.g || []) { if (!g.p || g.ec) continue; P(g.p).goals.push({ m, min: g.m, pen: g.pen }); }
  for (const [id, arr] of Object.entries(lineups)) { const m = byId.get(+id); if (!m) continue; for (const [pid, rol] of arr) P(players[pid]).apps.push({ m, rol }); }
  S.playerList = [...pm.values()].map((p) => {
    const ys = [...p.goals.map((g) => g.m.y), ...p.apps.map((a) => a.m.y)];
    p.ng = p.goals.length; p.pj = p.apps.length; p.tit = p.apps.filter((a) => a.rol === 0).length;
    p.y0 = ys.length ? Math.min(...ys) : null; p.y1 = ys.length ? Math.max(...ys) : null;
    return p;
  });
  S.playerMap = new Map(S.playerList.map((p) => [p.name, p]));
  S.hasLineup = new Set(Object.keys(lineups).map(Number));

  S.facts = computeFacts();
  return S;
}

// ───────── resúmenes
export function sum(list) {
  const s = { pj: 0, g: 0, e: 0, p: 0, gf: 0, gc: 0 };
  for (const m of list) { s.pj++; s[m.res.toLowerCase()]++; s.gf += m.gf ?? 0; s.gc += m.gc ?? 0; }
  s.dg = s.gf - s.gc; s.pts3 = 3 * s.g + s.e; s.ef = s.pj ? s.pts3 / (3 * s.pj) : null;
  s.pts = list.reduce((a, m) => a + (m.pt ?? 0), 0);
  return s;
}
export const byCond = (list, c) => list.filter((m) => m.c === c);
export const score = (m) => `${m.gl ?? "?"}-${m.gv ?? "?"}`;
export const title = (m) => `${m.l} ${score(m)} ${m.v}`;
export const condName = { L: "Local", V: "Visitante", N: "Neutral" };

// ───────── filtros de partidos
export function filterMatches(o = {}) {
  const q = o.q ? norm(o.q) : null;
  return S.matches.filter((m) =>
    (!o.div || m.div === o.div) && (!o.rival || m.r === o.rival) && (!o.cond || m.c === o.cond) && (!o.res || m.res === o.res) &&
    (!o.y0 || m.y >= o.y0) && (!o.y1 || m.y <= o.y1) && (!o.sd || m.sd === o.sd) && (!o.tn || m.tn === o.tn) &&
    (!o.dt || m.dt === o.dt) && (!o.arb || m.arb === o.arb) && (!o.cd || m.cd === o.cd) &&
    (!q || norm(`${m.l} ${m.v} ${m.tn} ${m.dt ?? ""} ${m.arb ?? ""} ${m.e ?? ""}`).includes(q)));
}

// ───────── rachas (en orden de fecha)
export const STREAKS = [
  ["Victorias consecutivas", (m) => m.res === "G"],
  ["Partidos invicto (sin perder)", (m) => m.res !== "P"],
  ["Partidos sin ganar", (m) => m.res !== "G"],
  ["Derrotas consecutivas", (m) => m.res === "P"],
  ["Empates consecutivos", (m) => m.res === "E"],
  ["Partidos seguidos convirtiendo", (m) => (m.gf ?? 0) > 0],
  ["Partidos seguidos sin convertir", (m) => (m.gf ?? 0) === 0],
  ["Vallas invictas seguidas", (m) => (m.gc ?? 0) === 0],
];
export function longestRun(list, test) {
  let best = { len: 0, i: -1 }, cur = 0, start = 0;
  list.forEach((m, i) => {
    if (test(m)) { if (cur === 0) start = i; cur++; if (cur > best.len) best = { len: cur, i: start }; } else cur = 0;
  });
  const now = (() => { let k = 0; for (let i = list.length - 1; i >= 0 && test(list[i]); i--) k++; return k; })();
  const first = best.len ? list[best.i] : null, last = best.len ? list[best.i + best.len - 1] : null;
  return { len: best.len, first, last, cutter: best.len ? list[best.i + best.len] || null : null, now };
}

// ───────── campañas por temporada (competencia principal, sin copas)
export function campaigns() {
  return S.seasons.map((s) => ({ sd: s.sd, div: s.div, s: sum(s.main), list: s.main })).filter((c) => c.s.pj > 0);
}

// ───────── goleadores
export function topScorers({ div, dec, sd, tn } = {}) {
  const map = new Map();
  for (const p of S.playerList) {
    const gs = p.goals.filter((g) => (!div || g.m.div === div) && (!dec || g.m.dec === +dec) && (!sd || g.m.sd === sd) && (!tn || g.m.tn === tn));
    if (!gs.length) continue;
    const apps = p.apps.filter((a) => (!div || a.m.div === div) && (!dec || a.m.dec === +dec) && (!sd || a.m.sd === sd) && (!tn || a.m.tn === tn));
    const gl = gs.filter((g) => S.hasLineup.has(g.m.id)).length;
    map.set(p.name, { p, g: gs.length, y0: Math.min(...gs.map((g) => g.m.y)), y1: Math.max(...gs.map((g) => g.m.y)), pj: apps.length, gl, pen: gs.filter((g) => g.pen).length });
  }
  return [...map.values()].sort((a, b) => b.g - a.g || a.y0 - b.y0 || a.p.name.localeCompare(b.p.name, "es"));
}

// ───────── efemérides
export function onDay(md) { return S.matches.filter((m) => m.md === md).sort((a, b) => b.d.localeCompare(a.d)); }

// ───────── datos destacados de la portada
function computeFacts() {
  const M = S.matches;
  const wins = M.filter((m) => m.res === "G" && m.gf != null);
  const bigWin = wins.reduce((a, m) => ((m.gf - m.gc) > (a.gf - a.gc) || ((m.gf - m.gc) === (a.gf - a.gc) && m.gf > a.gf) ? m : a), wins[0]);
  const losses = M.filter((m) => m.res === "P" && m.gf != null);
  const bigLoss = losses.reduce((a, m) => ((m.gc - m.gf) > (a.gc - a.gf) ? m : a), losses[0]);
  const mostGoals = M.reduce((a, m) => ((m.gf ?? 0) + (m.gc ?? 0) > (a.gf ?? 0) + (a.gc ?? 0) ? m : a), M[0]);
  const scorer = [...S.playerList].sort((a, b) => b.ng - a.ng)[0];
  const appear = [...S.playerList].sort((a, b) => b.pj - a.pj)[0];
  const unb = longestRun(M, (m) => m.res !== "P"), winRun = longestRun(M, (m) => m.res === "G");
  return { bigWin, bigLoss, mostGoals, scorer, appear, unb, winRun };
}

// ───────── búsqueda global
export function searchIndex() {
  const out = [];
  for (const r of S.rivals) out.push({ k: "Rival", n: r.name, d: `${r.s.pj} partidos`, href: `#/rivales/${encodeURIComponent(r.name)}`, t: norm(r.name) });
  for (const p of S.playerList) if (p.ng || p.pj > 20) out.push({ k: "Jugador", n: p.name, d: p.ng ? `${p.ng} goles` : `${p.pj} partidos`, href: `#/jugadores/${encodeURIComponent(p.name)}`, t: norm(p.name), w: p.ng + p.pj / 10 });
  for (const s of S.seasons) out.push({ k: "Temporada", n: s.sd, d: s.div, href: `#/temporadas/${encodeURIComponent(s.sd)}`, t: norm(s.sd + " " + s.div) });
  for (const t of S.torneos) out.push({ k: "Torneo", n: t.n, d: t.div, href: `#/partidos?tn=${encodeURIComponent(t.n)}`, t: norm(t.n) });
  return out;
}
export function search(q, idx, max = 9) {
  const t = norm(q);
  if (!t) return [];
  const sc = (e) => (e.t === t ? 100 : e.t.startsWith(t) ? 60 : e.t.split(" ").some((w) => w.startsWith(t)) ? 40 : e.t.includes(t) ? 20 : 0);
  return idx.map((e) => ({ e, s: sc(e) + (e.k === "Rival" ? 2 : 0) + (e.w ? Math.min(e.w, 9) / 10 : 0) })).filter((x) => x.s >= 20).sort((a, b) => b.s - a.s).slice(0, max).map((x) => x.e);
}
export { parseISO };
