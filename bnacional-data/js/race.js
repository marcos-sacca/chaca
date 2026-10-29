// carrera de la tabla histórica: puntos acumulados (3 por victoria) club por club, temporada tras temporada
import { S } from "./store.js";
import { h, n } from "./util.js";

let frames = null;
function build() {
  if (frames) return frames;
  const T = S.teams.length, acc = new Float64Array(T); frames = [];
  const bySeason = S.seasons.map(() => []);
  S.matches.forEach((m) => bySeason[m[0]].push(m));
  S.seasons.forEach((s, si) => {
    for (const m of bySeason[si]) { if (m[6] > m[7]) acc[m[4]] += 3; else if (m[6] < m[7]) acc[m[5]] += 3; else { acc[m[4]] += 1; acc[m[5]] += 1; } }
    frames.push(Float64Array.from(acc));
  });
  return frames;
}

export function race({ rows = 12, autoplay = false, compact = false } = {}) {
  const F = build(), N = F.length, ROW = 38;
  const top = (i) => { const f = F[i], idx = []; for (let t = 0; t < f.length; t++) if (f[t] > 0) idx.push(t); return idx.sort((a, b) => f[b] - f[a]).slice(0, rows); };
  const rowsEl = new Map();
  const stage = h("div.race__stage", { style: { "--n": rows } });
  const year = h("div.race__year", { "aria-hidden": "true" });
  const label = h("span.race__lab");
  const slider = h("input", { type: "range", min: 0, max: N - 1, value: N - 1, "aria-label": "Temporada", id: compact ? "race-s1" : "race-s2" });
  const play = h("button.iconbtn", { type: "button", "aria-label": "Reproducir" }, "▶");
  const speed = h("select", { "aria-label": "Velocidad", id: compact ? "race-v1" : "race-v2" }, [["Lento", 1400], ["Normal", 900], ["Rápido", 450]].map(([l, v], i) => h("option", { value: v, selected: i === 1 }, l)));
  let cur = N - 1, timer = null;
  const rowFor = (t) => {
    let r = rowsEl.get(t);
    if (!r) {
      r = h("a.race__row", { href: `#c-${S.teams[t].s}`, style: { transform: `translateY(${rows * ROW}px)`, opacity: 0 } }, [h("span.race__n", S.teams[t].short), h("span.race__bar", h("b", "0"))]);
      rowsEl.set(t, r); stage.append(r);
    }
    return r;
  };
  function draw(i) {
    cur = i; slider.value = i;
    const ids = top(i), f = F[i], mx = f[ids[0]] || 1, up = new Set(S.seasons[i].promoted.map((p) => p[0]));
    ids.forEach((t, k) => { const r = rowFor(t); r.style.opacity = 1; r.style.transform = `translateY(${k * ROW}px)`; r.classList.toggle("up", up.has(t)); r.style.setProperty("--w", (f[t] / mx) * 100); r.querySelector("b").textContent = n(f[t]); r.tabIndex = 0; });
    for (const [t, r] of rowsEl) if (!ids.includes(t)) { r.style.opacity = 0; r.style.transform = `translateY(${rows * ROW}px)`; r.tabIndex = -1; }
    year.textContent = S.seasons[i].label.replace("Transición ", "T");
    label.textContent = S.seasons[i].label;
    slider.style.setProperty("--v", "100%");
  }
  function stop() { clearTimeout(timer); timer = null; play.textContent = "▶"; play.setAttribute("aria-label", "Reproducir"); }
  function tick() {
    if (!stage.isConnected) { stop(); return; }
    if (cur >= N - 1) { stop(); return; }
    draw(cur + 1); timer = setTimeout(tick, Number(speed.value));
  }
  function start() { if (cur >= N - 1) draw(0); play.textContent = "❚❚"; play.setAttribute("aria-label", "Pausar"); timer = setTimeout(tick, 350); }
  play.addEventListener("click", () => (timer ? stop() : start()));
  slider.addEventListener("input", () => { stop(); draw(Number(slider.value)); });
  const box = h("div.race", [stage, year, h("div.race__ctl", [play, slider, label, speed]), compact ? null : h("p.race__note", "Los puntos se calculan con 3 por victoria en todas las épocas. Las barras celestes claras son los clubes que ascendieron esa temporada. Tocá un club para ver su historia.")]);
  draw(N - 1);
  if (autoplay && !matchMedia("(prefers-reduced-motion: reduce)").matches && "IntersectionObserver" in window) {
    const io = new IntersectionObserver((es) => { if (es[0].isIntersecting) { io.disconnect(); setTimeout(() => { if (!timer && stage.isConnected) { draw(0); start(); } }, 400); } }, { threshold: 0.45 });
    io.observe(box);
  }
  return box;
}
