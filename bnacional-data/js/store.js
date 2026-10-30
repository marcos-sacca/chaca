// carga de datos y derivados
import { norm } from "./util.js";
export const S = {};
const get = async (name) => (await fetch(`data/${name}.json`)).json();

// recursos agregados o sacados desde el panel (#admin): se guardan en este navegador hasta exportarlos a data/extra.json
const LS = "bn_admin_v1";
export const emptyDelta = () => ({ fotos: [], videos: [], ocultos: { fotos: [], videos: [] } });
export function getLocal() {
  try { const d = JSON.parse(localStorage.getItem(LS) || "null"); return d ? { ...emptyDelta(), ...d, ocultos: { fotos: [], videos: [], ...(d.ocultos || {}) } } : emptyDelta(); } catch { return emptyDelta(); }
}
export function setLocal(d) { try { localStorage.setItem(LS, JSON.stringify(d)); } catch { return false; } mergeResources(); return true; }
export const hasLocal = () => { const d = getLocal(); return d.fotos.length + d.videos.length + d.ocultos.fotos.length + d.ocultos.videos.length > 0; };
export const pkey = (p) => p.id || p.img;
// arma S.galeria y S.videos con: lo de base + data/extra.json + cambios locales, sin lo que está oculto
export function mergeResources() {
  const ex = S.extra || emptyDelta(), lo = getLocal();
  const hideP = new Set([...(ex.ocultos?.fotos || []), ...lo.ocultos.fotos]), hideV = new Set([...(ex.ocultos?.videos || []), ...lo.ocultos.videos]);
  const clubs = {}, general = [];
  const add = (club, p, src) => { if (hideP.has(pkey(p))) return; const q = { ...p, _src: src }; delete q.club; if (club === "general") general.push(q); else (clubs[club] ||= []).push(q); };
  for (const [c, L] of Object.entries(S._base.clubs)) L.forEach((p) => add(c, p, "base"));
  S._base.general.forEach((p) => add("general", p, "base"));
  (ex.fotos || []).forEach((p) => add(p.club, p, "extra")); lo.fotos.forEach((p) => add(p.club, p, "local"));
  const seen = new Set(), vids = [];
  for (const [list, src] of [[S._base.videos, "base"], [ex.videos || [], "extra"], [lo.videos, "local"]]) for (const v of list) { if (hideV.has(v.id) || seen.has(v.id)) continue; seen.add(v.id); vids.push({ ...v, _src: src }); }
  S.galeria = { ...(S._base.raw || {}), clubs, general }; S.videos = vids;
}

export async function load() {
  const [meta, teams, seasons, phases, players, matches, scorers, general, fotos, videos, crests, planteles, galeria, extra, titulares] = await Promise.all(
    ["meta", "teams", "seasons", "phases", "players", "matches", "scorers", "general", "fotos", "videos", "crests", "planteles", "galeria", "extra", "titulares"].map((x) => get(x).catch(() => (x === "fotos" ? { entries: {}, general: [] } : x === "videos" ? [] : x === "galeria" ? { general: [], clubs: {} } : {}))));
  Object.assign(S, { meta, teams, seasons, phases, players, matches, scorers, scorers_raw: scorers, general, fotos, videos, crests, planteles, galeria });
  S.extra = extra && extra.fotos ? extra : emptyDelta();
  S.titulares = titulares && titulares.p ? titulares : { p: [] };
  S._base = { clubs: galeria.clubs || {}, general: galeria.general || [], videos: videos || [], raw: {} };
  mergeResources();
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
  // ascensos, descensos y reducidos por club (índices de temporada)
  S.cs = teams.map(() => ({ asc: [], champ: 0, desc: [], red: [], promo: [] }));
  seasons.forEach((s, si) => {
    s.promoted.forEach(([t, how]) => { S.cs[t].asc.push(si); if (how === "Campeón") S.cs[t].champ++; });
    (s.desc || []).forEach((t) => S.cs[t].desc.push(si)); (s.red || []).forEach((t) => S.cs[t].red.push(si)); (s.promo || []).forEach((t) => S.cs[t].promo.push(si));
  });
  S.general.forEach((r) => { const c = S.cs[r[1]]; r[13] = c.asc.length; r[14] = c.desc.length; r[15] = c.red.length; });
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
