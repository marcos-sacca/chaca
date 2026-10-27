import { route } from "../app.js";
import { S, topScorers, DIVS, DIV_SHORT, title } from "../store.js";
import { h, n, pct, norm, dShort } from "../util.js";
import { hbars, miniColumns, legendGEP } from "../charts.js";
import { href, field, select, segmented, sortTable, statRow, pageHead, crumbs, matchRow, setQuery } from "./common.js";

route("jugadores", (r, page) => (r.arg ? one(r.arg, page) : all(r, page)));

function all(r, page) {
  const f = { tab: r.q.tab || "goles", div: r.q.div || "", dec: r.q.dec || "", sd: r.q.sd || "", q: r.q.q || "" };
  const out = h("div");
  const decs = [...new Set(S.matches.map((m) => m.dec))].sort();
  const sds = S.seasons.map((s) => s.sd);
  const draw = () => {
    setQuery("jugadores", f);
    const q = norm(f.q);
    if (f.tab === "goles") {
      const rows = topScorers({ div: f.div, dec: f.dec, sd: f.sd }).filter((x) => !q || norm(x.p.name).includes(q));
      out.replaceChildren(
        h("p.muted", { style: { marginBottom: "10px" } }, `${n(rows.length)} jugadores con goles${f.sd || f.dec || f.div ? " en este filtro" : ""}. «PJ» cuenta solo partidos con formación cargada.`),
        rows.length ? h("div.panel", { style: { marginBottom: "22px" } }, hbars(rows.slice(0, 10).map((x) => ({ label: x.p.name, value: x.g, href: href.player(x.p.name) })), { limit: 10 })) : null,
        sortTable([
          { t: "#", v: (x) => rows.indexOf(x) + 1, f: (x) => rows.indexOf(x) + 1 },
          { t: "Jugador", v: (x) => x.p.name, f: (x) => h("a", { href: href.player(x.p.name) }, h("b", x.p.name)) },
          { t: "Goles", v: (x) => x.g, r: true, desc: true, f: (x) => h("b", x.g) },
          { t: "Penales", v: (x) => x.pen, r: true, desc: true },
          { t: "PJ", v: (x) => x.pj, r: true, desc: true },
          { t: "Goles por partido", v: (x) => (x.pj ? x.gl / x.pj : null), r: true, desc: true, f: (x) => (x.pj >= 10 ? (x.gl / x.pj).toFixed(2).replace(".", ",") : "—") },
          { t: "Años", v: (x) => x.y0, r: true, f: (x) => (x.y0 === x.y1 ? x.y0 : `${x.y0}–${x.y1}`) },
        ], rows, { sort: 2, dir: -1, limit: 30, rowHref: (x) => href.player(x.p.name), empty: "No hay goleadores con ese filtro." }),
      );
    } else {
      const rows = S.playerList.filter((p) => p.pj && (!q || norm(p.name).includes(q)));
      out.replaceChildren(
        h("p.muted", { style: { marginBottom: "10px" } }, "Partidos jugados según las formaciones cargadas (no hay formaciones de todos los partidos, sobre todo antes de 1960)."),
        sortTable([
          { t: "Jugador", v: (p) => p.name, f: (p) => h("a", { href: href.player(p.name) }, h("b", p.name)) },
          { t: "PJ", v: (p) => p.pj, r: true, desc: true, f: (p) => h("b", n(p.pj)) },
          { t: "Titular", v: (p) => p.tit, r: true, desc: true }, { t: "Goles", v: (p) => p.ng, r: true, desc: true },
          { t: "Años", v: (p) => p.y0, r: true, f: (p) => (p.y0 === p.y1 ? p.y0 : `${p.y0}–${p.y1}`) },
        ], rows, { sort: 1, dir: -1, limit: 30, rowHref: (p) => href.player(p.name) }),
      );
    }
  };
  const text = h("input.in", { id: "jq", type: "search", value: f.q, placeholder: "Nombre", autocomplete: "off" });
  text.addEventListener("input", () => { f.q = text.value; draw(); });
  const filtersG = h("div.filters", [
    field("Jugador", text, "jq"),
    field("División", select("jd", [["", "Todas"], ...DIVS.slice(0, 3).map((d) => [d, DIV_SHORT[d]])], f.div, (v) => { f.div = v; draw(); }), "jd"),
    field("Década", select("jdec", [["", "Todas"], ...decs.map((d) => [d, `${d}s`])], f.dec, (v) => { f.dec = v; draw(); }), "jdec"),
    field("Temporada", select("jsd", [["", "Todas"], ...sds.slice().reverse().map((d) => [d, d])], f.sd, (v) => { f.sd = v; draw(); }), "jsd"),
  ]);
  const tabs = h("div.tabs", [["goles", "Goleadores"], ["pj", "Más partidos"]].map(([k, t]) => h("button", { type: "button", "aria-pressed": String(f.tab === k), onclick: (e) => { f.tab = k; tabs.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", "false")); e.currentTarget.setAttribute("aria-pressed", "true"); filtersG.hidden = k !== "goles" ? false : false; draw(); } }, t)));
  page.append(h("div.wrap.page", [pageHead("Jugadores", "Quién hizo qué", `${n(S.playerList.length)} jugadores en la base: goles desde 1931 y formaciones de ${n(S.hasLineup.size)} partidos.`), tabs, filtersG, out]));
  draw();
  return { title: "Jugadores" };
}

function one(name, page) {
  const p = S.playerMap.get(name);
  if (!p) {
    const q = norm(name), hits = S.playerList.filter((x) => norm(x.name).includes(q)).sort((a, b) => b.ng - a.ng || b.pj - a.pj).slice(0, 30);
    page.append(h("div.wrap.page", [crumbs({ t: "Jugadores", href: "#/jugadores" }, { t: name }), pageHead(null, "No hay un jugador con ese nombre exacto", hits.length ? "Quizás buscabas a alguno de estos:" : "Probá con el buscador de arriba."), h("ul", hits.map((x) => h("li", h("a.link", { href: href.player(x.name) }, `${x.name} · ${x.ng} goles · ${x.pj} PJ`))))]));
    return { title: "Jugador" };
  }
  const gm = p.goals.slice().sort((a, b) => a.m.d.localeCompare(b.m.d));
  const byY = new Map(); gm.forEach((g) => byY.set(g.m.y, (byY.get(g.m.y) || 0) + 1));
  const byR = new Map(); gm.forEach((g) => byR.set(g.m.r, (byR.get(g.m.r) || 0) + 1));
  const byDiv = new Map(); gm.forEach((g) => byDiv.set(g.m.div, (byDiv.get(g.m.div) || 0) + 1));
  const topR = [...byR].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], "es")).slice(0, 8).map(([r, v]) => ({ label: r, value: v, href: href.rival(r) }));
  const pen = gm.filter((g) => g.pen).length;
  const rank = [...S.playerList].sort((a, b) => b.ng - a.ng).findIndex((x) => x === p) + 1;
  const mWithGoals = [...new Set(gm.map((g) => g.m))];
  const apps = p.apps.slice().sort((a, b) => b.m.d.localeCompare(a.m.d));
  const hat = [...new Map(gm.map((g) => [g.m.id, 0])).keys()].filter((id) => gm.filter((g) => g.m.id === id).length >= 3);
  page.append(h("div.wrap.page", [
    crumbs({ t: "Jugadores", href: "#/jugadores" }, { t: p.name }),
    pageHead(null, p.name, p.y0 ? `En la base desde ${p.y0}${p.y1 !== p.y0 ? ` hasta ${p.y1}` : ""}.` : ""),
    statRow([["Goles", n(p.ng), p.ng ? `puesto ${rank} histórico` : null], ["Partidos", n(p.pj), p.pj ? `${p.tit} de titular` : "sin formaciones cargadas"], ["Penales", pen], ["Triplete o más", hat.length], p.ownGoals ? ["En contra", p.ownGoals] : null].filter(Boolean)),
    byY.size ? h("section.sec", { "data-reveal": "" }, [h("h2", { style: { marginBottom: "12px" } }, "Goles por año"), h("div.panel", miniColumns([...byY].sort((a, b) => a[0] - b[0]).map(([x, v]) => ({ x, v }))))]) : null,
    topR.length ? h("section.sec.cols2", { "data-reveal": "" }, [
      h("div", [h("h2", { style: { marginBottom: "12px" } }, "A quién más le convirtió"), hbars(topR, { limit: 8 })]),
      h("div", [h("h2", { style: { marginBottom: "12px" } }, "En qué división"), h("div.bars", [...byDiv].sort((a, b) => b[1] - a[1]).map(([d, v]) => h("div", { style: { display: "flex", justifyContent: "space-between", padding: "8px 0", borderBottom: "1px solid var(--line)" } }, [h("span", d), h("b.num", v)])))]),
    ]) : null,
    mWithGoals.length ? h("section.sec", { "data-reveal": "" }, [h("h2", { style: { marginBottom: "10px" } }, "Partidos en los que convirtió"), h("div.mlist", mWithGoals.sort((a, b) => b.d.localeCompare(a.d)).slice(0, 25).map((m) => { const k = gm.filter((g) => g.m === m).length; const row = matchRow(m); if (k > 1) row.querySelector(".m__t").append(h("span.mark", `${k} goles`)); return row; })), mWithGoals.length > 25 ? h("p.cap", `Se muestran los 25 más recientes de ${mWithGoals.length}.`) : null]) : null,
    apps.length ? h("section.sec", { "data-reveal": "" }, [h("h2", { style: { marginBottom: "10px" } }, "Últimos partidos jugados"), h("div.mlist", apps.slice(0, 10).map((a) => matchRow(a.m)))]) : null,
  ]));
  return { title: p.name };
}
