// juegos: adiviná el jugador, la grilla y el desafío del día (los dos primeros en versión diaria y libre)
import { route } from "../app.js";
import { S } from "../store.js";
import { h, n, norm } from "../util.js";
import { head, T, href, crest } from "./common.js";

// ---------- utilidades ----------
const rng = (a) => () => { a |= 0; a = (a + 0x6d2b79f5) | 0; let t = Math.imul(a ^ (a >>> 15), 1 | a); t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t; return ((t ^ (t >>> 14)) >>> 0) / 4294967296; };
const EPOCH = Date.UTC(2026, 9, 30); // desafío #1: 30/10/2026
const artNow = () => new Date(Date.now() - 3 * 3600e3); // hora de Argentina (UTC-3, sin horario de verano)
const dayNum = () => { const d = artNow(); return Math.floor((Date.UTC(d.getUTCFullYear(), d.getUTCMonth(), d.getUTCDate()) - EPOCH) / 864e5) + 1; };
const untilTomorrow = () => { const d = artNow(), m = 1440 - (d.getUTCHours() * 60 + d.getUTCMinutes()); return `${Math.floor(m / 60)} h ${String(m % 60).padStart(2, "0")} min`; };
const LS = "bn_juegos_v1";
const getLS = () => { try { return JSON.parse(localStorage.getItem(LS) || "{}") || {}; } catch { return {}; } };
const setLS = (k, v) => { const d = getLS(); d[k] = v; try { localStorage.setItem(LS, JSON.stringify(d)); } catch { /* sin almacenamiento: el juego sigue igual */ } };
const pick1 = (arr, r) => arr[Math.floor(r() * arr.length)];
const key = (a, b) => (a < b ? a + "|" + b : b + "|" + a);

// ---------- filtros de la práctica libre: época (10 años) y club favorito ----------
// El desafío del día no los usa: tiene que ser igual para todos.
const ERAS = [["", "Todas las épocas", 0, 9999], ["1986-95", "1986–1995", 1986, 1995], ["1996-05", "1996–2005", 1996, 2005], ["2006-15", "2006–2015", 2006, 2015], ["2016-hoy", "2016–hoy", 2016, 9999]];
const fil = { era: getLS().f_era || "", team: getLS().f_team || "" };
const eraOf = (k = fil.era) => ERAS.find((e) => e[0] === k) || ERAS[0];
const teamIx = () => (fil.team ? S.teamBy.get(fil.team) ?? null : null);
const hasFilter = () => !!fil.era || teamIx() != null;
const yr = (s) => +(S.seasons[s].label.match(/\d{4}/) || [0])[0];
const rowOk = (r) => { const [, , a, b] = eraOf(); return r[0] >= a && r[0] <= b && (teamIx() == null || r[1] === teamIx()); };
const gOf = (o) => (hasFilter() ? o.rows.reduce((s, r) => s + (rowOk(r) ? r[2] : 0), 0) : o.g); // goles dentro del filtro
const scopeText = () => `${teamIx() != null ? "en " + T(teamIx()).short : "en la B Nacional"}${fil.era ? ` (${eraOf()[1]})` : ""}`;
const dailyHint = (base) => h("p.muted.game__left", ["Los filtros de época y de club favorito funcionan en la ", h("a", { href: `#${base}-libre` }, "práctica libre"), ". El desafío del día es igual para todos."]);
// barra de filtros; opts.era / opts.team permiten ocultar el que el juego no puede usar
function filterBar(onChange, opts = {}) {
  const { era = true, team = true } = opts;
  const chips = h("div.chips", ERAS.map(([k, l]) => h("button.chip", { type: "button", "aria-pressed": String(fil.era === k), onclick: () => { fil.era = k; setLS("f_era", k); chips.querySelectorAll(".chip").forEach((x, i) => x.setAttribute("aria-pressed", String(ERAS[i][0] === k))); onChange(); } }, l)));
  const order = S.teams.map((t, i) => i).sort((x, y) => T(x).short.localeCompare(T(y).short, "es"));
  const sel = h("select", { "aria-label": "Mi equipo favorito", onchange: () => { fil.team = sel.value; setLS("f_team", sel.value); onChange(); } }, [h("option", { value: "" }, "Cualquier equipo"), ...order.map((i) => h("option", { value: S.teams[i].s, selected: S.teams[i].s === fil.team }, T(i).short))]);
  return h("div.toolbar.gfil", [era ? chips : null, team ? h("label", ["Mi equipo ", sel]) : null, !era ? h("small.muted", "Las formaciones son desde 2014: la época no se puede filtrar acá.") : null].filter(Boolean));
}

// ---------- datos de jugadores (goleadores) ----------
let P;
function prep() {
  if (P) return P;
  const by = new Map();
  for (const [s, p, t, g] of S.scorers_raw) {
    let o = by.get(p); if (!o) by.set(p, (o = { p, name: S.players[p], g: 0, s0: s, s1: s, teams: new Map(), rows: [] }));
    o.g += g; o.s0 = Math.min(o.s0, s); o.s1 = Math.max(o.s1, s); o.rows.push([yr(s), t, g]);
    let q = o.teams.get(t); if (!q) o.teams.set(t, (q = { t, g: 0, s0: s, s1: s }));
    q.g += g; q.s0 = Math.min(q.s0, s); q.s1 = Math.max(q.s1, s);
  }
  const all = [...by.values()].map((o) => ({ ...o, q: norm(o.name) })).sort((a, b) => a.p - b.p);
  const pair = new Map();
  for (const o of all) { const ts = [...o.teams.keys()]; for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) { const k = key(ts[i], ts[j]); (pair.get(k) || pair.set(k, []).get(k)).push(o.p); } }
  const bySearch = all.slice().sort((a, b) => b.g - a.g);
  P = { all, bySearch, byId: new Map(all.map((o) => [o.p, o])), pair };
  return P;
}

// buscador de jugadores (solo muestra el nombre, para no regalar pistas)
function playerPicker(onPick, placeholder = "Escribí el nombre de un jugador", src = null) {
  const inp = h("input.gpick__in", { type: "search", placeholder, autocomplete: "off", spellcheck: "false", "aria-label": placeholder, "aria-autocomplete": "list" });
  const list = h("ul.gpick__list", { role: "listbox" });
  let res = [], act = 0;
  const draw = () => list.replaceChildren(...res.map((o, i) => h("li", h("button.gpick__o" + (i === act ? ".on" : ""), { type: "button", role: "option", onmousedown: (e) => e.preventDefault(), onclick: () => choose(o) }, o.name))));
  const choose = (o) => { inp.value = ""; res = []; draw(); onPick(o); };
  inp.addEventListener("input", () => {
    const w = norm(inp.value.trim()).split(/\s+/).filter(Boolean); act = 0;
    res = w.join("").length < 2 ? [] : (src || P.bySearch).filter((o) => w.every((x) => o.q.includes(x))).slice(0, 8); draw();
  });
  inp.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { act = Math.min(act + 1, res.length - 1); draw(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { act = Math.max(act - 1, 0); draw(); e.preventDefault(); }
    else if (e.key === "Enter" && res[act]) { choose(res[act]); e.preventDefault(); }
    else if (e.key === "Escape") { res = []; draw(); }
  });
  inp.addEventListener("blur", () => setTimeout(() => { res = []; draw(); }, 120));
  return { el: h("div.gpick", [inp, list]), focus: () => inp.focus({ preventScroll: true }) };
}

function shareBox(text) {
  const msg = h("span.gshare__m", { "aria-live": "polite" });
  const ta = h("textarea.gshare__ta", { readonly: true, rows: text.split("\n").length, hidden: true, "aria-label": "Resultado para copiar" });
  ta.value = text;
  const copy = async () => { try { await navigator.clipboard.writeText(text); msg.textContent = "¡Copiado! Pegalo donde quieras."; } catch { ta.hidden = false; ta.select(); msg.textContent = "Copialo de acá:"; } };
  return h("div.gshare", [h("pre.gshare__pre", text), h("div.gshare__b", [h("button.btn", { type: "button", onclick: copy }, "Copiar resultado"), h("a.btn.btn--ghost", { href: "https://wa.me/?text=" + encodeURIComponent(text), target: "_blank", rel: "noopener" }, "Mandar por WhatsApp")]), msg, ta]);
}
const tabs = (cur) => h("nav.gtabs", { "aria-label": "Juegos" }, [["jugador", "Adiviná el jugador"], ["contrarreloj", "Contrarreloj"], ["grilla", "La grilla"], ["masgoles", "¿Quién hizo más?"]].map(([k, l]) => h("a.chip", { href: "#" + k, "aria-pressed": String(cur === k) }, l)));
const modeSwitch = (base, libre) => h("div.gmode", [h("a" + (libre ? "" : ".on"), { href: "#" + base }, `Desafío del día #${dayNum()}`), h("a" + (libre ? ".on" : ""), { href: `#${base}-libre` }, "Práctica libre")]);

// ---------- 1. Adiviná el jugador: por categorías, todo a la vista, puntos por tiempo ----------
const CATS = [
  { k: "goleadores", l: "Goleadores", e: "⚽", d: "50 goles o más en la B Nacional", src: "g", f: (o) => o.g >= 50 && o.teams.size >= 2 },
  { k: "idolos", l: "Ídolos", e: "🏟️", d: "30 goles o más en un mismo club", src: "g", f: (o) => o.teams.size >= 2 && Math.max(...[...o.teams.values()].map((c) => c.g)) >= 30 },
  { k: "clasicos", l: "Clásicos del ascenso", e: "🧳", d: "hicieron goles en 5 clubes o más", src: "g", f: (o) => o.teams.size >= 5 && o.g >= 25 },
  { k: "arqueros", l: "Arqueros", e: "🧤", d: "titulares en la Primera Nacional desde 2014", src: "t", f: (o) => o.pos === "arquero" && o.clubs.length >= 2 && o.pj >= 60 },
];
const tPoints = (secs) => (secs < 30 ? 5 : secs < 60 ? 3 : 1);
const ptsEmoji = (p) => (p >= 5 ? "🟩" : p >= 3 ? "🟨" : p >= 1 ? "🟧" : "🟥");
const poolOf = (c, filtered = false) => {
  const all = c.src === "g" ? P.all.filter(c.f) : prepCR().all.filter(c.f);
  if (!filtered || !hasFilter()) return all;
  const t = teamIx(); // arqueros: las formaciones son desde 2014, solo se filtra por club
  return all.filter((o) => (c.src === "g" ? gOf(o) > 0 : t == null || o.clubs.some(([x]) => x === t)));
};
const roundFor = (c, rnd, libre = false) => {
  let pool = poolOf(c, libre), relaxed = false;
  if (!pool.length) { pool = poolOf(c); relaxed = true; } // el filtro dejó la categoría vacía: se juega sin filtro y se avisa
  const o = pick1(pool, rnd);
  return { cat: c.k, id: c.src === "g" ? o.p : o.i, t0: null, errs: [], done: false, won: false, secs: 0, pts: 0, relaxed };
};
const jState = { cat: "goleadores", total: 0, played: 0 };
route("jugador", async (r) => {
  prep(); prepCR();
  const libre = r.arg === "libre", N = dayNum(), page = h("div.wrap.page"), box = h("div.game");
  const catOf = (k) => CATS.find((c) => c.k === k);
  let st;
  if (libre) st = { rounds: [roundFor(catOf(jState.cat), Math.random, true)], i: 0 };
  else {
    const sv = getLS().jugador2;
    if (sv && sv.day === N && sv.rounds) st = sv;
    else { const rnd = rng(N * 7919 + 11); st = { day: N, rounds: CATS.filter((c) => poolOf(c).length).map((c) => roundFor(c, rnd)), i: 0 }; }
  }
  const persist = () => { if (!libre) setLS("jugador2", st); };
  let msg = "", timer = null;
  const clock = h("b.cr__clock"), live = h("span.cr__pts");
  const cur = () => st.rounds[st.i];
  const subject = (rd) => { const c = catOf(rd.cat); return c.src === "g" ? P.byId.get(rd.id) : CR.all[rd.id]; };
  const tick = () => {
    if (!clock.isConnected && timer) { clearInterval(timer); timer = null; return; }
    const rd = cur(); if (!rd || rd.done || !rd.t0) return;
    const t = Math.floor((Date.now() - rd.t0) / 1000);
    clock.textContent = mmss(t); live.textContent = `${tPoints(t)} ${tPoints(t) === 1 ? "punto" : "puntos"} en juego`;
  };
  const finish = (rd, won) => {
    rd.done = true; rd.won = won; rd.secs = Math.floor((Date.now() - rd.t0) / 1000); rd.pts = won ? tPoints(rd.secs) : 0;
    if (libre) { jState.total += rd.pts; jState.played++; }
  };
  const guess = (o) => {
    const rd = cur(); if (!rd || rd.done) return;
    const ans = subject(rd), c = catOf(rd.cat);
    const ok = c.src === "g" ? o.p === ans.p || o.q === ans.q : o.q === ans.q;
    if (ok) finish(rd, true);
    else if (!rd.errs.includes(o.name)) { rd.errs.push(o.name); msg = `No es ${o.name}.`; }
    persist(); draw();
  };
  const clubsView = (rd) => {
    const c = catOf(rd.cat), o = subject(rd);
    const items = c.src === "g" ? [...o.teams.values()].sort((a, b) => b.g - a.g).map((x) => [x.t, `${x.g} ${x.g === 1 ? "gol" : "goles"}`]) : o.clubs.map(([t, k]) => [t, `${k} ${k === 1 ? "partido" : "partidos"} de titular`]);
    const total = c.src === "g" ? `${n(o.g)} goles en ${o.teams.size} clubes de la B Nacional` : `${n(o.pj)} partidos de titular en ${o.clubs.length} clubes de la Primera Nacional`;
    return [h("p.muted.game__q", [h("span.pill", `${c.e} ${c.l}`), ` ${total}. ¿Quién es?`]), h("ol.gclues", items.map(([t, txt]) => h("li.gclue", [crest(t), h("span", [h("b", T(t).short), h("small", txt)])])))];
  };
  const draw = () => {
    const rd = cur(), kids = [];
    if (!libre) kids.push(h("div.mg__dots", st.rounds.map((x, i) => h("i" + (x.done ? (x.won ? ".ok" : ".no") : ""), { title: catOf(x.cat).l + (x.done ? `: ${x.pts} pts` : "") }))));
    if (rd && !rd.done) {
      if (!rd.t0) { rd.t0 = Date.now(); persist(); }
      const c = catOf(rd.cat);
      const pk = playerPicker(guess, "Escribí el nombre del jugador", c.src === "g" ? P.bySearch : CR.bySearch);
      kids.push(h("div.cr__bar", [h("span", ["⏱ ", clock]), live]), rd.relaxed ? h("p.muted", "Con ese filtro no queda ningún jugador de esta categoría: te tocó uno de cualquier época o club.") : null, ...clubsView(rd));
      if (rd.errs.length) kids.push(h("ol.gtries", rd.errs.map((e) => h("li.no", e))));
      kids.push(h("div.game__play", [pk.el, h("button.btn.btn--ghost", { type: "button", onclick: () => { finish(rd, false); persist(); draw(); } }, "Me rindo")]), msg ? h("p.game__msg", msg) : null,
        h("p.muted.game__left", "Antes de los 30 segundos: 5 puntos. Hasta el minuto: 3. Después: 1. Los errores no restan."));
      box.replaceChildren(...kids.filter(Boolean)); tick(); if (!timer) timer = setInterval(tick, 1000); pk.focus(); return;
    }
    if (timer) { clearInterval(timer); timer = null; }
    msg = "";
    // resultado de la ronda que terminó
    const last = rd || st.rounds[st.rounds.length - 1], o = subject(last), c = catOf(last.cat);
    kids.push(...clubsView(last), h("div.gres" + (last.won ? ".gres--ok" : ".gres--no"), [h("p.eyebrow", last.won ? `¡Bien! ${mmss(last.secs)} · ${last.pts} ${last.pts === 1 ? "punto" : "puntos"}` : "Esta vez no salió"), h("h2", o.name)]));
    const more = !libre && st.i < st.rounds.length - 1;
    if (libre) {
      kids.push(h("p.muted.game__left", `Llevás ${jState.total} ${jState.total === 1 ? "punto" : "puntos"} en ${jState.played} ${jState.played === 1 ? "jugador" : "jugadores"}.`), h("div.game__again", h("button.btn", { type: "button", onclick: () => { st = { rounds: [roundFor(catOf(jState.cat), Math.random, true)], i: 0 }; draw(); } }, "Otro jugador")));
    } else if (more) {
      kids.push(h("div.game__again", h("button.btn", { type: "button", onclick: () => { st.i++; persist(); draw(); } }, `Siguiente: ${catOf(st.rounds[st.i + 1].cat).l} →`)));
    } else {
      const tot = st.rounds.reduce((a, x) => a + x.pts, 0), max = st.rounds.length * 5;
      kids.push(h("div.gres", [h("p.eyebrow", "Desafío del día"), h("h2", `${tot} de ${max} puntos`)]),
        shareBox(`B Nacional Histórica · Adiviná el jugador #${N}\n${st.rounds.map((x) => `${catOf(x.cat).e}${ptsEmoji(x.pts)}`).join(" ")}\n${tot}/${max} puntos`),
        h("p.muted.game__left", [`Mañana hay otro (en ${untilTomorrow()}). Mientras, `, h("a", { href: "#jugador-libre" }, "seguí practicando"), "."]));
    }
    box.replaceChildren(...kids);
  };
  const catChips = libre ? h("div.chips.gcats", CATS.map((c) => h("button.chip", { type: "button", "aria-pressed": String(jState.cat === c.k), title: c.d, onclick: () => { jState.cat = c.k; st = { rounds: [roundFor(c, Math.random, true)], i: 0 }; msg = ""; page.querySelectorAll(".gcats .chip").forEach((x) => x.setAttribute("aria-pressed", String(x.title === c.d))); draw(); } }, `${c.e} ${c.l}`))) : null;
  page.append(head("Juegos", "Adiviná el jugador", "Te mostramos sus clubes con los goles que hizo en cada uno (en los arqueros, los partidos de titular). Cuanto más rápido lo saques, más puntos."), tabs("jugador"), h("div.gbar", modeSwitch("jugador", libre)), libre ? filterBar(() => { st = { rounds: [roundFor(catOf(jState.cat), Math.random, true)], i: 0 }; msg = ""; draw(); }) : dailyHint("jugador"), catChips, box);
  draw();
  return { page, title: "Adiviná el jugador" };
});

// ---------- 2. La grilla ----------
// jugadores que hicieron goles para cada par de clubes dentro de una época (la clave de época es la de ERAS)
const pairCache = new Map();
function pairsFor(era) {
  if (pairCache.has(era)) return pairCache.get(era);
  const [, , a, b] = eraOf(era), pm = new Map();
  for (const o of P.all) {
    const ts = [...new Set(o.rows.filter((r) => r[0] >= a && r[0] <= b).map((r) => r[1]))].sort((x, y) => x - y);
    for (let i = 0; i < ts.length; i++) for (let j = i + 1; j < ts.length; j++) { const k = key(ts[i], ts[j]); (pm.get(k) || pm.set(k, []).get(k)).push(o.p); }
  }
  pairCache.set(era, pm);
  return pm;
}
const pmOf = (era) => (era ? pairsFor(era) : P.pair);
function makeGrid(rnd, minAns, pm = P.pair, fav = null, minDeg = 60) {
  const deg = new Map();
  for (const [k, L] of pm) for (const t of k.split("|")) deg.set(+t, (deg.get(+t) || 0) + L.length);
  const cand = [...deg.entries()].filter(([, d]) => d >= minDeg).map(([t]) => t).sort((a, b) => a - b);
  const cnt = (a, b) => (pm.get(key(a, b)) || []).length;
  for (let i = 0; i < 4000; i++) {
    const rows = fav != null && cand.includes(fav) ? [fav] : []; while (rows.length < 3) { const t = pick1(cand, rnd); if (!rows.includes(t)) rows.push(t); }
    const ok = cand.filter((c) => !rows.includes(c) && rows.every((a) => cnt(a, c) >= minAns));
    if (ok.length < 3) continue;
    const cols = []; while (cols.length < 3) { const t = pick1(ok, rnd); if (!cols.includes(t)) cols.push(t); }
    return { rows, cols };
  }
  return null;
}
route("grilla", async (r) => {
  prep();
  const libre = r.arg === "libre", N = dayNum(), page = h("div.wrap.page"), box = h("div.game");
  const fresh = (rnd) => {
    const era = libre ? fil.era : "", fav = libre ? teamIx() : null;
    let g = makeGrid(rnd, era ? 2 : 3, pmOf(era), fav, era ? 25 : 60), used = era, note = "";
    if (!g && libre && hasFilter()) { g = makeGrid(rnd, 3); used = ""; note = "Con ese filtro no se pudo armar una grilla: te tocó una de cualquier época."; }
    else if (g && fav != null && !g.rows.includes(fav)) note = `${T(fav).short} no tiene suficientes cruces para armar la grilla: usamos otros clubes.`;
    return { ...g, era: used, note, cells: Array(9).fill(null), left: 9, done: false };
  };
  let st;
  if (libre) st = fresh(Math.random);
  else { const sv = getLS().grilla; st = sv && sv.day === N && sv.rows ? sv : { day: N, ...fresh(rng(N * 104729 + 7)) }; }
  const persist = () => { if (!libre) setLS("grilla", st); };
  let sel = st.cells.indexOf(null), msg = "";
  const ans = (i) => pmOf(st.era).get(key(st.rows[Math.floor(i / 3)], st.cols[i % 3])) || [];

  const guess = (o) => {
    if (st.done || sel < 0) return;
    if (st.cells.includes(o.p)) { msg = `${o.name} ya está en la grilla: cada jugador va una sola vez.`; return draw(); }
    st.left--;
    const a = st.rows[Math.floor(sel / 3)], b = st.cols[sel % 3];
    if (ans(sel).includes(o.p)) { st.cells[sel] = o.p; msg = `¡Sí! ${o.name} convirtió para ${T(a).short} y para ${T(b).short}.`; }
    else msg = `No: ${o.name} no hizo goles para ${T(a).short} y ${T(b).short}.`;
    if (st.left <= 0 || !st.cells.includes(null)) st.done = true;
    sel = st.done ? -1 : st.cells[sel] == null ? sel : st.cells.indexOf(null);
    persist(); draw();
  };
  const draw = () => {
    const filled = st.cells.filter((x) => x != null).length;
    const cell = (i) => {
      const p = st.cells[i], L = ans(i);
      if (p != null) return h("div.gcell.gcell--ok", [h("b", P.byId.get(p).name), h("small", `1 de ${L.length} posibles`)]);
      if (st.done) { const top = L.map((x) => P.byId.get(x)).sort((a, b) => b.g - a.g).slice(0, 2); return h("div.gcell.gcell--miss", [h("small", `${L.length} posibles, como`), h("b", top.map((x) => x.name).join(" o "))]); }
      return h("button.gcell" + (i === sel ? ".on" : ""), { type: "button", "aria-label": `${T(st.rows[Math.floor(i / 3)]).short} y ${T(st.cols[i % 3]).short}`, onclick: () => { sel = i; msg = ""; draw(); } }, h("span", i === sel ? "Elegida" : "+"));
    };
    const hd = (t) => h("div.ghead", [crest(t), h("span", T(t).short)]);
    const grid = h("div.ggrid", [h("div.ghead.ghead--x", h("span", `${st.left} ${st.left === 1 ? "intento" : "intentos"}`)), ...st.cols.map(hd), ...st.rows.flatMap((t, ri) => [hd(t), ...[0, 1, 2].map((ci) => cell(ri * 3 + ci))])]);
    const kids = [h("p.muted.game__q", `Completá cada casilla con un jugador que haya hecho goles en la B Nacional${st.era ? ` (${eraOf(st.era)[1]})` : ""} para el club de la fila y para el de la columna. Tenés 9 intentos y no se repiten jugadores.`), st.note ? h("p.muted", st.note) : null, grid].filter(Boolean);
    if (!st.done) {
      const pk = playerPicker(guess, sel >= 0 ? `¿Quién jugó en ${T(st.rows[Math.floor(sel / 3)]).short} y ${T(st.cols[sel % 3]).short}?` : "Elegí una casilla");
      kids.push(h("div.game__play", [pk.el, h("button.btn.btn--ghost", { type: "button", onclick: () => { st.done = true; persist(); draw(); } }, "Me rindo")]), msg ? h("p.game__msg", msg) : null);
      box.replaceChildren(...kids.filter(Boolean)); if (msg) pk.focus(); return;
    }
    kids.push(h("div.gres" + (filled === 9 ? ".gres--ok" : ""), [h("p.eyebrow", filled === 9 ? "¡Grilla completa!" : "Fin del juego"), h("h2", `${filled} de 9`), msg ? h("p.muted", msg) : null]));
    if (libre) kids.push(h("div.game__again", h("button.btn", { type: "button", onclick: () => { st = fresh(Math.random); sel = 0; msg = ""; draw(); } }, "Otra grilla")));
    else {
      const em = [0, 1, 2].map((r_) => [0, 1, 2].map((c) => (st.cells[r_ * 3 + c] != null ? "🟩" : "⬜")).join("")).join("\n");
      kids.push(shareBox(`B Nacional Histórica · La grilla #${N}\n${em}\n${filled}/9 en ${9 - st.left} intentos`), h("p.muted.game__left", [`Mañana hay otra (en ${untilTomorrow()}). Mientras, `, h("a", { href: "#grilla-libre" }, "jugá una de práctica"), "."]));
    }
    box.replaceChildren(...kids);
  };
  page.append(head("Juegos", "La grilla", "Tres clubes arriba, tres al costado. Buscá al jugador que los une."), tabs("grilla"), h("div.gbar", modeSwitch("grilla", libre)), libre ? filterBar(() => { st = fresh(Math.random); sel = 0; msg = ""; draw(); }) : dailyHint("grilla"), box);
  if (!st.rows) { box.append(h("p", "No se pudo armar la grilla.")); return { page, title: "La grilla" }; }
  draw();
  return { page, title: "La grilla" };
});

// ---------- 3. Contrarreloj: todos los clubes y los partidos de titular, puntos por tiempo ----------
let CR;
function prepCR() {
  if (CR) return CR;
  const all = (S.titulares.p || []).map(([name, clubs, pos], i) => ({ i, name, q: norm(name), clubs, pos: pos || "", pj: clubs.reduce((a, c) => a + c[1], 0) }));
  CR = { all, bySearch: all.slice().sort((a, b) => b.pj - a.pj), pool: all.filter((o) => o.clubs.length >= 3 && o.pj >= 60) };
  return CR;
}
const crPoints = (secs, errs) => Math.max(100, 1000 - 5 * secs - 100 * errs);
const mmss = (t) => `${Math.floor(t / 60)}:${String(t % 60).padStart(2, "0")}`;
route("contrarreloj", async (r) => {
  prepCR();
  const libre = r.arg === "libre", N = dayNum(), page = h("div.wrap.page"), box = h("div.game");
  const head_ = head("Juegos", "Contrarreloj", "Todos los clubes y sus partidos de titular, a la vista. Cuanto más rápido lo saques, más puntos.");
  if (!CR.pool.length) { page.append(head_, tabs("contrarreloj"), h("p.muted", "Faltan los datos de formaciones (data/titulares.json).")); return { page, title: "Contrarreloj" }; }
  const fresh = (rnd) => {
    const t = libre ? teamIx() : null;
    const mine = t == null ? [] : CR.all.filter((o) => o.clubs.some(([x]) => x === t) && o.clubs.length >= 2 && o.pj >= 30);
    const pool = mine.length ? mine : CR.pool;
    return { i: pick1(pool, rnd).i, t0: Date.now(), errs: [], done: false, won: false, secs: 0, pts: 0, note: t != null && !mine.length ? `No hay jugadores de ${T(t).short} con tantas formaciones: te tocó uno de cualquier club.` : "" };
  };
  let st;
  if (libre) st = fresh(Math.random);
  else { const sv = getLS().contrarreloj; st = sv && sv.day === N && CR.all[sv.i] ? sv : { day: N, ...fresh(rng(N * 15485863 + 3)) }; }
  const persist = () => { if (!libre) setLS("contrarreloj", st); };
  persist();
  let msg = "", timer = null;
  const clock = h("b.cr__clock"), live = h("span.cr__pts");
  const tick = () => {
    if (!clock.isConnected && timer) { clearInterval(timer); timer = null; return; }
    const t = Math.floor((Date.now() - st.t0) / 1000);
    clock.textContent = mmss(t); live.textContent = `${crPoints(t, st.errs.length)} pts en juego`;
  };
  const guess = (o) => {
    if (st.done) return;
    const ans = CR.all[st.i];
    if (o.q === ans.q) { st.done = st.won = true; st.secs = Math.floor((Date.now() - st.t0) / 1000); st.pts = crPoints(st.secs, st.errs.length); }
    else if (!st.errs.includes(o.name)) { st.errs.push(o.name); msg = `No es ${o.name}. −100 puntos.`; }
    persist(); draw();
  };
  const draw = () => {
    const o = CR.all[st.i];
    const clubs = h("ol.gclues", o.clubs.map(([t, k]) => h("li.gclue", [crest(t), h("span", [h("b", T(t).short), h("small", `${k} ${k === 1 ? "partido" : "partidos"} de titular`)])])));
    const kids = [h("p.muted.game__q", `Jugó en estos ${o.clubs.length} clubes de la Primera Nacional: ${n(o.pj)} partidos de titular en total. ¿Quién es?`), st.note ? h("p.muted", st.note) : null, clubs].filter(Boolean);
    if (st.errs.length) kids.push(h("ol.gtries", st.errs.map((e) => h("li.no", e))));
    if (!st.done) {
      const pk = playerPicker(guess, "Escribí el nombre del jugador", CR.bySearch);
      kids.splice(1, 0, h("div.cr__bar", [h("span", ["⏱ ", clock]), live]));
      kids.push(h("div.game__play", [pk.el, h("button.btn.btn--ghost", { type: "button", onclick: () => { st.done = true; st.secs = Math.floor((Date.now() - st.t0) / 1000); st.pts = 0; persist(); draw(); } }, "Me rindo")]), msg ? h("p.game__msg", msg) : null,
        h("p.muted.game__left", "Arrancás con 1000 puntos: se pierden 5 por segundo y 100 por cada error. Si lo sacás, te llevás al menos 100."));
      box.replaceChildren(...kids.filter(Boolean)); tick(); if (!timer) timer = setInterval(tick, 1000); pk.focus(); return;
    }
    if (timer) { clearInterval(timer); timer = null; }
    kids.push(h("div.gres" + (st.won ? ".gres--ok" : ".gres--no"), [h("p.eyebrow", st.won ? `¡Lo sacaste en ${mmss(st.secs)}!` : "Esta vez no salió"), h("h2", st.won ? `${st.pts} puntos` : o.name), h("p.muted", st.won ? `Era ${o.name}. ${st.errs.length ? `${st.errs.length} ${st.errs.length === 1 ? "error" : "errores"}.` : "Sin errores."}` : "0 puntos.")]));
    if (libre) kids.push(h("div.game__again", h("button.btn", { type: "button", onclick: () => { st = fresh(Math.random); msg = ""; draw(); } }, "Otro jugador")));
    else {
      kids.push(shareBox(`B Nacional Histórica · Contrarreloj #${N}\n${st.won ? `⏱ ${mmss(st.secs)} · ${st.errs.length ? "🟥".repeat(st.errs.length) : "sin errores"}\n${st.pts} puntos` : "No lo saqué"}`), h("p.muted.game__left", [`Mañana hay otro (en ${untilTomorrow()}). Mientras, `, h("a", { href: "#contrarreloj-libre" }, "seguí practicando"), "."]));
    }
    box.replaceChildren(...kids);
  };
  page.append(head_, tabs("contrarreloj"), h("div.gbar", modeSwitch("contrarreloj", libre)), libre ? filterBar(() => { st = fresh(Math.random); msg = ""; draw(); }, { era: false }) : dailyHint("contrarreloj"), box);
  draw();
  return { page, title: "Contrarreloj" };
});

// ---------- 4. ¿Quién hizo más goles? ----------
const MG_ROUNDS = 10;
// f = true: se comparan los goles dentro del filtro (época / club); null si no alcanzan los goleadores para armar cruces
function mgPairs(rnd, k, f = false) {
  const val = (o) => (f ? gOf(o) : o.g), pool = P.all.filter((o) => val(o) >= (f ? 3 : 15));
  const out = [];
  for (let i = 0; i < 3000 && out.length < k; i++) {
    const a = pick1(pool, rnd), b = pick1(pool, rnd);
    if (!a || !b || a.p === b.p || val(a) === val(b) || Math.abs(val(a) - val(b)) > Math.max(val(a), val(b)) * 0.6) continue; // parejos, pero no iguales
    out.push([a.p, b.p]);
  }
  return out.length === k ? out : null;
}
const mgState = { best: (getLS().masgoles_best || 0) };
route("masgoles", async (r) => {
  prep();
  const libre = r.arg === "libre", N = dayNum(), page = h("div.wrap.page"), box = h("div.game");
  const fresh = (rnd) => {
    const k = libre ? 1 : MG_ROUNDS, f = libre && hasFilter();
    let pairs = f ? mgPairs(rnd, k, true) : null, used = !!pairs;
    if (!pairs) pairs = mgPairs(rnd, k);
    return { pairs, res: [], done: false, f: used, note: f && !used ? "Con ese filtro no hay suficientes goleadores para armar cruces: te tocaron de toda la historia." : "" };
  };
  const val = (o) => (st.f ? gOf(o) : o.g);
  let st;
  if (libre) st = fresh(Math.random);
  else { const sv = getLS().masgoles; st = sv && sv.day === N && sv.pairs ? sv : { day: N, ...fresh(rng(N * 32452843 + 5)) }; }
  const persist = () => { if (!libre) setLS("masgoles", st); };
  let reveal = null; // [elegido, acierto] mientras se muestra el resultado de la ronda
  const choose = (pid) => {
    if (st.done || reveal) return;
    const [a, b] = st.pairs[st.res.length], A = P.byId.get(a), B = P.byId.get(b), win = val(A) > val(B) ? a : b, ok = pid === win;
    reveal = [pid, ok]; draw();
    setTimeout(() => {
      reveal = null; st.res.push(ok);
      if (libre) {
        const nx = ok ? mgPairs(Math.random, 1, st.f) : null; // sin cruces nuevos con el filtro, la racha termina
        if (nx) st.pairs.push(...nx);
        else { st.done = true; const sc = ok ? st.res.length : st.res.length - 1; if (!st.f && sc > mgState.best) { mgState.best = sc; setLS("masgoles_best", sc); } }
      }
      else if (st.res.length >= MG_ROUNDS) st.done = true;
      persist(); draw();
    }, 1400);
  };
  const card = (pid, show) => {
    const o = P.byId.get(pid), clubs = [...o.teams.values()].sort((x, y) => y.g - x.g).slice(0, 3);
    const cls = !reveal ? "" : pid === reveal[0] ? (reveal[1] ? ".is-ok" : ".is-no") : "";
    return h("button.mgcard" + cls, { type: "button", disabled: !!reveal, onclick: () => choose(pid) }, [
      h("b.mgcard__n", o.name), h("span.mgcard__c", clubs.map((c) => h("span.mgclub", [crest(c.t), T(c.t).short]))),
      h("span.mgcard__g", show ? [h("b", n(val(o))), " goles"] : "¿?"),
    ]);
  };
  const draw = () => {
    const kids = [];
    const score = st.res.filter(Boolean).length;
    if (!st.done) {
      const [a, b] = st.pairs[st.res.length];
      kids.push(h("p.muted.game__q", libre ? `Racha: ${st.res.length} · Mejor racha: ${mgState.best}` : `Ronda ${st.res.length + 1} de ${MG_ROUNDS} · ${score} ${score === 1 ? "acierto" : "aciertos"}`),
        st.note ? h("p.muted", st.note) : null, h("p.mg__q", `¿Quién hizo más goles ${st.f ? scopeText() : "en la B Nacional"}?`), h("div.mg", [card(a, !!reveal), h("span.mg__vs", "vs"), card(b, !!reveal)]),
        h("div.mg__dots", st.res.map((x) => h("i" + (x ? ".ok" : ".no"))).concat(libre ? [] : Array(MG_ROUNDS - st.res.length).fill(0).map(() => h("i")))));
      box.replaceChildren(...kids.filter(Boolean)); return;
    }
    if (libre) {
      const sc = st.res.filter(Boolean).length; // con filtro la racha puede cortarse porque se acaban los cruces, no por un error
      kids.push(h("div.gres" + (sc > 0 ? ".gres--ok" : ".gres--no"), [h("p.eyebrow", st.res[st.res.length - 1] ? "No quedan más cruces con ese filtro" : "Se cortó la racha"), h("h2", `${sc} seguidas`), h("p.muted", st.f ? "Con filtro no se guarda el récord." : `Tu mejor racha: ${mgState.best}.`)]), h("div.game__again", h("button.btn", { type: "button", onclick: () => { st = fresh(Math.random); draw(); } }, "Jugar de nuevo")));
    } else {
      kids.push(h("div.gres" + (score >= 7 ? ".gres--ok" : ""), [h("p.eyebrow", score >= 9 ? "¡Enciclopedia del ascenso!" : score >= 7 ? "Muy bien" : score >= 5 ? "Zafaste" : "A repasar la tabla de goleadores"), h("h2", `${score} de ${MG_ROUNDS}`)]),
        h("ol.mg__list", st.pairs.map(([a, b], i) => { const A = P.byId.get(a), B = P.byId.get(b); return h("li", [h("span" + (st.res[i] ? ".ok" : ".no"), st.res[i] ? "✓" : "✗"), ` ${A.name} (${A.g}) vs ${B.name} (${B.g})`]); })),
        shareBox(`B Nacional Histórica · ¿Quién hizo más? #${N}\n${st.res.map((x) => (x ? "🟩" : "🟥")).join("")}\n${score}/${MG_ROUNDS}`), h("p.muted.game__left", [`Mañana hay otro (en ${untilTomorrow()}). Mientras, `, h("a", { href: "#masgoles-libre" }, "probá la racha infinita"), "."]));
    }
    box.replaceChildren(...kids);
  };
  page.append(head("Juegos", "¿Quién hizo más goles?", "Dos goleadores de la categoría, uno contra otro. Elegí el que hizo más goles en la B Nacional."), tabs("masgoles"), h("div.gbar", modeSwitch("masgoles", libre)), libre ? filterBar(() => { st = fresh(Math.random); reveal = null; draw(); }) : dailyHint("masgoles"), box);
  draw();
  return { page, title: "¿Quién hizo más goles?" };
});

// ---------- portada de juegos ----------
route("juegos", async () => {
  prep();
  const N = dayNum(), d = getLS();
  const done = (k) => (k === "jugador" ? d.jugador2 && d.jugador2.day === N && d.jugador2.rounds.every((x) => x.done) : d[k] && d[k].day === N && d[k].done);
  const card = (k, t, txt) => h("a.gcard", { href: "#" + k }, [h("p.eyebrow", done(k) ? "Ya jugaste el de hoy ✓" : `Desafío del día #${N}`), h("h2", t), h("p", txt), h("span.link", done(k) ? "Ver resultado →" : "Jugar →")]);
  const page = h("div.wrap.page", [head("Juegos", "¿Cuánto sabés de la B Nacional?", "Un desafío nuevo por día, igual para todos, para compartir con amigos. Y práctica libre para cuando quieras."),
    h("div.gcards", [card("jugador", "Adiviná el jugador", "Goleadores, ídolos, clásicos del ascenso y arqueros: sus clubes y sus goles a la vista. 5 puntos si lo sacás en menos de 30 segundos."), card("contrarreloj", "Contrarreloj", "Todos sus clubes y partidos de titular a la vista. Corre el reloj: cuanto más rápido, más puntos."), card("grilla", "La grilla", "Nueve casillas, nueve cruces de clubes. Encontrá al jugador que hizo goles para los dos."), card("masgoles", "¿Quién hizo más?", "Dos goleadores, uno contra otro. Diez rondas por día, o racha infinita.")]),
    h("p.muted.game__left", `Los datos salen de los goleadores de cada partido desde 1986/87 (solo aparecen jugadores que convirtieron en la categoría) y, en el contrarreloj, de las formaciones confirmadas de Solo Ascenso desde 2014. El desafío cambia a la medianoche (hora argentina).`)]);
  return { page, title: "Juegos" };
});
