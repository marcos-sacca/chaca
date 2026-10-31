// ficha de un partido: se abre en el diálogo #lightbox al tocar un resultado. Los datos por partido (cancha, goles,
// árbitro, síntesis de Solo Ascenso) están en data/partidos_info.json y se bajan recién la primera vez.
import { S } from "./store.js";
import { h, el$, mdate, imgSrc } from "./util.js";
import { T, href, crest } from "./views/common.js";
import { hrefH2H } from "./views/historial.js";

let INFO = null;
const load = () => (INFO ||= fetch("data/partidos_info.json").then((r) => r.json()).catch(() => ({ p: [], canchas: [], arbitros: [] })));

export async function openMatch(i) {
  const m = S.matches[i]; if (!m) return;
  const dlg = el$("lightbox"), body = el$("lightbody");
  const side = (t) => h("a.mt__team", { href: href.club(t), onclick: () => dlg.close() }, [crest(t), h("b", T(t).short)]);
  const headEl = h("div.mt__head", [side(m[4]), h("span.mt__score", `${m[6]} - ${m[7]}`), side(m[5])]);
  const meta = h("p.mt__meta", [S.seasons[m[0]].label, " · ", S.phases[m[1]], m[2] ? ` · fecha ${m[2]}` : "", mdate(m) ? ` · ${mdate(m)}` : ""]);
  const rest = h("div.mt__body", h("p.muted", "Cargando…"));
  body.replaceChildren(h("div.mt", [h("p.eyebrow", "Partido"), headEl, meta, rest]));
  if (!dlg.open) dlg.showModal();
  const info = await load(), x = info.p[i];
  if (!x) { rest.replaceChildren(h("p.muted", "No hay más datos de este partido.")); return; }
  const [ci, ai, obs, goals, sa] = x;
  const tipo = (k) => (k === 1 ? " (penal)" : k === 2 ? " (en contra)" : "");
  const col = (s) => h("ul.mt__goals", goals.filter((g) => g[0] === s).sort((a, b) => a[3] - b[3]).map((g) => h("li", [g[3] ? h("span.mt__min", `${g[3]}'`) : null, g[1] + tipo(g[2])])));
  const total = m[6] + m[7];
  rest.replaceChildren(...[
    total ? h("div.mt__gl", [col(0), col(1)]) : h("p.muted", "Terminó sin goles."),
    total && goals.length < total ? h("p.muted.mt__note", goals.length ? "La fuente no trae todos los goleadores de este partido." : "La fuente no trae los goleadores de este partido.") : null,
    h("dl.mt__dl", [ci >= 0 ? [h("dt", "Cancha"), h("dd", info.canchas[ci])] : null, ai >= 0 ? [h("dt", "Árbitro"), h("dd", info.arbitros[ai])] : null].flat().filter(Boolean)),
    obs ? h("p.mt__obs", obs) : null,
    h("div.lb__links", [h("a.btn", { href: hrefH2H(m[4], m[5]), onclick: () => dlg.close() }, "Historial entre los dos"),
      sa ? h("a.btn.btn--ghost", { href: `https://www.soloascenso.com.ar/sintesis/x/${sa}`, target: "_blank", rel: "noopener" }, "Síntesis en Solo Ascenso ↗") : null,
      h("a.btn.btn--ghost", { href: href.season(m[0]), onclick: () => dlg.close() }, `Temporada ${S.seasons[m[0]].label}`)].filter(Boolean)),
  ].filter(Boolean));
}
// botón con el resultado que abre la ficha
export const scoreBtn = (i, cls = "res__s") => { const m = S.matches[i]; return h("button." + cls + ".mt__btn", { type: "button", title: "Ver el partido", "aria-label": `Ver el partido ${T(m[4]).short} ${m[6]} - ${m[7]} ${T(m[5]).short}`, onclick: () => openMatch(i) }, `${m[6]} - ${m[7]}`); };
