// carga de datos y derivados
import { norm } from "./util.js";
export const S = {};
const get = async (name) => (await fetch(`data/${name}.json`)).json();

export async function load() {
  const [meta, teams, seasons, phases, players, matches, scorers, general, fotos, videos, crests, planteles, galeria] = await Promise.all(
    ["meta", "teams", "seasons", "phases", "players", "matches", "scorers", "general", "fotos", "videos", "crests", "planteles", "galeria"].map((x) => get(x).catch(() => (x === "fotos" ? { entries: {}, general: [] } : x === "videos" ? [] : x === "galeria" ? { general: [], clubs: {} } : {}))));
  Object.assign(S, { meta, teams, seasons, phases, players, matches, scorers, scorers_raw: scorers, general, fotos, videos, crests, planteles, galeria });
  S.teamBy = new Map(teams.map((t, i) => [t.s, i]));
  S.seasonBy = new Map(seasons.map((s, i) => [s.id, i]));
  // partidos por temporada y por club
  S.mBySeason = seasons.map(() => []);
  S.mByTeam = teams.map(() => []);
  matches.forEach((m, i) => { S.mBySeason[m[0]].push(i); S.mByTeam[m[4]].push(i); S.mByTeam[m[5]].push(i); });
  S.scBySeason = seasons.map(() => ({}));
  for (const [s_, p, t, g] of scorers) S.scBySeason[s_][p + "|" + t] = { name: players[p], team: t, g };
  // goleadores históricos por jugador
  const byP = new Map();
  for (const [s, p, t, g, pen] of scorers) {
    let o = byP.get(p); if (!o) byP.set(p, o = { p, name: players[p], goals: 0, pen: 0, teams: new Map(), seasons: new Set() });
    o.goals += g; o.pen += pen; o.teams.set(t, (o.teams.get(t) || 0) + g); o.seasons.add(s);
  }
  S.scorers = [...byP.values()].map((o) => ({ ...o, teamList: [...o.teams.entries()].sort((a, b) => b[1] - a[1]).map((x) => x[0]), s0: Math.min(...o.seasons), s1: Math.max(...o.seasons) })).sort((a, b) => b.goals - a.goals);
  // ascensos con foto
  S.ascensos = [];
  seasons.forEach((s, si) => s.promoted.forEach(([t, how]) => S.ascensos.push({ si, t, how, season: s, key: `${s.id}|${teams[t].s}` })));
  S.crest = (ti) => S.crests[S.teams[ti].s] || null;
  S.photo = (key) => fotos.entries[key] || null;
  S.clubPhoto = (slug) => fotos.clubs?.[slug] || null;
  S.index = [
    ...teams.map((t, i) => ({ k: "Club", n: t.n, d: t.prov || "", href: `#c-${t.s}`, q: norm(t.n + " " + t.short) })),
    ...seasons.map((s) => ({ k: "Temporada", n: s.label, d: s.champion != null ? "Campeón: " + teams[s.champion].short : "", href: `#t-${s.id}`, q: norm(s.label) })),
    ...S.scorers.slice(0, 600).map((o) => ({ k: "Goleador", n: o.name, d: `${o.goals} goles · ${teams[o.teamList[0]].short}`, href: "#goleadores", q: norm(o.name), player: o.name })),
  ];
}
export function search(q, lim = 10) {
  q = norm(q.trim()); if (!q) return [];
  const out = [];
  for (const it of S.index) { const i = it.q.indexOf(q); if (i >= 0) out.push([i === 0 ? 0 : it.q[i - 1] === " " ? 1 : 2, it]); }
  return out.sort((a, b) => a[0] - b[0] || (a[1].k === "Club" ? -1 : 0)).slice(0, lim).map((x) => x[1]);
}
// puntos por partido de un club en una temporada (según el sistema de puntos de la temporada)
export function clubSeason(ti, si) {
  const w = S.seasons[si].ptsw || 3; let pj = 0, pg = 0, pe = 0, pp = 0, gf = 0, gc = 0;
  for (const i of S.mByTeam[ti]) {
    const m = S.matches[i]; if (m[0] !== si) continue;
    const home = m[4] === ti, a = home ? m[6] : m[7], b = home ? m[7] : m[6];
    pj++; gf += a; gc += b; if (a > b) pg++; else if (a === b) pe++; else pp++;
  }
  return { pj, pg, pe, pp, gf, gc, pts: pg * w + pe, eff: pj ? (pg * w + pe) / (pj * w) : null };
}
