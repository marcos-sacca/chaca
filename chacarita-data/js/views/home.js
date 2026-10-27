import { route, suggestBox } from "../app.js";
import { S, sum, title, onDay } from "../store.js";
import { h, n, pct, countUp, dShort, MESES, resChip } from "../util.js";
import { stackBar, legendGEP, divisionTimeline } from "../charts.js";
import { href, matchRow, figure, loadCredits, kpi, IMG } from "./common.js";

route("inicio", async (r, page) => {
  await loadCredits();
  const M = S.matches, T = sum(M), F = S.facts;
  const last = M[M.length - 1];
  const years = new Date(last.d).getFullYear() - 1931;

  // ── portada
  const input = h("input", { type: "search", placeholder: matchMedia("(max-width: 640px)").matches ? "Rival, jugador o año" : "Buscá un rival, un jugador o un año", "aria-label": "Buscar rival, jugador o año", autocomplete: "off", spellcheck: false });
  const go = (x) => (location.hash = x.href);
  const find = h("div.hero__find", [
    h("div.bigsearch", [input, h("button.btn", { type: "button", onclick: () => { const t = input.value.trim(); if (t) location.hash = `#/rivales/${encodeURIComponent(t)}`; } }, "Buscar")]),
    suggestBox(input, go),
  ]);
  const figs = [[T.pj, "partidos"], [T.g, "victorias"], [T.gf, "goles a favor"], [years, "años de historia"]].map(([v, l]) => {
    const num = h("div.fig__n.num", "0"); countUp(num, v);
    return h("div.fig", { "data-reveal": "" }, [num, h("div.fig__l", l)]);
  });
  const hero = h("section.hero", [
    h("div", [
      h("h1.display", ["Todo ", h("em", "Chacarita"), ", partido por partido"]),
      h("p.lead", { style: { marginTop: "22px" } }, `${n(T.pj)} partidos desde 1931, con sus goles, formaciones, rachas y récords.`),
      find,
    ]),
    h("div", [h("div.hero__photo", [h("img", { src: "assets/img/h-1983.jpg", alt: "Plantel de Chacarita Juniors en 1983, con la camiseta de bastones rojos y negros", fetchpriority: "high" })]), credit("h-1983")]),
  ]);

  // ── últimos partidos + un día como hoy
  const lastTen = M.slice(-10).reverse();
  const today = new Date(), md = `${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;
  const otd = onDay(md);
  const seas = S.seasons[S.seasons.length - 1], ss = sum(seas.main);
  const colA = h("div", [
    h("div.sec__head", [h("h2", "Últimos partidos"), h("a.link", { href: "#/partidos" }, "Ver todos")]),
    h("div.form", { style: { marginBottom: "12px" }, "aria-label": "Últimos 10 resultados" }, lastTen.slice().reverse().map((m) => resChip(m.res))),
    h("div.mlist", lastTen.slice(0, 7).map((m) => matchRow(m))),
  ]);
  const colB = h("div", [
    h("div.sec__head", [h("h2", "Un día como hoy"), h("a.link", { href: `#/efemerides/${md}` }, `${today.getDate()} de ${MESES[today.getMonth()]}`)]),
    otd.length ? h("div.mlist", otd.slice(0, 6).map((m) => h("a.m", { href: href.match(m) }, [
      h("span.m__d", m.y), h("span.m__t", [h("b", `${m.l} – ${m.v}`), h("small", m.tn)]), h("span.m__s.num", [m.gl ?? "?", h("span", "-"), m.gv ?? "?"]), resChip(m.res)])))
      : h("p.muted", "Ese día Chacarita no jugó partidos oficiales."),
  ]);
  const now = h("section.sec.split", { "data-reveal": "" }, [colA, colB]);

  // ── temporada en curso
  const cur = h("section.sec", { "data-reveal": "" }, [
    h("div.sec__head", [h("h2", `Temporada ${seas.sd}`), h("a.link", { href: href.season(seas.sd) }, "Ver la temporada")]),
    h("div.panel", [
      h("div.row", { style: { justifyContent: "space-between", marginBottom: "12px" } }, [
        h("div", [h("div.rec__v", `${ss.g}-${ss.e}-${ss.p}`), h("div.rec__d", `${ss.pj} partidos · ${ss.gf} goles a favor, ${ss.gc} en contra`)]),
        legendGEP(),
      ]),
      stackBar(ss, { tall: true }),
    ]),
  ]);

  // ── récords
  const rec = h("section.sec", { "data-reveal": "" }, [
    h("div.sec__head", [h("h2", "Lo más grande"), h("a.link", { href: "#/records" }, "Todos los récords")]),
    h("div.grid.g3", [
      rcard("Goleador histórico", F.scorer.ng, `${F.scorer.name} · ${F.scorer.y0}–${F.scorer.y1}`, href.player(F.scorer.name)),
      rcard("Más partidos jugados", F.appear.pj, `${F.appear.name} (con formación cargada)`, href.player(F.appear.name)),
      rcard("Mayor goleada", `${F.bigWin.gf}-${F.bigWin.gc}`, `${F.bigWin.v === "Chacarita" ? F.bigWin.l : F.bigWin.v} · ${dShort(F.bigWin.d)}`, href.match(F.bigWin)),
      rcard("Peor derrota", `${F.bigLoss.gf}-${F.bigLoss.gc}`, `${F.bigLoss.l === "Chacarita" ? F.bigLoss.v : F.bigLoss.l} · ${dShort(F.bigLoss.d)}`, href.match(F.bigLoss)),
      rcard("Partido con más goles", (F.mostGoals.gf ?? 0) + (F.mostGoals.gc ?? 0), `${title(F.mostGoals)} · ${dShort(F.mostGoals.d)}`, href.match(F.mostGoals)),
      rcard("Racha invicta más larga", F.unb.len, `${dShort(F.unb.first.d)} a ${dShort(F.unb.last.d)}`, "#/records"),
    ]),
  ]);

  // ── clásicos
  const cl = h("section.sec", { "data-reveal": "" }, [
    h("div.sec__head", [h("h2", "Los rivales de siempre"), h("a.link", { href: "#/rivales" }, "Todos los rivales")]),
    h("div.panel", [
      legendGEP(),
      h("div", { style: { marginTop: "14px", display: "grid", gap: "12px" } }, S.rivals.slice(0, 8).map((rv) => h("a.rivrow", { href: href.rival(rv.name), style: { display: "grid", gridTemplateColumns: "minmax(110px,190px) 1fr 64px", gap: "14px", alignItems: "center" } }, [
        h("b", rv.name), stackBar(rv.s), h("span.num.muted", { style: { textAlign: "right" } }, `${rv.s.pj} PJ`)]))),
    ]),
  ]);

  // ── mapa de divisiones
  const items = S.seasons.map((s) => ({ sd: s.sd, div: s.div, y: s.list[0].y, pos: s.torneos.find((t) => t.pos && t.tipo !== "Copa")?.pos || null }));
  const map = h("section.sec", { "data-reveal": "" }, [
    h("div.sec__head", [h("h2", "Noventa y cinco años, tres categorías")]),
    h("div.panel", [divisionTimeline(items, { onpick: (it) => (location.hash = href.season(it.sd)) }), h("p.cap", "Cada punto es una temporada; tocá uno para verla. Rojo: Primera División.")]),
  ]);

  // ── fotos
  const gal = h("section.sec", { "data-reveal": "" }, [
    h("div.sec__head", [h("h2", "La camiseta y la cancha")]),
    h("div.gallery", [
      figure("assets/img/h-1969.jpg", "El plantel campeón de 1969", "h-1969"),
      figure("assets/img/h-river69.jpg", "Chacarita frente a River, 1969", "h-river69"),
      figure("assets/img/h-inauguracion.jpg", "Inauguración del estadio", "h-inauguracion"),
      figure("assets/img/h-cabecera.jpg", "Cabecera local del estadio de Chacarita", "h-cabecera"),
      figure("assets/img/h-1937.jpg", "Formación de 1937", "h-1937"),
      figure("assets/img/h-tribuna.jpg", "Tribuna oficial del estadio", "h-tribuna"),
    ]),
  ]);

  page.append(h("div.wrap.page", [hero, h("div.figs", figs), now, cur, rec, cl, map, gal]));
  return { title: "" };
});

const rcard = (k, v, d, to) => h("a.rec", { href: to }, [h("span.rec__k", k), h("span.rec__v.num", String(v)), h("span.rec__d", d)]);
function credit(key) {
  const c = IMG[key]; if (!c) return null;
  return h("p.cap", [c.caption || c.title, " — ", c.author ? c.author + ", " : "", h("a", { href: c.page, target: "_blank", rel: "noopener" }, c.lic)]);
}
