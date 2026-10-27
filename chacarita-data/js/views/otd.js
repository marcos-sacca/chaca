import { route } from "../app.js";
import { S, onDay } from "../store.js";
import { h, n, MESES, resChip, dShort, dLong } from "../util.js";
import { href, field, select, pageHead, matchRow, setQuery } from "./common.js";

const ROUND = [25, 50, 75, 100];
const dim = (m) => [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1];

route("efemerides", (r, page) => {
  const now = new Date();
  let [mm, dd] = (r.arg || `${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`).split("-").map(Number);
  const out = h("div");
  const year = now.getFullYear();
  const draw = () => {
    dd = Math.min(dd, dim(mm));
    const md = `${String(mm).padStart(2, "0")}-${String(dd).padStart(2, "0")}`;
    history.replaceState(null, "", `#/efemerides/${md}`);
    const list = onDay(md);
    const round = S.matches.filter((m) => ROUND.includes(year - m.y)).sort((a, b) => a.md.localeCompare(b.md));
    const upcoming = round.filter((m) => m.md >= md).concat(round.filter((m) => m.md < md));
    out.replaceChildren(
      h("section.sec", { style: { marginTop: "6px" } }, [
        h("h2", `${dd} de ${MESES[mm - 1]}`),
        list.length ? [h("p.muted", { style: { margin: "6px 0 14px" } }, `${list.length} ${list.length === 1 ? "partido" : "partidos"} en ${list.length === 1 ? "esa fecha" : "esa fecha, en distintos años"}.`), h("div.mlist", list.map((m) => { const row = matchRow(m); row.querySelector(".m__d").textContent = m.y; row.querySelector(".m__t small").append(` · hace ${year - m.y} años`); return row; }))] : h("p.muted", { style: { marginTop: "10px" } }, "Chacarita no jugó partidos oficiales un día como ese. Probá con el día anterior o el siguiente."),
      ]),
      upcoming.length ? h("section.sec", { "data-reveal": "" }, [
        h("div.sec__head", [h("h2", `Aniversarios redondos de ${year}`)]),
        h("p.muted", { style: { margin: "0 0 14px" } }, "Partidos que este año cumplen 25, 50, 75 o 100 años, empezando por el más cercano a la fecha elegida."),
        h("div.mlist", upcoming.slice(0, 24).map((m) => { const row = matchRow(m); row.querySelector(".m__d").textContent = `${String(+m.md.slice(3)).padStart(2, "0")}/${m.md.slice(0, 2)}`; row.querySelector(".m__t small").append(h("span.mark", `${year - m.y} años`)); return row; })),
        upcoming.length > 24 ? h("p.cap", `Se muestran 24 de ${upcoming.length}.`) : null,
      ]) : null,
    );
  };
  const mSel = select("em", MESES.map((m, i) => [i + 1, m[0].toUpperCase() + m.slice(1)]), mm, (v) => { mm = +v; draw(); });
  const dSel = select("ed", Array.from({ length: 31 }, (_, i) => [i + 1, i + 1]), dd, (v) => { dd = +v; draw(); }, { cls: "in--sm" });
  const shift = (k) => { const dt = new Date(2024, mm - 1, dd + k); mm = dt.getMonth() + 1; dd = dt.getDate(); mSel.value = mm; dSel.value = dd; draw(); };
  page.append(h("div.wrap.page", [
    pageHead("Efemérides", "Un día como hoy", "Elegí una fecha y mirá todo lo que Chacarita jugó ese día a lo largo de los años."),
    h("div.filters", [field("Mes", mSel, "em"), field("Día", dSel, "ed"), h("button.btn.btn--ghost.btn--sm", { type: "button", style: { alignSelf: "end", marginBottom: "4px" }, onclick: () => shift(-1) }, "← Día anterior"), h("button.btn.btn--ghost.btn--sm", { type: "button", style: { alignSelf: "end", marginBottom: "4px" }, onclick: () => shift(1) }, "Día siguiente →"), h("button.btn.btn--sm", { type: "button", style: { alignSelf: "end", marginBottom: "4px" }, onclick: () => { mm = now.getMonth() + 1; dd = now.getDate(); mSel.value = mm; dSel.value = dd; draw(); } }, "Hoy")]),
    out,
  ]));
  draw();
  return { title: "Efemérides" };
});
