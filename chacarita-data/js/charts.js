// Gráficos en SVG/HTML a mano. Reglas: marcas finas, extremos de 4px redondeados y apoyados en la base,
// 2px de separación entre segmentos, grilla de 1px apenas visible, leyenda siempre, el texto nunca lleva el color del dato.
import { h, svg, n, pct, tip, resLabel } from "./util.js";

const COL = { G: "var(--win)", E: "var(--draw)", P: "var(--loss)" };

/** Barra apilada G/E/P en HTML (segmentos con 2px de aire). */
export function stackBar(s, { tall = false } = {}) {
  const tot = s.pj || 1;
  const bar = h("div.sb", { style: tall ? { height: "20px" } : null, role: "img", "aria-label": `${s.g} ganados, ${s.e} empatados, ${s.p} perdidos` });
  for (const [k, v] of [["G", s.g], ["E", s.e], ["P", s.p]]) {
    if (!v) continue;
    const seg = h(`i.${k}`, { style: { width: (v / tot) * 100 + "%" } });
    tip(seg, () => [h("b", `${n(v)} ${({ G: "ganados", E: "empatados", P: "perdidos" })[k]}`), h("small", pct(v / tot, 1) + " de " + n(s.pj))]);
    bar.append(seg);
  }
  return bar;
}

export const legendGEP = () => h("div.legend", [["G", "Ganó"], ["E", "Empató"], ["P", "Perdió"]].map(([k, t]) => h("span", [h("i", { style: { background: COL[k] } }), t])));

/** Ranking en barras horizontales. items: [{label, value, href?, sub?}] */
export function hbars(items, { max, fmt = n, limit = 12, onclick } = {}) {
  const top = Math.max(max ?? 0, ...items.map((i) => i.value), 1);
  const box = h("div.bars");
  items.slice(0, limit).forEach((it, i) => {
    const name = it.href ? h("a", { href: it.href }, it.label) : h("span.name", it.label);
    box.append(h("div.bar", { style: { "--i": i } }, [
      h("span.bar__i", String(i + 1)), name,
      h("div.bar__t", [h("i", { style: { width: (it.value / top) * 100 + "%" } })]),
      h("span.bar__v", fmt(it.value)),
    ]));
  });
  return box;
}

/** Columnas apiladas por año/temporada: G/E/P. data: [{x, G, E, P, href?}]. */
export function stackedColumns(data, { height = 260, label = (d) => d.x, every = 5, onpick } = {}) {
  const W = 1000, H = height, m = { l: 34, r: 8, t: 10, b: 28 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const mx = Math.max(...data.map((d) => d.G + d.E + d.P), 1);
  const niceMax = Math.ceil(mx / 10) * 10 || 10;
  const bw = Math.min(22, iw / data.length - 3), step = iw / data.length;
  const root = svg("svg", { class: "chart", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Partidos por temporada: ganados, empatados y perdidos" });
  for (let v = 0; v <= niceMax; v += niceMax / 4) {
    const y = m.t + ih - (v / niceMax) * ih;
    root.append(svg("line", { class: v ? "grid-l" : "axis-l", x1: m.l, x2: W - m.r, y1: y, y2: y }), svg("text", { x: m.l - 6, y: y + 4, "text-anchor": "end" }, Math.round(v)));
  }
  data.forEach((d, i) => {
    const x = m.l + i * step + (step - bw) / 2;
    let y = m.t + ih;
    const g = svg("g", { class: "col", tabindex: 0, role: "img", "aria-label": `${label(d)}: ${d.G} ganados, ${d.E} empatados, ${d.P} perdidos` });
    for (const k of ["G", "E", "P"]) {
      const v = d[k]; if (!v) continue;
      const hh = (v / niceMax) * ih, r = Math.min(4, hh / 2);
      const top = k === "P" || (k === "E" && !d.P) || (k === "G" && !d.E && !d.P);
      y -= hh;
      const seg = svg("path", { d: top ? `M${x},${y + hh} V${y + r} Q${x},${y} ${x + r},${y} H${x + bw - r} Q${x + bw},${y} ${x + bw},${y + r} V${y + hh} Z` : `M${x},${y} h${bw} v${hh} h${-bw} Z`, fill: COL[k] });
      seg.setAttribute("transform", "translate(0 0)");
      g.append(seg); y -= 1; // 2px de aire entre segmentos
    }
    g.append(svg("rect", { class: "hit", x: m.l + i * step, y: m.t, width: step, height: ih }));
    tip(g, () => [h("b", label(d)), h("small", `${d.G + d.E + d.P} partidos`), ...["G", "E", "P"].map((k) => h("div", [h("span.k", { style: { background: COL[k] } }), `${resLabel[k]} ${d[k]}`]))]);
    if (onpick) { g.style.cursor = "pointer"; g.addEventListener("click", () => onpick(d)); g.addEventListener("keydown", (e) => e.key === "Enter" && onpick(d)); }
    root.append(g);
    if (i % every === 0 || i === data.length - 1) root.append(svg("text", { x: x + bw / 2, y: H - 8, "text-anchor": "middle" }, String(d.x)));
  });
  return root;
}

/** Línea de tiempo de divisiones: un punto por temporada, nivel 1 arriba. */
export function divisionTimeline(items, { height = 170, onpick } = {}) {
  const W = 1000, H = height, m = { l: 86, r: 14, t: 12, b: 30 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b;
  const rows = ["Primera División", "Segunda División", "Tercera División"];
  const ys = (div) => m.t + (rows.indexOf(div) + .5) * (ih / rows.length);
  const y0 = items[0].y, y1 = items[items.length - 1].y;
  const xs = (y) => m.l + ((y - y0) / (y1 - y0 || 1)) * iw;
  const root = svg("svg", { class: "chart", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "División en la que jugó Chacarita en cada temporada" });
  rows.forEach((r, i) => {
    const y = m.t + i * (ih / rows.length);
    root.append(svg("line", { class: "grid-l", x1: m.l, x2: W - m.r, y1: y + ih / rows.length, y2: y + ih / rows.length }), svg("text", { x: m.l - 10, y: ys(r) + 4, "text-anchor": "end" }, r.split(" ")[0]));
  });
  const path = items.map((it, i) => `${i ? "L" : "M"}${xs(it.y).toFixed(1)},${ys(it.div).toFixed(1)}`).join(" ");
  root.append(svg("path", { d: path, fill: "none", stroke: "var(--ink)", "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round", opacity: .85 }));
  items.forEach((it) => {
    const c = svg("circle", { cx: xs(it.y), cy: ys(it.div), r: 4.5, fill: it.div === "Primera División" ? "var(--red)" : "var(--ink)", stroke: "var(--paper)", "stroke-width": 2, tabindex: 0, class: "pt" });
    c.style.cursor = "pointer";
    tip(c, () => [h("b", it.sd), h("small", it.div + (it.pos ? ` · ${it.pos}` : ""))]);
    if (onpick) { c.addEventListener("click", () => onpick(it)); c.addEventListener("keydown", (e) => e.key === "Enter" && onpick(it)); }
    root.append(c);
  });
  for (let y = Math.ceil(y0 / 10) * 10; y <= y1; y += 10) root.append(svg("text", { x: xs(y), y: H - 8, "text-anchor": "middle" }, String(y)));
  return root;
}

/** Mini barras por año de goles (perfil de jugador). */
export function miniColumns(data, { height = 150 } = {}) {
  const W = 700, H = height, m = { l: 26, r: 4, t: 8, b: 24 };
  const iw = W - m.l - m.r, ih = H - m.t - m.b, mx = Math.max(...data.map((d) => d.v), 1);
  const step = iw / data.length, bw = Math.min(22, step - 4);
  const root = svg("svg", { class: "chart", viewBox: `0 0 ${W} ${H}`, role: "img", "aria-label": "Goles por año" });
  root.append(svg("line", { class: "axis-l", x1: m.l, x2: W - m.r, y1: m.t + ih, y2: m.t + ih }));
  data.forEach((d, i) => {
    const x = m.l + i * step + (step - bw) / 2, hh = (d.v / mx) * ih, y = m.t + ih - hh, r = Math.min(4, hh / 2);
    const g = svg("g", { class: "col", tabindex: 0, "aria-label": `${d.x}: ${d.v}` });
    g.append(svg("path", { d: `M${x},${m.t + ih} V${y + r} Q${x},${y} ${x + r},${y} H${x + bw - r} Q${x + bw},${y} ${x + bw},${y + r} V${m.t + ih} Z`, fill: "var(--red)" }), svg("rect", { class: "hit", x: m.l + i * step, y: m.t, width: step, height: ih }));
    tip(g, () => [h("b", `${d.x}`), h("small", `${d.v} ${d.v === 1 ? "gol" : "goles"}`)]);
    root.append(g);
    if (data.length <= 14 || i % Math.ceil(data.length / 12) === 0) root.append(svg("text", { x: x + bw / 2, y: H - 6, "text-anchor": "middle" }, String(d.x)));
  });
  return root;
}
