import { route } from "../app.js";
import { S, search } from "../store.js";
import { h, n, countUp, debounce } from "../util.js";
import { ascCard, sec, T, href, crest } from "./common.js";
import { race } from "../race.js";

function stairs() {
  const N = S.seasons.length, tip = h("div.stairs__tip", { "aria-hidden": "true" }), box = h("div.stairs", { role: "group", "aria-label": "Una barra por temporada: tocá una para ver su campeón" });
  const show = (b, s) => {
    box.querySelectorAll(".on").forEach((x) => x.classList.remove("on")); b.classList.add("on");
    tip.replaceChildren(s.label, h("small", s.champion != null ? `Campeón: ${T(s.champion).short}` : s.promoted.length ? `Subieron: ${s.promoted.map((p) => T(p[0]).short).join(", ")}` : "Sin ascensos")); tip.classList.add("on");
    const x = b.offsetLeft + b.offsetWidth / 2; tip.style.left = Math.max(0, Math.min(x - 60, box.clientWidth - tip.offsetWidth)) + "px";
  };
  S.seasons.forEach((s, i) => {
    const b = h("button.stairs__bar", { type: "button", "data-y": s.label, style: { "--h": 16 + (84 * i) / (N - 1), "--i": i }, "aria-label": `${s.label}${s.champion != null ? ", campeón " + T(s.champion).short : ""}`, onpointerenter: () => show(b, s), onfocus: () => show(b, s), onclick: () => (location.hash = href.season(i)) });
    box.append(b);
  });
  box.addEventListener("pointerleave", () => { tip.classList.remove("on"); box.querySelectorAll(".on").forEach((x) => x.classList.remove("on")); });
  box.append(tip);
  return box;
}

route("inicio", async () => {
  const M = S.meta, page = h("div");
  const input = h("input#herosearch", { type: "search", placeholder: "Buscá un club, una temporada o un goleador", "aria-label": "Buscar", autocomplete: "off", spellcheck: "false" });
  const box = h("ul.suggest", { role: "listbox", hidden: true });
  const draw = () => { const r = search(input.value, 7); box.hidden = !r.length; box.replaceChildren(...r.map((x) => h("li", h("a", { href: x.href, onclick: () => (box.hidden = true) }, [h("span.sug__k", x.k), h("span.sug__n", x.n), h("span.sug__d", x.d)])))); };
  input.addEventListener("input", debounce(draw, 60)); input.addEventListener("blur", () => setTimeout(() => (box.hidden = true), 150));
  page.append(h("section.hero", h("div.wrap.hero__in", [
    h("div.hero__txt", [h("p.eyebrow", "Primera B Nacional · Primera Nacional"), h("h1", ["40 años de ", h("span.w", "ascensos")]), h("p.lead", `${n(M.partidos)} partidos de la segunda categoría del fútbol argentino desde 1986, con sus goleadores, tablas y los ${M.ascensos} clubes que subieron a Primera.`), h("div.hero__find", [input, box])]),
    stairs(),
  ])));
  const kpis = [[M.temporadas, "torneos"], [M.clubes, "clubes"], [M.partidos, "partidos"], [M.goles, "goles"]].map(([v, l]) => { const d = h("div.kpi__n", "0"); countUp(d, v, 1400); return h("div.kpi", [d, h("div.kpi__l", l)]); });
  page.append(h("div.wrap", h("div.kpis", kpis)));

  // cartel de campeones
  const champs = S.seasons.map((s, si) => ({ s, si })).filter((x) => x.s.champion != null).reverse();
  const items = champs.map(({ s, si }) => h("a", { href: href.season(si) }, [h("small", s.label), T(s.champion).short]));
  page.append(h("div.marquee", { "aria-label": "Campeones de todas las temporadas" }, h("div.marquee__in", [...items, ...items.map((x) => x.cloneNode(true))])));

  page.append(h("div.wrap", sec("Los que subieron", [h("p.muted", "Los últimos ascensos a Primera División. Tocá una tarjeta para verla en grande."), h("div.rail", S.ascensos.slice(-14).reverse().map((a) => ascCard(a)))], h("a.link", { href: "#ascensos" }, "Todos los ascensos →"))));

  page.append(h("div.wrap", sec("La tabla histórica en movimiento", [h("p.muted", "Cómo se fue armando la tabla de todos los tiempos, temporada por temporada. Mirá quién lidera en cada época o movelo vos."), race({ rows: 10, autoplay: true, compact: true })], h("a.link", { href: "#carrera" }, "Pantalla completa →"))));

  // todos los ascendidos por temporada: el campeón destacado, el resto como complemento (desplegable si son muchos)
  const upSeasons = S.seasons.map((s, si) => ({ s, si })).filter((x) => x.s.promoted.length).reverse();
  const chip = (t, how) => h("a.upchip" + (how === "Campeón" ? ".is-champ" : ""), { href: href.club(t) }, [crest(t), T(t).short]);
  const row = ({ s, si }) => {
    const champ = s.promoted.find((p) => p[1] === "Campeón"), rest = s.promoted.filter((p) => p !== champ);
    const many = rest.length > 3;
    return h("li", [
      h("a.champs__row", { href: href.season(si) }, [h("span.champs__y", s.label), champ ? h("span.champs__n", [crest(champ[0]), T(champ[0]).short, h("small.champs__tag", "Campeón")]) : h("span.champs__n.is-none", "Sin campeón")]),
      rest.length ? (many ? h("details.champs__more", [h("summary", `${champ ? "y " : ""}${rest.length} ${champ ? "ascendidos más" : "clubes ascendieron"}`), h("div.upchips", rest.map((p) => chip(p[0], p[1])))]) : h("div.upchips", rest.map((p) => chip(p[0], p[1])))) : null,
    ].filter(Boolean));
  };
  page.append(h("div.wrap", sec("Todos los ascendidos", [h("p.muted", "Cada temporada: el campeón primero y, abajo, los demás clubes que subieron a Primera."), h("ol.champs", upSeasons.map(row))], h("a.link", { href: "#temporadas" }, "Todas las temporadas →"))));

  const top = [...S.general].sort((a, b) => b[12] - a[12]).slice(0, 10), mx = top[0][12];
  const left = h("div", [h("div.sec__head", [h("h2", "Tabla histórica"), h("a.link", { href: "#tabla" }, "Completa →")]), h("p.muted", "Puntos con 3 por victoria, para comparar todas las épocas."), h("ol.bars", top.map((r, i) => h("li", h("a", { href: href.club(r[1]) }, [h("span.bars__pos", i + 1), h("span.bars__n", T(r[1]).short), h("span.bars__bar", h("i", { style: { width: (r[12] / mx) * 100 + "%", animationDelay: 0.3 + i * 0.07 + "s" } })), h("span.bars__v", n(r[12]))]))))]);
  const right = h("div", [h("div.sec__head", [h("h2", "Goleadores"), h("a.link", { href: "#goleadores" }, "Ranking →")]), h("p.muted", "Goles en fase regular, sin los en contra."), h("ol.rank", S.scorers.slice(0, 8).map((o, i) => h("li", [h("span.rank__pos", i + 1), h("span.rank__n", [h("b", o.name), h("small", T(o.teamList[0]).short)]), h("span.rank__v", o.goals)])))]);
  page.append(h("div.wrap", h("section.sec.cols2", [left, right])));
  page.append(h("div.wrap", h("section.sec.tiles", [["#fotos", "Fotos", "Imágenes de la categoría, con autor y licencia."], ["#videos", "Videos", "Finales y festejos, para ver en YouTube."], ["#ascensos", "Ascensos", "Los 97 que subieron, año por año."]].map(([to, t, d]) => h("a.tile", { href: to }, [h("b", t), h("span", d)])))));
  return { page, title: "" };
});
