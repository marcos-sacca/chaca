// clásicos: un rival por club (cargado a mano o, si no hay, el más enfrentado) y armador de cruces propios
import { route } from "../app.js";
import { S } from "../store.js";
import { h, n, norm, fshort } from "../util.js";
import { head, sec, T, crest, href } from "./common.js";
import { h2hMatches, h2hSummary, rivalsOf, hrefH2H } from "./historial.js";

const LS = "bn_cruces_v1";
const getMine = () => { try { return JSON.parse(localStorage.getItem(LS) || "[]"); } catch { return []; } };
const setMine = (L) => { try { localStorage.setItem(LS, JSON.stringify(L)); } catch { /* sin almacenamiento */ } };
const AMBA = new Set(["Buenos Aires", "Ciudad de Buenos Aires"]);
const zone = (ti) => (AMBA.has(S.teams[ti].prov) ? "AMBA" : S.teams[ti].prov);

let cache = null;
function build() {
  if (cache) return cache;
  const man = new Map();
  for (const [a, b, name] of S.clasicos?.pares || []) { const x = S.teamBy.get(a), y = S.teamBy.get(b); if (x != null && y != null) { man.set(x, { b: y, name }); man.set(y, { b: x, name }); } }
  cache = S.teams.map((t, ti) => {
    if (man.has(ti)) return { ti, ...man.get(ti), manual: true };
    const rs = rivalsOf(ti).filter((r) => r.b !== ti).sort((p, q) => q.pj - p.pj);
    const near = rs.find((r) => zone(r.b) === zone(ti)) || rs[0];
    return near ? { ti, b: near.b, name: "", manual: false } : null;
  }).filter(Boolean);
  return cache;
}
export const classicOf = (ti) => build().find((c) => c.ti === ti) || null;

const balance = (a, b) => h2hSummary(a, h2hMatches(a, b));
const line = (a, b) => { const s = balance(a, b); return s.pj ? `${s.pj} partidos · ${s.pg} G · ${s.pe} E · ${s.pp} P · goles ${s.gf}-${s.gc}` : "Nunca se enfrentaron en la base"; };

route("clasicos", async () => {
  const page = h("div.wrap.page"), grid = h("div.cl__grid"), mine = h("div.cl__mine"), out = h("div.cl__out");
  const st = { q: "", only: false };
  const sorted = S.teams.map((t, i) => i).sort((x, y) => T(x).short.localeCompare(T(y).short, "es"));
  const opt = (ph) => [h("option", { value: "" }, ph), ...sorted.map((i) => h("option", { value: S.teams[i].s }, T(i).short))];
  const sa = h("select", { "aria-label": "Primer club" }, opt("Primer club")), sb = h("select", { "aria-label": "Segundo club" }, opt("Segundo club"));
  const pair = () => { const x = S.teamBy.get(sa.value), y = S.teamBy.get(sb.value); return x != null && y != null && x !== y ? [x, y] : null; };

  const drawMine = () => {
    const L = getMine().map(([a, b]) => [S.teamBy.get(a), S.teamBy.get(b)]).filter(([a, b]) => a != null && b != null);
    mine.replaceChildren(...(L.length ? [h("h3", "Mis cruces"), h("div.cl__chips", L.map(([a, b]) => h("span.cl__chip", [h("a", { href: hrefH2H(a, b) }, [crest(a), T(a).short, " vs ", crest(b), T(b).short]), h("button", { type: "button", "aria-label": `Sacar ${T(a).short} vs ${T(b).short}`, onclick: () => { setMine(getMine().filter(([x, y]) => !(x === S.teams[a].s && y === S.teams[b].s))); drawMine(); } }, "×")]))) ] : []));
  };
  const drawOut = () => {
    const p = pair();
    if (!p) { out.replaceChildren(h("p.muted", "Elegí dos clubes para ver cómo les fue cuando se cruzaron.")); return; }
    const [a, b] = p, list = h2hMatches(a, b), s = h2hSummary(a, list), last = list.length ? S.matches[list[list.length - 1]] : null;
    const saved = getMine().some(([x, y]) => x === S.teams[a].s && y === S.teams[b].s);
    out.replaceChildren(h("div.cl__res", [
      h("div.cl__vs", [h("span", [crest(a), h("b", T(a).short)]), h("span.cl__score", s.pj ? `${s.pg} - ${s.pe} - ${s.pp}` : "—"), h("span", [h("b", T(b).short), crest(b)])]),
      h("p.muted", s.pj ? `${s.pj} partidos en la categoría · goles ${s.gf} a ${s.gc} · G - E - P desde ${T(a).short}${last ? ` · último: ${last[4] === a ? last[6] : last[7]}-${last[4] === a ? last[7] : last[6]} (${S.seasons[last[0]].label}, ${fshort(last[3])})` : ""}` : "Nunca se enfrentaron en la base."),
      h("div.cl__act", [h("a.btn", { href: hrefH2H(a, b) }, "Ver historial completo"), h("button.btn.btn--ghost", { type: "button", disabled: saved, onclick: () => { setMine([...getMine(), [S.teams[a].s, S.teams[b].s]]); drawMine(); drawOut(); } }, saved ? "Ya está en mis cruces" : "Guardar en mis cruces")]),
    ]));
  };
  sa.addEventListener("change", drawOut); sb.addEventListener("change", drawOut);

  const draw = () => {
    const f = norm(st.q), L = build().filter((c) => (!st.only || c.manual) && (!f || norm(T(c.ti).n + " " + T(c.b).n).includes(f))).sort((x, y) => T(x.ti).short.localeCompare(T(y.ti).short, "es"));
    grid.replaceChildren(...(L.length ? L.map((c) => h("a.cl__card", { href: hrefH2H(c.ti, c.b) }, [
      h("div.cl__teams", [h("span", [crest(c.ti), h("b", T(c.ti).short)]), h("i", "vs"), h("span", [crest(c.b), h("b", T(c.b).short)])]),
      h("p.cl__tag" + (c.manual ? "" : ".is-auto"), c.manual ? (c.name || "Rival histórico") : "Rival más enfrentado"),
      h("p.cl__stat", line(c.ti, c.b)),
    ])) : [h("p.muted", "Ningún clásico coincide con esa búsqueda.")]));
  };

  page.append(head("Clásicos", "Un rival por club, y los cruces que elijas", "Cada club con su clásico y cómo le fue en la B Nacional. Donde no hay un clásico cargado se muestra el rival que más veces enfrentó, y está marcado así."),
    h("div.cl__build", [h("h3", "Armá tu cruce"), h("div.toolbar", [sa, h("span.muted", "vs"), sb]), out, mine]),
    h("div.toolbar", [h("input#clq", { type: "search", placeholder: "Buscar club", "aria-label": "Buscar club", oninput: (e) => { st.q = e.target.value; draw(); } }), h("label.cl__only", [h("input", { type: "checkbox", onchange: (e) => { st.only = e.target.checked; draw(); } }), " Solo clásicos cargados"]), h("a.link", { href: "#historial" }, "Historiales de cualquier cruce →")]),
    grid);
  drawOut(); drawMine(); draw();
  return { page, title: "Clásicos" };
});
