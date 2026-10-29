// gráficos SVG simples, a escala y con colores del tema
const NS = "http://www.w3.org/2000/svg";
export const s = (tag, attrs = {}, kids = []) => { const e = document.createElementNS(NS, tag); for (const [k, v] of Object.entries(attrs)) e.setAttribute(k, v); for (const c of [].concat(kids)) if (c != null) e.append(c instanceof Node ? c : document.createTextNode(c)); return e; };

// efectividad por temporada: puntos obtenidos / puntos posibles
export function effLine(points, { height = 190, onpick } = {}) {
  const W = 760, H = height, L = 38, R = 26, Tp = 14, B = 34, iw = W - L - R, ih = H - Tp - B;
  const svg = s("svg", { viewBox: `0 0 ${W} ${H}`, class: "chart", role: "img", "aria-label": "Efectividad del club temporada por temporada" });
  for (const v of [0, 0.25, 0.5, 0.75, 1]) {
    const y = Tp + ih * (1 - v);
    svg.append(s("line", { x1: L, x2: W - R, y1: y, y2: y, class: "grid" }), s("text", { x: L - 6, y: y + 4, class: "ax", "text-anchor": "end" }, Math.round(v * 100) + "%"));
  }
  const n = points.length, x = (i) => L + (n === 1 ? iw / 2 : (iw * i) / (n - 1));
  const real = points.map((p, i) => ({ ...p, i })).filter((p) => p.v != null);
  if (real.length > 1) {
    const d = real.map((p, k) => `${k ? "L" : "M"}${x(p.i).toFixed(1)},${(Tp + ih * (1 - p.v)).toFixed(1)}`).join("");
    svg.append(s("path", { d: d + `L${x(real[real.length - 1].i)},${Tp + ih}L${x(real[0].i)},${Tp + ih}Z`, class: "area" }), s("path", { d, class: "line" }));
  }
  const step = Math.max(1, Math.ceil(n / 9));
  points.forEach((p, i) => {
    if (i % step === 0 || i === n - 1) svg.append(s("text", { x: x(i), y: H - 12, class: "ax", "text-anchor": "middle" }, p.label));
    if (p.v == null) return;
    const c = s("circle", { cx: x(i), cy: Tp + ih * (1 - p.v), r: p.up ? 6 : 4, class: p.up ? "dot dot--up" : "dot", tabindex: onpick ? 0 : null }, [s("title", {}, `${p.label}: ${Math.round(p.v * 100)}%${p.up ? " · ascenso" : ""}`)]);
    if (onpick) { c.addEventListener("click", () => onpick(p)); c.style.cursor = "pointer"; }
    svg.append(c);
  });
  requestAnimationFrame(() => { const l = svg.querySelector(".line"); if (l) l.style.setProperty("--len", Math.ceil(l.getTotalLength?.() || 4000) + 8); });
  return svg;
}
