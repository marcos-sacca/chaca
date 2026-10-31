// Primera Nacional 2027: cómo se va armando. Los clubes de la temporada base se clasifican solos con sus partidos
// (permanencia asegurada, descendidos, en juego, pelea el ascenso); los que llegan de otras categorías vienen de
// data/temporada_2027.json, a mano y con fuente. Todo lo «asegurado» es matemático: un empate en puntos cuenta como en juego.
import { route } from "../app.js";
import { S } from "../store.js";
import { h, n, fdate } from "../util.js";
import { head, sec, T, href, crest, monogram } from "./common.js";

let CFG = null;
const loadCfg = () => (CFG ||= fetch("data/temporada_2027.json").then((r) => r.json()).catch(() => null));

function estado(cfg) {
  const si = S.seasons.findIndex((s) => s.label === cfg.base);
  if (si < 0) return null;
  const s = S.seasons[si], zonas = s.tables.filter((t) => t.zona);
  const tabs = zonas.length ? zonas : s.tables.slice(0, 1);
  const w = s.ptsw || 3, promoted = new Set(s.promoted.map((p) => p[0]));
  const out = [];
  for (const t of tabs) {
    const rows = t.rows.map(([pos, ti, pj, , , , , , dg, , pts]) => ({ ti, pos, pj, pts, dg, max: pts + w * Math.max(0, cfg.fechas_total - pj), zona: t.fase }));
    const nz = rows.length, k = cfg.descensos_por_zona;
    for (const r of rows) {
      const others = rows.filter((u) => u !== r);
      const below = others.filter((u) => u.max < r.pts).length;           // seguro terminan abajo
      const above = others.filter((u) => u.pts > r.max).length;           // seguro terminan arriba
      r.desc = above >= nz - k;                                            // ya descendió
      r.safe = below >= k;                                                 // ya aseguró la permanencia
      const eighth = rows.slice().sort((a, b) => b.pts - a.pts)[cfg.plazas_reducido - 1];
      r.asc = promoted.has(r.ti) ? "subió" : r.max >= (eighth ? eighth.pts : 0) ? "pelea" : "";
      r.final = r.max >= Math.max(...rows.map((u) => u.pts));
      out.push(r);
    }
  }
  return { s, si, rows: out, rem: Math.max(0, cfg.fechas_total - Math.min(...out.map((r) => r.pj))) };
}

route("proxima", async () => {
  const page = h("div.wrap.page"), cfg = await loadCfg();
  if (!cfg) { page.append(h("p.muted", "No se pudo cargar la información de la próxima temporada.")); return { page, title: "2027" }; }
  const E = estado(cfg);
  if (!E) { page.append(h("p.muted", `No está la temporada ${cfg.base} en la base.`)); return { page, title: cfg.temporada }; }
  const club = (r, extra) => h("a.ccard.ccard--s.px__c", { href: href.club(r.ti) }, [crest(r.ti), h("span.ccard__t", [h("b", T(r.ti).short), extra ? h("small", extra) : null])]);
  const sigue = E.rows.filter((r) => r.safe && r.asc !== "subió"), riesgo = E.rows.filter((r) => !r.safe && !r.desc), bajan = E.rows.filter((r) => r.desc), suben = E.rows.filter((r) => r.asc === "subió");
  const confirmados = sigue.filter((r) => !r.asc).length + cfg.llegan.length;
  const ultimo = S.meta.ultimo;
  page.append(head(`Primera Nacional ${cfg.temporada}`, `Así se va armando la ${cfg.temporada}`, `Quiénes ya tienen lugar, quiénes llegan de otras categorías y qué falta definir. Con los partidos de la ${cfg.base} hasta el ${fdate(ultimo)}${E.rem ? ` · ${E.rem === 1 ? "falta 1 fecha" : `faltan ${E.rem} fechas`}` : " · temporada terminada"}.`));
  page.append(h("div.stats.stats--hi", [["Ya confirmados", confirmados, "sin chance de irse"], ["Llegan", cfg.llegan.length, "de otras categorías"], ["Pelean el ascenso", sigue.filter((r) => r.asc === "pelea").length, "siguen, salvo que suban"], ["En juego", riesgo.length, "por el descenso"]].map(([l, v, sub]) => h("div.stat", [h("b", n(v)), h("span", l), h("small", sub)]))));

  const llegan = cfg.llegan.map((x) => { const ti = x.slug ? S.teamBy.get(x.slug) : null; return h("div.px__new", [ti != null ? crest(ti) : h("div.mono.mono--s", h("span", x.nombre.split(/\s+/).filter((w) => w.length > 2).slice(0, 2).map((w) => w[0]).join("").toUpperCase())), h("div", [ti != null ? h("a", { href: href.club(ti) }, h("b", x.nombre)) : h("b", x.nombre), h("small", `${x.desde} · ${x.como}`), h("a.px__src", { href: x.fuente, target: "_blank", rel: "noopener" }, "fuente ↗")])]); });
  page.append(sec("Llegan", h("div.px__grid", llegan)));

  const byZone = (L, extra) => { const zs = [...new Set(L.map((r) => r.zona))]; return zs.map((z) => h("div.px__z", [zs.length > 1 ? h("h3", z) : null, h("div.cgrid", L.filter((r) => r.zona === z).sort((a, b) => a.pos - b.pos).map((r) => club(r, extra(r))))])); };
  page.append(sec("Siguen en la categoría", [h("p.muted", `Ya aseguraron la permanencia. Los marcados «pelea el ascenso» se quedan salvo que suban a Primera.`), ...byZone(sigue, (r) => `${r.pos}.º · ${r.pts} pts${r.asc === "pelea" ? (r.final ? " · pelea la final" : " · pelea el ascenso") : ""}`)]));
  if (riesgo.length) page.append(sec("Se juegan el descenso", [h("p.muted", `Bajan los ${cfg.descensos_por_zona} últimos de cada zona. Estos todavía pueden terminar ahí.`), ...byZone(riesgo, (r) => `${r.pos}.º · ${r.pts} pts`)]));
  if (bajan.length) page.append(sec(`Se van a la Primera B o al Federal A`, [h("p.muted", "Ya descendieron."), ...byZone(bajan, (r) => `${r.pos}.º · ${r.pts} pts`)]));
  if (suben.length) page.append(sec("Se van a Primera División", h("div.cgrid", suben.map((r) => club(r, "ascendió")))));
  page.append(sec("Falta definir", h("ul.px__todo", cfg.por_definir.map((t) => h("li", t)))));
  page.append(h("p.cap", [`Lo «asegurado» es matemático, con las ${E.rem} ${E.rem === 1 ? "fecha que falta" : "fechas que faltan"} y ${E.s.ptsw || 3} puntos por partido: un empate en puntos cuenta como todavía en juego. Las zonas son las de `, h("a", { href: href.season(E.si) }, `la temporada ${cfg.base}`), `. Lo que llega de otras categorías se carga a mano (actualizado el ${fdate(cfg.actualizado)}).`]));
  return { page, title: `Primera Nacional ${cfg.temporada}` };
});
