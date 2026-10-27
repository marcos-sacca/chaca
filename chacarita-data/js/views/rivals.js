import { route } from "../app.js";
import { S, sum, byCond, longestRun, search, searchIndex, condName, title } from "../store.js";
import { h, n, pct, dShort, signed } from "../util.js";
import { stackBar, legendGEP, stackedColumns, hbars } from "../charts.js";
import { href, field, sortTable, statRow, pageHead, crumbs, matchBrowser, select, rowsTable } from "./common.js";

route("rivales", (r, page) => {
  if (r.arg) {
    const rv = S.rivalMap.get(r.arg);
    if (rv) return one(rv, page);
    const hit = search(r.arg, searchIndex(), 8).find((e) => e.k === "Rival");
    if (hit && search(r.arg, searchIndex(), 8).filter((e) => e.k === "Rival").length === 1) { location.replace(hit.href); return { title: "Rivales" }; }
    return all(page, r.arg);
  }
  return all(page, "");
});

function all(page, q0) {
  let q = q0.toLowerCase(), min = 1;
  const out = h("div");
  const draw = () => {
    const t = q.normalize("NFD").replace(/[̀-ͯ]/g, "");
    const rows = S.rivals.filter((x) => x.s.pj >= min && (!t || x.name.toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "").includes(t)));
    out.replaceChildren(
      h("p.muted", { style: { marginBottom: "10px" } }, `${n(rows.length)} rivales`),
      sortTable([
        { t: "Rival", v: (x) => x.name, f: (x) => h("a", { href: href.rival(x.name) }, h("b", x.name)) },
        { t: "PJ", v: (x) => x.s.pj, r: true, desc: true },
        { t: "G", v: (x) => x.s.g, r: true, desc: true }, { t: "E", v: (x) => x.s.e, r: true, desc: true }, { t: "P", v: (x) => x.s.p, r: true, desc: true },
        { t: "GF", v: (x) => x.s.gf, r: true, desc: true }, { t: "GC", v: (x) => x.s.gc, r: true, desc: true },
        { t: "Dif.", v: (x) => x.s.dg, r: true, desc: true, f: (x) => signed(x.s.dg) },
        { t: "Efectividad", v: (x) => x.s.ef, r: true, desc: true, f: (x) => pct(x.s.ef, 1) },
        { t: "Balance", v: (x) => x.s.ef, f: (x) => h("div", { style: { width: "120px" } }, stackBar(x.s)) },
        { t: "Último", v: (x) => x.list[x.list.length - 1].d, r: true, desc: true, f: (x) => dShort(x.list[x.list.length - 1].d) },
      ], rows, { sort: 1, limit: 40, rowHref: (x) => href.rival(x.name) }),
    );
  };
  const input = h("input.in", { id: "rq", type: "search", value: q0, placeholder: "Nombre del rival", autocomplete: "off", style: { minWidth: "230px" } });
  input.addEventListener("input", () => { q = input.value; draw(); });
  page.append(h("div.wrap.page", [
    pageHead("Rivales", "Contra quién jugó", `${n(S.rivals.length)} rivales distintos en ${n(S.matches.length)} partidos. Tocá un encabezado para ordenar o un rival para ver el historial completo.`),
    h("div.filters", [field("Buscar", input, "rq"), field("Partidos jugados", select("rmin", [[1, "Todos"], [5, "5 o más"], [10, "10 o más"], [20, "20 o más"], [40, "40 o más"]], 1, (v) => { min = +v; draw(); }), "rmin"), h("div", { style: { alignSelf: "center" } }, legendGEP())]),
    out,
  ]));
  draw();
  return { title: "Rivales" };
}

function one(rv, page) {
  const L = rv.list, s = rv.s, last = L[L.length - 1], first = L[0];
  const wins = L.filter((m) => m.res === "G" && m.gf != null), loss = L.filter((m) => m.res === "P" && m.gf != null);
  const bw = wins.sort((a, b) => (b.gf - b.gc) - (a.gf - a.gc) || b.gf - a.gf || a.d.localeCompare(b.d))[0];
  const bl = loss.sort((a, b) => (b.gc - b.gf) - (a.gc - a.gf) || b.gc - a.gc || a.d.localeCompare(b.d))[0];
  const inv = longestRun(L, (m) => m.res !== "P"), win = longestRun(L, (m) => m.res === "G"), nowInv = inv.now;
  const cond = ["L", "V", "N"].map((c) => [c, sum(byCond(L, c))]).filter(([, x]) => x.pj);
  const byYear = new Map();
  L.forEach((m) => { const o = byYear.get(m.y) || { x: m.y, G: 0, E: 0, P: 0 }; o[m.res]++; byYear.set(m.y, o); });
  const scorers = new Map();
  L.forEach((m) => (m.g || []).forEach((g) => { if (g.p && !g.ec) scorers.set(g.p, (scorers.get(g.p) || 0) + 1); }));
  const topS = [...scorers].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "es")).slice(0, 8).map(([p, v]) => ({ label: p, value: v, href: href.player(p) }));
  const mk = (t, m, extra) => m ? h("a.strk", { href: href.match(m) }, [h("b", t), h("span.strk__v.num", extra), h("small", `${title(m)} · ${dShort(m.d)}`)]) : null;
  page.append(h("div.wrap.page", [
    crumbs({ t: "Rivales", href: "#/rivales" }, { t: rv.name }),
    pageHead(null, rv.name, `${n(s.pj)} ${s.pj === 1 ? "partido" : "partidos"} entre ${first.y} y ${last.y}.`),
    statRow([["Jugados", n(s.pj)], ["Ganó", n(s.g), pct(s.g / s.pj, 0)], ["Empató", n(s.e), pct(s.e / s.pj, 0)], ["Perdió", n(s.p), pct(s.p / s.pj, 0)], ["Goles", `${s.gf}–${s.gc}`, `diferencia ${signed(s.dg)}`], ["Efectividad", pct(s.ef, 1), "puntos a 3 por victoria"]]),
    h("div.panel", { style: { marginTop: "22px" } }, [h("div.row", { style: { justifyContent: "space-between", marginBottom: "12px" } }, [h("b", "Balance"), legendGEP()]), stackBar(s, { tall: true })]),
    h("section.sec.cols2", { "data-reveal": "" }, [
      h("div", [h("h2", "Local y visitante"), rowsTable([{ t: "Condición" }, { t: "PJ", r: 1 }, { t: "G", r: 1 }, { t: "E", r: 1 }, { t: "P", r: 1 }, { t: "Goles", r: 1 }, { t: "Efect.", r: 1 }], cond.map(([c, x]) => [condName[c], x.pj, x.g, x.e, x.p, `${x.gf}–${x.gc}`, pct(x.ef, 0)]))]),
      h("div", [h("h2", "Marcas contra este rival"), h("div", [
        mk("Mayor victoria", bw, `${bw?.gf}-${bw?.gc}`), mk("Mayor derrota", bl, `${bl?.gf}-${bl?.gc}`),
        inv.len > 1 ? h("div.strk", [h("b", "Racha invicta más larga"), h("span.strk__v.num", inv.len), h("small", `${dShort(inv.first.d)} a ${dShort(inv.last.d)}${nowInv ? " · sigue vigente" : ""}`)]) : null,
        win.len > 1 ? h("div.strk", [h("b", "Victorias seguidas"), h("span.strk__v.num", win.len), h("small", `${dShort(win.first.d)} a ${dShort(win.last.d)}`)]) : null,
      ])]),
    ]),
    byYear.size > 3 ? h("section.sec", { "data-reveal": "" }, [h("h2", "Año por año"), h("div.panel", [h("div", { style: { marginBottom: "10px" } }, legendGEP()), stackedColumns([...byYear.values()], { every: Math.ceil(byYear.size / 14) })])]) : null,
    topS.length ? h("section.sec", { "data-reveal": "" }, [h("div.sec__head", [h("h2", "Quiénes más le convirtieron")]), hbars(topS, { limit: 8 }), h("p.cap", "Solo partidos con goleadores cargados.")]) : null,
    h("section.sec", { "data-reveal": "" }, [h("h2", { style: { marginBottom: "10px" } }, "Todos los partidos"), matchBrowser(L)]),
  ]));
  return { title: rv.name };
}
