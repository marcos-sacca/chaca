// Ejecuta los cálculos del sitio en Node (sin navegador) y los compara con lo que trae la planilla. Ver verify_vs_excel.py.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
const root = path.join(path.dirname(fileURLToPath(import.meta.url)), "..");
globalThis.fetch = async (u) => ({ ok: true, json: async () => JSON.parse(fs.readFileSync(path.join(root, u), "utf8")) });
const { S, load, sum, byCond, longestRun, STREAKS, campaigns, topScorers, onDay } = await import(path.join(root, "js/store.js"));
await load();
const X = JSON.parse(fs.readFileSync(process.argv[2], "utf8"));
let ok = 0, bad = 0;
const check = (name, got, want, tol = 0) => {
  const same = typeof want === "number" ? Math.abs(got - want) <= (tol || 1e-9) : String(got) === String(want);
  if (same) ok++; else { bad++; console.log(`  ✗ ${name}: sitio=${got} · planilla=${want}`); }
};
const sec = (t) => console.log(`\n${t}`);

sec("Totales (DATOS CURIOSOS)");
const T = { Total: S.matches, Local: byCond(S.matches, "L"), Visitante: byCond(S.matches, "V"), Neutral: byCond(S.matches, "N") };
for (const [k, v] of Object.entries(X.totales)) { const s = sum(T[k]); [["PJ", s.pj], ["G", s.g], ["E", s.e], ["P", s.p], ["GF", s.gf], ["GC", s.gc]].forEach(([n, g], i) => check(`${k} ${n}`, g, v[i])); }

sec("Rivales más enfrentados por división");
for (const [div, list] of Object.entries(X.rivales_por_div)) {
  const c = new Map(); S.matches.filter((m) => m.div === div).forEach((m) => c.set(m.r, (c.get(m.r) || 0) + 1));
  list.forEach(([name, pj]) => check(`${div} · ${name}`, c.get(name) ?? 0, pj));
}

sec("Canchas (por club dueño de la cancha)");
{
  const by = new Map(); S.matches.filter((m) => m.cd).forEach((m) => { if (!by.has(m.cd)) by.set(m.cd, []); by.get(m.cd).push(m); });
  check("cantidad de canchas listadas", by.size >= X.canchas.length, true);
  X.canchas.forEach(([name, pj, g, e, p, ef]) => { const s = sum(by.get(name) || []); check(`${name} PJ`, s.pj, pj); check(`${name} G-E-P`, `${s.g}-${s.e}-${s.p}`, `${g}-${e}-${p}`); check(`${name} efect.`, s.ef ?? 0, ef, 1e-6); });
}

sec("Año calendario");
X.anio.forEach(([y, pj, g, e, p, gf, gc, dg, ef]) => { const s = sum(S.matches.filter((m) => m.y === y)); check(`${y} PJ`, s.pj, pj); check(`${y} G-E-P`, `${s.g}-${s.e}-${s.p}`, `${g}-${e}-${p}`); check(`${y} GF:GC`, `${s.gf}:${s.gc}`, `${gf}:${gc}`); check(`${y} efect.`, s.ef, ef, 1e-6); });

sec(`Récords por temporada (mínimo ${X.min_pj} partidos, competencia principal)`);
{
  const cs = campaigns().filter((c) => c.s.pj >= X.min_pj);
  const best = (key, dir = 1) => cs.reduce((a, c) => (dir * key(c) > dir * key(a) ? c : a), cs[0]);
  const f = { "Mejor campaña (% efect.)": best((c) => c.s.ef), "Peor campaña (% efect.)": best((c) => c.s.ef, -1), "Más victorias": best((c) => c.s.g), "Más derrotas": best((c) => c.s.p), "Más goles a favor": best((c) => c.s.gf), "Más goles en contra": best((c) => c.s.gc), "Mejor diferencia de gol": best((c) => c.s.dg), "Peor diferencia de gol": best((c) => c.s.dg, -1) };
  const val = { "Mejor campaña (% efect.)": (c) => c.s.ef, "Peor campaña (% efect.)": (c) => c.s.ef, "Más victorias": (c) => c.s.g, "Más derrotas": (c) => c.s.p, "Más goles a favor": (c) => c.s.gf, "Más goles en contra": (c) => c.s.gc, "Mejor diferencia de gol": (c) => c.s.dg, "Peor diferencia de gol": (c) => c.s.dg };
  X.records_temp.forEach(([name, v, sd, div]) => {
    if (f[name]) { check(`${name} valor`, val[name](f[name]), v, 1e-6); check(`${name} temporada`, f[name].sd, sd); check(`${name} división`, f[name].div, div); }
    else if (name.startsWith("Goleador")) { let b = null; S.seasons.forEach((se) => { const t = topScorers({ sd: se.sd })[0]; if (t && (!b || t.g > b.g)) b = { g: t.g, sd: se.sd }; }); check(`${name} valor`, b.g, v); check(`${name} temporada`, b.sd, sd); }
  });
}

sec("Campañas por temporada (competencia principal)");
{
  const cs = new Map(campaigns().map((c) => [c.sd, c]));
  X.campanas.forEach(([sd, div, pj, g, e, p, gf, gc, ef, scorer, goles, pts, pos]) => {
    const c = cs.get(String(sd)); if (!c) { check(`${sd} existe`, "no", "sí"); return; }
    check(`${sd} división`, c.div, div); check(`${sd} PJ`, c.s.pj, pj); check(`${sd} G-E-P`, `${c.s.g}-${c.s.e}-${c.s.p}`, `${g}-${e}-${p}`); check(`${sd} GF:GC`, `${c.s.gf}:${c.s.gc}`, `${gf}:${gc}`); check(`${sd} efect.`, c.s.ef, ef, 1e-6);
    check(`${sd} puntos reales`, c.s.pts, pts); const cnt = new Map(); c.list.forEach((m) => (m.g || []).forEach((g) => { if (g.p && !g.ec) cnt.set(g.p, (cnt.get(g.p) || 0) + 1); })); if (goles) check(`${sd} goles del goleador (solo competencia principal)`, Math.max(0, ...cnt.values()), goles);
  });
}

sec(`Rachas contra ${X.filtro_rachas.rival} (todas las divisiones y condiciones)`);
{
  const L = S.matches.filter((m) => m.r === X.filtro_rachas.rival);
  X.rachas.forEach(([name, rec, desde, hasta, , , , now]) => {
    const t = STREAKS.find((s) => s[0].startsWith(name.slice(0, 24))); if (!t) return;
    const r = longestRun(L, t[1]);
    check(`${name} récord`, r.len, rec); check(`${name} desde`, r.first?.d, desde); check(`${name} hasta`, r.last?.d, hasta); check(`${name} actual`, r.now, now);
  });
  X.rachas_cond.forEach(([name, recL, nowL, recV, , , nowV]) => {
    const t = STREAKS.find((s) => s[0].startsWith(name.slice(0, 24))); if (!t) return;
    const l = longestRun(L.filter((m) => m.c === "L"), t[1]), v = longestRun(L.filter((m) => m.c === "V"), t[1]);
    check(`${name} récord local`, l.len, recL); check(`${name} actual local`, l.now, nowL); check(`${name} récord visitante`, v.len, recV); check(`${name} actual visitante`, v.now, nowV);
  });
}

sec(`CHACADATA (${X.chacadata.rival})`);
{
  const rv = S.rivalMap.get(X.chacadata.rival), L = rv.list;
  const cmp = (label, s, row) => { check(`${label} PJ`, s.pj, row[1]); check(`${label} G-E-P`, `${s.g}-${s.e}-${s.p}`, `${row[2]}-${row[3]}-${row[4]}`); check(`${label} GF:GC`, `${s.gf}:${s.gc}`, `${row[5]}:${row[6]}`); if (s.pj) check(`${label} efect.`, s.ef, row[8], 1e-6); };
  cmp("Total", sum(L), X.chacadata.tot[0]); cmp("Local", sum(byCond(L, "L")), X.chacadata.tot[1]); cmp("Visitante", sum(byCond(L, "V")), X.chacadata.tot[2]);
  X.chacadata.div.forEach((row) => cmp(row[0], sum(L.filter((m) => m.div === row[0])), row));
  const [first, last, bw, bl, mg] = X.chacadata.clave.map((r) => r[1]);
  check("primer partido", L[0].id, first); check("último partido", L[L.length - 1].id, last);
  const wins = L.filter((m) => m.res === "G"), loss = L.filter((m) => m.res === "P");
  check("mayor victoria", wins.reduce((a, m) => ((m.gf - m.gc) > (a.gf - a.gc) ? m : a)).id, bw);
  check("peor derrota", loss.reduce((a, m) => ((m.gc - m.gf) > (a.gc - a.gf) ? m : a)).id, bl);
  check("más goles", L.reduce((a, m) => ((m.gf + m.gc) > (a.gf + a.gc) ? m : a)).id, mg);
  const sc = new Map(); L.forEach((m) => (m.g || []).forEach((g) => { if (g.p && !g.ec) sc.set(g.p, (sc.get(g.p) || 0) + 1); }));
  X.chacadata.goleadores.forEach(([p, n]) => check(`goles de ${p}`, sc.get(p) ?? 0, n));
}

sec(`Ranking de goleadores (filtro de la planilla: división=${X.filtro_rank.div}, década=${X.filtro_rank.dec}, torneo/temporada=${X.filtro_rank.sd})`);
{
  const o = {}; if (X.filtro_rank.div !== "Todas") o.div = X.filtro_rank.div; if (!isNaN(+X.filtro_rank.dec)) o.dec = +X.filtro_rank.dec;
  const r = topScorers(o), by = new Map(r.map((x) => [x.p.name, x]));
  X.ranking.forEach(([pos, name, g, , , pj, , gl]) => { const x = by.get(name); check(`${name} goles`, x?.g ?? 0, g); });
  // La columna «PJ (con formación)» de la planilla usa APARICIONES!B2:B1000 (solo las primeras 999 de 27.777 filas): da 0 para jugadores de 2020 aunque haya formaciones. No se compara.
}

sec("Partidos jugados por jugador (con formación)");
// las formaciones agregadas desde otras fuentes (marca «lu» en el partido) no están en la planilla: se descuentan para comparar
X.pj_ranking.forEach(([pos, name, pj, tit, ing]) => { const p = S.playerMap.get(name); const base = (p?.apps ?? []).filter((a) => !(a.m.enr || []).includes("lu")); check(`${name} PJ`, base.length, pj); check(`${name} titular`, base.filter((a) => a.rol === 0).length, tit); });

sec(`Efemérides (${X.efem.dia} de ${X.efem.mes})`);
{
  const MES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"];
  const list = onDay(`${String(MES.indexOf(X.efem.mes) + 1).padStart(2, "0")}-${String(Math.round(X.efem.dia)).padStart(2, "0")}`);
  const s = sum(list);
  check("PJ", s.pj, X.efem.res[0]); check("G", s.g, X.efem.res[1]); check("E", s.e, X.efem.res[2]); check("P", s.p, X.efem.res[3]);
  check("años listados", list.map((m) => m.y).join(","), X.efem.lista.map((r) => r[0]).join(","));
}
console.log(`\n${ok} comprobaciones correctas, ${bad} con diferencias.`);
process.exit(bad ? 1 : 0);
