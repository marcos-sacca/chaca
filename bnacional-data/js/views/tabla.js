import { route } from "../app.js";
import { S } from "../store.js";
import { h, n, norm } from "../util.js";
import { head, table, T, href, crest } from "./common.js";
import { extras, regularSets } from "./reducidos.js";

const st = { by: 12, dir: -1, q: "", min: 1, red: false };
// tabla con los partidos fuera de la fase regular sumados (solo para los clubes que jugaban la categoría esa temporada)
function withExtras() {
  const by = new Map(S.general.map((r) => [r[1], r.slice()])), reg = regularSets();
  for (const x of extras()) {
    const w = S.seasons[x.si].ptsw || 3;
    for (const [t, gf, gc] of [[x.a, x.ga, x.gb], [x.b, x.gb, x.ga]]) {
      if (t == null || !reg[x.si].has(t) || !by.has(t)) continue;
      const r = by.get(t);
      r[3]++; r[7] += gf; r[8] += gc; r[9] = r[7] - r[8];
      if (gf > gc) { r[4]++; r[11] += w; r[12] += 3; } else if (gf === gc) { r[5]++; r[11]++; r[12]++; } else r[6]++;
    }
  }
  return [...by.values()];
}
const COLS = [[2, "Temp.", "Temporadas jugadas"], [13, "Asc.", "Ascensos a Primera"], [14, "Desc.", "Descensos: temporadas en que el club salió de la categoría"], [15, "Red.", "Reducidos por el ascenso que jugó"], [3, "PJ", "Partidos jugados"], [4, "PG", "Ganados"], [5, "PE", "Empatados"], [6, "PP", "Perdidos"], [7, "GF", "Goles a favor"], [8, "GC", "Goles en contra"], [9, "DG", "Diferencia de gol"], [11, "Pts", "Puntos según el sistema de cada época"], [12, "Pts (3 x V)", "Puntos con 3 por victoria, para comparar épocas"]];
route("tabla", async () => {
  const page = h("div.wrap.page"), box = h("div");
  const draw = () => {
    const f = norm(st.q);
    const base = st.red ? withExtras() : S.general;
    const rows = base.filter((r) => r[2] >= st.min && (!f || norm(T(r[1]).n).includes(f))).sort((a, b) => (a[st.by] - b[st.by]) * st.dir || b[12] - a[12]);
    const mx = Math.max(...base.map((r) => r[12]));
    box.replaceChildren(table([{ label: "#" }, { label: "Club" }, ...COLS.map(([i, l, t]) => ({ label: h("button.sort" + (st.by === i ? ".is-on" : ""), { type: "button", title: t, "aria-label": `Ordenar por ${t}`, onclick: () => { st.dir = st.by === i ? -st.dir : -1; st.by = i; draw(); } }, [l, st.by === i ? (st.dir < 0 ? " ↓" : " ↑") : ""]), cls: "num" }))],
      rows.map((r, k) => h("tr", [h("td.num", k + 1), h("td.tbl__club", h("a", { href: href.club(r[1]) }, [crest(r[1]), T(r[1]).short])), ...COLS.map(([i]) => i === 12 ? h("td.num.has-bar", [h("i.mini", { style: { width: (r[12] / mx) * 100 + "%" } }), h("b", n(r[12]))]) : h("td.num", i === 9 && r[9] > 0 ? "+" + r[9] : n(r[i])))])), { cls: "tbl--wide" }));
  };
  page.append(head("Tabla histórica", "Todos los clubes, todas las épocas", "Suma de todas las temporadas de fase regular desde 1986/87. La columna «Pts (3 x V)» recalcula todo con 3 puntos por victoria, así se pueden comparar épocas. Si querés, sumá también los reducidos, finales, promociones y desempates."),
    h("div.toolbar", [h("input#tq", { type: "search", placeholder: "Buscar club", "aria-label": "Buscar club", value: st.q, oninput: (e) => { st.q = e.target.value; draw(); } }), h("label.sel", ["Al menos ", h("select#tmin", { onchange: (e) => { st.min = Number(e.target.value); draw(); } }, [1, 5, 10, 20].map((v) => h("option", { value: v, selected: v === st.min }, `${v} ${v === 1 ? "temporada" : "temporadas"}`)))]),
      h("label.tbl__tog", [h("input", { type: "checkbox", checked: st.red, onchange: (e) => { st.red = e.target.checked; draw(); } }), "Incluir reducidos, finales, promociones y desempates"]), h("a.link", { href: "#reducidos" }, "Ver todos esos partidos →")]), box);
  draw();
  return { page, title: "Tabla histórica" };
});
