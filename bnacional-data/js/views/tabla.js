import { route } from "../app.js";
import { S } from "../store.js";
import { h, n, norm } from "../util.js";
import { head, table, T, href } from "./common.js";

const st = { by: 12, dir: -1, q: "", min: 1 };
const COLS = [[2, "Temp.", "Temporadas jugadas"], [3, "PJ", "Partidos jugados"], [4, "PG", "Ganados"], [5, "PE", "Empatados"], [6, "PP", "Perdidos"], [7, "GF", "Goles a favor"], [8, "GC", "Goles en contra"], [9, "DG", "Diferencia de gol"], [11, "Pts", "Puntos según el sistema de cada época"], [12, "Pts (3 x V)", "Puntos con 3 por victoria, para comparar épocas"]];
route("tabla", async () => {
  const page = h("div.wrap.page"), box = h("div");
  const draw = () => {
    const f = norm(st.q);
    const rows = S.general.filter((r) => r[2] >= st.min && (!f || norm(T(r[1]).n).includes(f))).sort((a, b) => (a[st.by] - b[st.by]) * st.dir || b[12] - a[12]);
    const mx = Math.max(...S.general.map((r) => r[12]));
    box.replaceChildren(table([{ label: "#" }, { label: "Club" }, ...COLS.map(([i, l, t]) => ({ label: h("button.sort" + (st.by === i ? ".is-on" : ""), { type: "button", title: t, "aria-label": `Ordenar por ${t}`, onclick: () => { st.dir = st.by === i ? -st.dir : -1; st.by = i; draw(); } }, [l, st.by === i ? (st.dir < 0 ? " ↓" : " ↑") : ""]), cls: "num" }))],
      rows.map((r, k) => h("tr", [h("td.num", k + 1), h("td", h("a", { href: href.club(r[1]) }, T(r[1]).short)), ...COLS.map(([i]) => i === 12 ? h("td.num.has-bar", [h("i.mini", { style: { width: (r[12] / mx) * 100 + "%" } }), h("b", n(r[12]))]) : h("td.num", i === 9 && r[9] > 0 ? "+" + r[9] : n(r[i])))])), { cls: "tbl--wide" }));
  };
  page.append(head("Tabla histórica", "Todos los clubes, todas las épocas", "Suma de todas las temporadas de fase regular desde 1986/87. La columna «Pts (3 x V)» recalcula todo con 3 puntos por victoria, así se pueden comparar épocas."),
    h("div.toolbar", [h("input#tq", { type: "search", placeholder: "Buscar club", "aria-label": "Buscar club", value: st.q, oninput: (e) => { st.q = e.target.value; draw(); } }), h("label.sel", ["Al menos ", h("select#tmin", { onchange: (e) => { st.min = Number(e.target.value); draw(); } }, [1, 5, 10, 20].map((v) => h("option", { value: v, selected: v === st.min }, `${v} ${v === 1 ? "temporada" : "temporadas"}`)))])]), box);
  draw();
  return { page, title: "Tabla histórica" };
});
