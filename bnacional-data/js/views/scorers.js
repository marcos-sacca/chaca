import { route } from "../app.js";
import { S } from "../store.js";
import { h, n, norm } from "../util.js";
import { head, table, T, href } from "./common.js";

const st = { q: "", club: "", season: "", lim: 50 };
route("goleadores", async () => {
  const page = h("div.wrap.page"), box = h("div"), more = h("button.btn.btn--ghost", { type: "button", onclick: () => { st.lim += 100; draw(); } }, "Mostrar más");
  const clubs = [...new Set(S.scorers.flatMap((o) => o.teamList))].sort((a, b) => T(a).short.localeCompare(T(b).short));
  const draw = () => {
    const f = norm(st.q);
    let list;
    if (st.season !== "") { // goleadores de una temporada
      const si = Number(st.season);
      list = Object.values(S.scBySeason[si]).filter((o) => (!st.club || o.team === Number(st.club)) && (!f || norm(o.name).includes(f))).sort((a, b) => b.g - a.g).map((o) => ({ name: o.name, goals: o.g, pen: null, teamList: [o.team], s0: si, s1: si }));
    } else list = S.scorers.filter((o) => (!st.club || o.teams.has(Number(st.club))) && (!f || norm(o.name).includes(f)));
    const shown = list.slice(0, st.lim);
    box.replaceChildren(table([{ label: "#" }, { label: "Jugador" }, { label: "Clubes" }, { label: "Años" }, { label: "Goles", cls: "num" }, { label: "De penal", cls: "num" }],
      shown.map((o, i) => h("tr", [h("td.num", i + 1), h("td", h("b", o.name)), h("td", o.teamList.slice(0, 3).map((t) => T(t).short).join(", ") + (o.teamList.length > 3 ? "…" : "")), h("td", o.s0 === o.s1 ? S.seasons[o.s0].label : `${S.seasons[o.s0].label.slice(0, 4)}–${S.seasons[o.s1].label.slice(-2)}`), h("td.num", h("b", o.goals)), h("td.num", o.pen ?? "–")]))));
    more.hidden = list.length <= shown.length;
    count.textContent = `${n(list.length)} jugadores`;
  };
  const count = h("span.muted");
  page.append(head("Goleadores", "Quién hizo más goles en la categoría", "Goles de fase regular, sin los goles en contra. Hasta 2018/19 los nombres vienen de las crónicas (con inicial del segundo nombre) y después de Solo Ascenso, por eso un mismo jugador puede aparecer dos veces."),
    h("div.toolbar", [
      h("input#gq", { type: "search", placeholder: "Buscar jugador", "aria-label": "Buscar jugador", oninput: (e) => { st.q = e.target.value; st.lim = 50; draw(); } }),
      h("select#gc", { "aria-label": "Club", onchange: (e) => { st.club = e.target.value; st.lim = 50; draw(); } }, [h("option", { value: "" }, "Todos los clubes"), ...clubs.map((t) => h("option", { value: t }, T(t).short))]),
      h("select#gs", { "aria-label": "Temporada", onchange: (e) => { st.season = e.target.value; st.lim = 50; draw(); } }, [h("option", { value: "" }, "Toda la historia"), ...S.seasons.map((s, i) => [s, i]).reverse().map(([s, i]) => h("option", { value: i }, s.label))]),
      count]), box, h("div.more", more));
  draw();
  return { page, title: "Goleadores" };
});
