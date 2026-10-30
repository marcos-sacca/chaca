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

// ---------- datos de jugadores (goleadores) ----------
let P;
function prep() {
  if (P) return P;
  const by = new Map();
  for (const [s, p, t, g] of S.scorers_raw) {
    let o = by.get(p); if (!o) by.set(p, (o = { p, name: S.players[p], g: 0, s0: s, s1: s, teams: new Map() }));
    o.g += g; o.s0 = Math.min(o.s0, s); o.s1 = Math.max(o.s1, s);
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
function playerPicker(onPick, placeholder = "Escribí el nombre de un jugador") {
  const inp = h("input.gpick__in", { type: "search", placeholder, autocomplete: "off", spellcheck: "false", "aria-label": placeholder, "aria-autocomplete": "list" });
  const list = h("ul.gpick__list", { role: "listbox" });
  let res = [], act = 0;
  const draw = () => list.replaceChildren(...res.map((o, i) => h("li", h("button.gpick__o" + (i === act ? ".on" : ""), { type: "button", role: "option", onmousedown: (e) => e.preventDefault(), onclick: () => choose(o) }, o.name))));
  const choose = (o) => { inp.value = ""; res = []; draw(); onPick(o); };
  inp.addEventListener("input", () => {
    const w = norm(inp.value.trim()).split(/\s+/).filter(Boolean); act = 0;
    res = w.join("").length < 2 ? [] : P.bySearch.filter((o) => w.every((x) => o.q.includes(x))).slice(0, 8); draw();
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
const tabs = (cur) => h("nav.gtabs", { "aria-label": "Juegos" }, [["jugador", "Adiviná el jugador"], ["grilla", "La grilla"]].map(([k, l]) => h("a.chip", { href: "#" + k, "aria-pressed": String(cur === k) }, l)));
const modeSwitch = (base, libre) => h("div.gmode", [h("a" + (libre ? "" : ".on"), { href: "#" + base }, `Desafío del día #${dayNum()}`), h("a" + (libre ? ".on" : ""), { href: `#${base}-libre` }, "Práctica libre")]);

// ---------- 1. Adiviná el jugador ----------
const MAXC = 6;
const POOLS = { facil: { l: "Fácil", f: (o) => o.teams.size >= 3 && o.g >= 40 }, normal: { l: "Normal", f: (o) => o.teams.size >= 3 && o.g >= 20 }, dificil: { l: "Difícil", f: (o) => o.teams.size >= 2 && o.g >= 8 } };
const DAILY = (o) => o.teams.size >= 3 && o.g >= 25;
function cluesFor(o) {
  const tl = [...o.teams.values()].sort((a, b) => b.g - a.g).slice(0, MAXC).sort((a, b) => a.g - b.g || a.s0 - b.s0); // el club donde más gritó, al final
  const extra = o.teams.size - tl.length;
  const ini = o.name.replace(/\./g, "").split(/\s+/).map((w) => w[0].toUpperCase() + ".").join(" ");
  return [...tl.map((c) => ({ k: "club", t: c.t })),
    { k: "txt", l: "Época", v: `de ${S.seasons[o.s0].label} a ${S.seasons[o.s1].label}` },
    { k: "txt", l: "Goles en la categoría", v: n(o.g) + (extra ? ` · y convirtió en ${extra} ${extra === 1 ? "club" : "clubes"} más` : "") },
    { k: "txt", l: "Iniciales", v: ini }];
}
const jState = { lvl: "normal" };
route("jugador", async (r) => {
  prep();
  const libre = r.arg === "libre", N = dayNum(), page = h("div.wrap.page"), box = h("div.game");
  const fresh = (pool, rnd) => ({ pid: pick1(pool, rnd).p, shown: 1, guesses: [], done: false, won: false });
  let st;
  if (libre) st = fresh(P.all.filter(POOLS[jState.lvl].f), Math.random);
  else { const sv = getLS().jugador; st = sv && sv.day === N && P.byId.has(sv.pid) ? sv : { day: N, ...fresh(P.all.filter(DAILY), rng(N * 7919 + 11)) }; }
  const persist = () => { if (!libre) setLS("jugador", st); };
  let msg = "";

  const guess = (o) => {
    if (st.done) return;
    const cl = cluesFor(P.byId.get(st.pid));
    if (o && st.guesses.includes(o.p)) { msg = `Ya probaste con ${o.name}.`; return draw(); }
    st.guesses.push(o ? o.p : null); msg = "";
    if (o && o.p === st.pid) { st.done = st.won = true; }
    else if (st.shown >= cl.length) st.done = true;
    else { st.shown++; msg = o ? `No es ${o.name}. Ahí va otra pista.` : "Ahí va otra pista."; }
    persist(); draw();
  };
  const draw = () => {
    const o = P.byId.get(st.pid), cl = cluesFor(o), shown = st.done ? cl.length : st.shown;
    const clue = (c, i) => i >= shown ? h("li.gclue.gclue--off", [h("span.gclue__i", i + 1), h("span", "Pista bloqueada")])
      : c.k === "club" ? h("li.gclue", [h("span.gclue__i", i + 1), crest(c.t), h("b", T(c.t).short)])
      : h("li.gclue.gclue--t", [h("span.gclue__i", i + 1), h("span", [h("small", c.l), h("b", c.v)])]);
    const tries = st.guesses.length ? h("ol.gtries", st.guesses.map((g) => h("li" + (g === st.pid ? ".ok" : g == null ? ".skip" : ".no"), g == null ? "Pasé" : P.byId.get(g).name))) : null;
    const kids = [h("p.muted.game__q", "Hizo goles en la B Nacional para estos clubes. ¿Quién es?"), h("ol.gclues", cl.map(clue)), tries];
    if (!st.done) {
      const pk = playerPicker(guess);
      kids.push(h("div.game__play", [pk.el, h("button.btn.btn--ghost", { type: "button", onclick: () => guess(null) }, "Pasar y ver otra pista")]), msg ? h("p.game__msg", msg) : null, h("p.muted.game__left", `Pista ${shown} de ${cl.length}. Cada error suma una pista.`));
      box.replaceChildren(...kids.filter(Boolean)); if (st.guesses.length) pk.focus(); return;
    }
    const career = [...o.teams.values()].sort((a, b) => a.s0 - b.s0);
    kids.push(h("div.gres" + (st.won ? ".gres--ok" : ".gres--no"), [
      h("p.eyebrow", st.won ? `¡Bien! Lo sacaste con ${st.shown} ${st.shown === 1 ? "pista" : "pistas"}` : "Esta vez no salió"),
      h("h2", o.name), h("p.muted", `${n(o.g)} goles en la categoría, de ${S.seasons[o.s0].label} a ${S.seasons[o.s1].label}.`),
      h("ul.gcareer", career.map((c) => h("li", [crest(c.t), h("a", { href: href.club(c.t) }, T(c.t).short), h("small", `${c.s0 === c.s1 ? S.seasons[c.s0].label : S.seasons[c.s0].label + " a " + S.seasons[c.s1].label} · ${c.g} ${c.g === 1 ? "gol" : "goles"}`)]))),
    ]));
    if (libre) kids.push(h("div.game__again", [h("button.btn", { type: "button", onclick: () => { st = fresh(P.all.filter(POOLS[jState.lvl].f), Math.random); msg = ""; draw(); } }, "Otro jugador")]));
    else {
      const em = st.guesses.map((g) => (g === st.pid ? "🟩" : g == null ? "⬜" : "🟥")).join("");
      kids.push(shareBox(`B Nacional Histórica · Adiviná el jugador #${N}\n${em}\n${st.won ? `Lo saqué con ${st.shown} de ${cl.length} pistas` : "No lo saqué"}`), h("p.muted.game__left", [`Mañana hay otro (en ${untilTomorrow()}). Mientras, `, h("a", { href: "#jugador-libre" }, "seguí practicando"), "."]));
    }
    box.replaceChildren(...kids);
  };
  const lvl = libre ? h("label.sel", ["Dificultad ", h("select", { onchange: (e) => { jState.lvl = e.target.value; st = fresh(P.all.filter(POOLS[jState.lvl].f), Math.random); msg = ""; draw(); } }, Object.entries(POOLS).map(([k, v]) => h("option", { value: k, selected: k === jState.lvl }, v.l)))]) : null;
  page.append(head("Juegos", "Adiviná el jugador", "Te mostramos los clubes para los que hizo goles en la categoría, de a uno. Cuantas menos pistas necesites, mejor."), tabs("jugador"), h("div.gbar", [modeSwitch("jugador", libre), lvl]), box);
  draw();
  return { page, title: "Adiviná el jugador" };
});

// ---------- 2. La grilla ----------
function makeGrid(rnd, minAns) {
  const deg = new Map();
  for (const [k, L] of P.pair) for (const t of k.split("|")) deg.set(+t, (deg.get(+t) || 0) + L.length);
  const cand = [...deg.entries()].filter(([, d]) => d >= 60).map(([t]) => t).sort((a, b) => a - b);
  const cnt = (a, b) => (P.pair.get(key(a, b)) || []).length;
  for (let i = 0; i < 4000; i++) {
    const rows = []; while (rows.length < 3) { const t = pick1(cand, rnd); if (!rows.includes(t)) rows.push(t); }
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
  const fresh = (rnd) => ({ ...makeGrid(rnd, 3), cells: Array(9).fill(null), left: 9, done: false });
  let st;
  if (libre) st = fresh(Math.random);
  else { const sv = getLS().grilla; st = sv && sv.day === N && sv.rows ? sv : { day: N, ...fresh(rng(N * 104729 + 7)) }; }
  const persist = () => { if (!libre) setLS("grilla", st); };
  let sel = st.cells.indexOf(null), msg = "";
  const ans = (i) => P.pair.get(key(st.rows[Math.floor(i / 3)], st.cols[i % 3])) || [];

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
    const kids = [h("p.muted.game__q", "Completá cada casilla con un jugador que haya hecho goles en la B Nacional para el club de la fila y para el de la columna. Tenés 9 intentos y no se repiten jugadores."), grid];
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
  page.append(head("Juegos", "La grilla", "Tres clubes arriba, tres al costado. Buscá al jugador que los une."), tabs("grilla"), h("div.gbar", modeSwitch("grilla", libre)), box);
  if (!st.rows) { box.append(h("p", "No se pudo armar la grilla.")); return { page, title: "La grilla" }; }
  draw();
  return { page, title: "La grilla" };
});

// ---------- portada de juegos ----------
route("juegos", async () => {
  prep();
  const N = dayNum(), d = getLS();
  const done = (k) => d[k] && d[k].day === N && d[k].done;
  const card = (k, t, txt) => h("a.gcard", { href: "#" + k }, [h("p.eyebrow", done(k) ? "Ya jugaste el de hoy ✓" : `Desafío del día #${N}`), h("h2", t), h("p", txt), h("span.link", done(k) ? "Ver resultado →" : "Jugar →")]);
  const page = h("div.wrap.page", [head("Juegos", "¿Cuánto sabés de la B Nacional?", "Un desafío nuevo por día, igual para todos, para compartir con amigos. Y práctica libre para cuando quieras."),
    h("div.gcards", [card("jugador", "Adiviná el jugador", "Te damos los clubes para los que hizo goles, de a uno. ¿Con cuántas pistas lo sacás?"), card("grilla", "La grilla", "Nueve casillas, nueve cruces de clubes. Encontrá al jugador que hizo goles para los dos.")]),
    h("p.muted.game__left", `Los datos salen de los goleadores de cada partido desde 1986/87: solo aparecen jugadores que convirtieron en la categoría. El desafío cambia a la medianoche (hora argentina).`)]);
  return { page, title: "Juegos" };
});
