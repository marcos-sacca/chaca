import { route } from "../app.js";
import { S, sum } from "../store.js";
import { h, n, pct, dLong } from "../util.js";
import { pageHead, loadCredits, IMG, rowsTable } from "./common.js";

route("datos", async (r, page) => {
  await loadCredits();
  const M = S.matches, m = S.meta;
  let P = null; try { P = await (await fetch("data/enrichment/parche_partidos.json")).json(); } catch {}
  const ok = (k) => { const x = P.stats[k]; return pct(x.iguales / x.comparados, 0); };
  const decs = [...new Set(M.map((x) => x.dec))].sort();
  const cov = (f) => decs.map((d) => { const l = M.filter((x) => x.dec === d); return l.filter(f).length / l.length; });
  const camp = [["Resultado y goles", () => true], ["Goleadores", (x) => (x.gf + x.gc) === 0 || (x.g && x.g.length)], ["Formación", (x) => S.hasLineup.has(x.id)], ["Estadio", (x) => !!x.e], ["Árbitro", (x) => !!x.arb], ["Director técnico", (x) => !!x.dt], ["Espectadores", (x) => x.esp != null]];
  const heat = h("div.tblwrap", h("table.tbl.heat", [
    h("thead", h("tr", [h("th", "Dato"), ...decs.map((d) => h("th.r", `${d}s`))])),
    h("tbody", camp.map(([t, f]) => h("tr", [h("td", h("b", t)), ...cov(f).map((v) => { const td = h("td.c.r", pct(v, 0)); td.style.background = `color-mix(in srgb, var(--red) ${Math.round(v * 62)}%, var(--white))`; return td; })]))),
  ]));
  const fuentesPatch = P ? [...new Set(P.patch.map((x) => x.fuente.replace(/ p\.\d+$/, "")))].sort() : [];
  const imgs = Object.entries(IMG).filter(([, c]) => c.page);
  page.append(h("div.wrap.page", [
    pageHead("Datos", "De dónde sale cada cosa", "Todo parte de la planilla «DATACHACA Máster». Completamos lo que faltaba solo cuando una fuente pública lo confirmaba, y lo dejamos marcado."),
    h("section.sec", { style: { marginTop: "30px" } }, [h("h2", { style: { marginBottom: "12px" } }, "Qué tan completo está cada dato"), heat, h("p.cap", `Porcentaje de partidos de cada década que tiene el dato cargado. En total: ${n(m.partidos)} partidos, ${n(m.goles)} goles y ${n(m.formaciones)} apariciones en formaciones (${n(m.partidos_con_formacion)} partidos con formación).`)]),
    h("section.sec.cols2", { "data-reveal": "" }, [
      h("div", [h("h2", { style: { marginBottom: "12px" } }, "Lo que agregamos"), h("p", `Se completaron ${m.enriquecidos.arb} árbitros, ${m.enriquecidos.dt} directores técnicos y ${m.enriquecidos.esp} cifras de espectadores que estaban vacíos, y ${m.posiciones_completadas} posiciones finales de campeonatos. Cada dato agregado aparece con la marca «agregado» y la fuente al pasar el mouse.`), h("p", P ? `Antes de agregar algo se comparó el método con datos que la planilla ya tenía: coincidió en ${ok("Árbitro")} de los árbitros, ${ok("Espectadores")} de los espectadores y ${ok("DT")} de los directores técnicos. Si en una década la coincidencia era baja, no se agregó nada.` : "Antes de agregar algo se comparó el método con datos que la planilla ya tenía."), h("p.muted", "Nunca se pisó un dato existente.")]),
      h("div", [h("h2", { style: { marginBottom: "12px" } }, "Fuentes"), h("ul", { style: { paddingLeft: "1.1em", display: "grid", gap: "8px" } }, [
        h("li", [h("b", "Planilla DATACHACA Máster"), ": partidos, goles, formaciones y torneos (fuentes anotadas en la planilla)."]),
        h("li", [h("b", "Historical-Lineups"), " (formaciones, árbitros, recaudación y espectadores de 1932 a 1984): ", ...(fuentesPatch.length ? [fuentesPatch.length + " archivos usados."] : [])]),
        h("li", [h("b", "RSSSF"), " (tablas finales de los campeonatos de Primera)."]),
        h("li", [h("b", "Wikimedia Commons"), " (fotos, con autor y licencia debajo)."]),
      ])]),
    ]),
    h("section.sec", { "data-reveal": "" }, [h("h2", { style: { marginBottom: "12px" } }, "Cómo se calcula"), h("ul", { style: { paddingLeft: "1.1em", display: "grid", gap: "6px", maxWidth: "70ch" } }, [
      h("li", [h("b", "Efectividad"), " = (3 × ganados + empatados) ÷ (3 × jugados). Así se pueden comparar épocas aunque la victoria valiera 2 puntos hasta 1994/95."]),
      h("li", [h("b", "Rachas"), ": en orden de fecha entre todos los torneos; si dos empatan, se muestra la primera."]),
      h("li", [h("b", "Récords por temporada"), ": solo la competencia principal (sin copas) y con un mínimo de partidos."]),
      h("li", [h("b", "Goleador por partido"), " y «PJ»: solo cuentan los partidos con formación cargada."]),
    ])]),
    h("section.sec", { "data-reveal": "" }, [h("h2", { style: { marginBottom: "12px" } }, "Fotos y escudo"), h("ul", { style: { paddingLeft: "1.1em", display: "grid", gap: "6px" } }, imgs.map(([k, c]) => h("li", [c.caption || c.title, " — ", c.author ? c.author + ", " : "", h("a", { href: c.page, target: "_blank", rel: "noopener" }, c.lic)]))), h("div.row", { style: { marginTop: "20px", gap: "24px", alignItems: "center" } }, [h("img.shirt", { src: "assets/img/camiseta.svg", alt: "Ilustración de una camiseta de bastones rojos y negros", width: 280, height: 294 }), h("p.cap", { style: { maxWidth: "36ch" } }, "La camiseta es una ilustración propia de chacarita-data (bastones rojos y negros), no una imagen oficial del club.")]), h("p.cap", "chacarita-data es un proyecto de hinchas, sin vínculo oficial con el club.")]),
  ]));
  return { title: "Datos y fuentes" };
});
