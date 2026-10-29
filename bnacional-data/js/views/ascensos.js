import { route } from "../app.js";
import { S, search } from "../store.js";
import { h, norm, n } from "../util.js";
import { ascCard, head, T, photoFor, monogram, openCard, href } from "./common.js";
import { imgSrc } from "../util.js";

const st = { how: "todos", q: "" };
route("ascensos", async () => {
  const page = h("div.wrap.page"), grid = h("div.stack");
  const tabs = h("div.chips", ["todos", "Campeón", "Ascenso"].map((k) => h("button.chip", { type: "button", "aria-pressed": String(st.how === k), onclick: (e) => { st.how = k; tabs.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", String(c === e.currentTarget))); draw(); } }, k === "todos" ? "Todos" : k === "Campeón" ? "Campeones" : "Segundo ascenso y reducidos")));
  const q = h("input#ascq", { type: "search", placeholder: "Filtrar por club", value: st.q, "aria-label": "Filtrar por club", oninput: (e) => { st.q = e.target.value; draw(); } });
  const draw = () => {
    const f = norm(st.q), bySeason = new Map();
    for (const a of S.ascensos) { if (st.how !== "todos" && a.how !== st.how) continue; if (f && !norm(T(a.t).n).includes(f)) continue; if (!bySeason.has(a.si)) bySeason.set(a.si, []); bySeason.get(a.si).push(a); }
    const keys = [...bySeason.keys()].sort((a, b) => b - a);
    grid.replaceChildren(...(keys.length ? keys.map((si) => h("section.yr", [h("h3", [S.seasons[si].label, h("small", ` ${bySeason.get(si).length} ${bySeason.get(si).length === 1 ? "club" : "clubes"}`)]), h("div.agrid", bySeason.get(si).map((a) => ascCard(a)))])) : [h("p.muted", "No hay ascensos con ese filtro.")]));
  };
  draw();
  // visor: recorre los 97 ascensos con una barra de tiempo
  const list = S.ascensos, N = list.length;
  let cur = N - 1, timer = null;
  const media = h("div.viewer__img"), info = h("div.viewer__info");
  const slider = h("input#asc-s", { type: "range", min: 0, max: N - 1, value: cur, "aria-label": "Ascenso" });
  const play = h("button.iconbtn", { type: "button", "aria-label": "Recorrer la historia" }, "▶");
  const show = (i) => {
    cur = i; slider.value = i; slider.style.setProperty("--v", (i / (N - 1)) * 100 + "%");
    const a = list[i], t = T(a.t), ph = photoFor(a), champ = a.how === "Campeón";
    const cr = S.crest(a.t);
    media.replaceChildren(...[cr ? h("div.acard__crest", h("img", { src: imgSrc(cr.img), alt: "Escudo de " + t.short })) : monogram(a.t), ph ? h("img.viewer__thumb", { src: imgSrc(ph.img), alt: ph.alt || t.n, title: ph.caption || "" }) : null].filter(Boolean));
    info.replaceChildren(...[h("span.pill" + (champ ? ".pill--champ" : ""), champ ? "Campeón y ascenso" : "Ascenso a Primera"), h("div.big", a.season.label.replace("Transición ", "T ")), h("h3", t.n), ph ? h("p.viewer__cap", (ph.kind === "temporada" ? "Foto de la temporada: " : "Foto del club: ") + ph.caption) : null,
      h("div.lb__links", [h("button.btn", { type: "button", onclick: () => openCard(a) }, "Ver en grande"), h("a.btn.btn--ghost", { href: href.club(a.t) }, "Historia del club")])].filter(Boolean));
  };
  const stop = () => { clearInterval(timer); timer = null; play.textContent = "▶"; };
  play.addEventListener("click", () => { if (timer) return stop(); if (cur >= N - 1) show(0); play.textContent = "❚❚"; timer = setInterval(() => { if (!media.isConnected || cur >= N - 1) return stop(); show(cur + 1); }, 2200); });
  slider.addEventListener("input", () => { stop(); show(Number(slider.value)); });
  const first = list[0].season.label, lastL = list[N - 1].season.label;
  const viewer = h("section", { "aria-label": "Recorrido por los ascensos" }, [h("div.viewer", [media, info]), h("div.timeline", [h("div.timeline__row", [play, slider]), h("div.timeline__ticks", [h("span", first), h("span", "2000"), h("span", "2010"), h("span", "2020"), h("span", lastL)])])]);
  show(cur);
  const withPhoto = S.ascensos.filter((a) => S.photo(a.key) || S.clubPhoto(T(a.t).s)).length;
  page.append(head("Ascensos", "Los clubes que subieron a Primera", `${S.ascensos.length} ascensos desde 1986/87. Cada ascenso tiene su escudo como carátula; la foto libre de Wikimedia Commons es un complemento (${withPhoto} de ${S.ascensos.length} tienen una). Fuente de las listas: Wikipedia.`), viewer, h("h2", { style: { marginTop: "46px" } }, "Todos los ascensos"), h("div.toolbar", [tabs, q]), grid);
  return { page, title: "Ascensos" };
});
