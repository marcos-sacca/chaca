import { h, dShort, dLong, resChip, n, pct, signed } from "../util.js";
import { S, score, sum } from "../store.js";

export const href = {
  rival: (r) => `#/rivales/${encodeURIComponent(r)}`,
  player: (p) => `#/jugadores/${encodeURIComponent(p)}`,
  season: (s) => `#/temporadas/${encodeURIComponent(s)}`,
  match: (m) => `#/partido/${m.id}`,
};

const scorers = (m) => {
  const c = new Map(); m.g.forEach((g) => { if (g.p && !g.ec) c.set(g.p, (c.get(g.p) || 0) + 1); });
  const l = [...c].map(([p, k]) => (k > 1 ? `${p} (${k})` : p));
  return l.slice(0, 3).join(", ") + (l.length > 3 ? "…" : "");
};

/** Fila de partido: fecha · equipos y torneo · marcador · resultado. */
export function matchRow(m, { rival = false } = {}) {
  const me = (name) => (name === "Chacarita" ? h("b", name) : name);
  return h("a.m", { href: href.match(m) }, [
    h("span.m__d", dShort(m.d)),
    h("span.m__t", [h("span", [me(m.l), " – ", me(m.v)]), h("small", [m.tn, m.j != null && m.j !== "" ? ` · ${typeof m.j === "number" || /^\d+$/.test(String(m.j)) ? "fecha " : ""}${m.j}` : "", m.g && m.g.length ? ` · ${scorers(m)}` : ""])]),
    h("span.m__s.num", [m.gl ?? "?", h("span", "-"), m.gv ?? "?", m.pen ? h("small.muted", ` (${m.pen[0]}-${m.pen[1]})`) : null]),
    resChip(m.res),
  ]);
}

export function matchList(list, { limit = 10 } = {}) {
  return h("div.mlist", list.slice(0, limit).map((m) => matchRow(m)));
}

export function figure(src, alt, credit, { cls = "" } = {}) {
  const c = IMG[credit] || {};
  return h(`figure${cls ? "." + cls : ""}`, [
    h("img", { src, alt, loading: "lazy", decoding: "async" }),
    c.title ? h("figcaption.cap", [c.caption || c.title, " — ", c.author ? `${c.author}, ` : "", h("a", { href: c.page, target: "_blank", rel: "noopener" }, c.lic || "Wikimedia Commons")]) : null,
  ]);
}

// Créditos (se completan desde assets/img/credits.json al cargar)
export const IMG = {};
export async function loadCredits() {
  try { Object.assign(IMG, await (await fetch("assets/img/credits.json")).json()); } catch { /* sin créditos: las imágenes igual se muestran */ }
}

export const kpi = (k, v, d) => h("div.rec", [h("span.rec__k", k), h("span.rec__v", v), d ? h("span.rec__d", d) : null]);

export function rowsTable(cols, rows, { cls = "" } = {}) {
  return h("div.tblwrap", h("table.tbl" + (cls ? "." + cls : ""), [
    h("thead", h("tr", cols.map((c) => h("th" + (c.r ? ".r" : ""), c.t)))),
    h("tbody", rows.map((r) => h("tr", r.map((cell, i) => h("td" + (cols[i].r ? ".r" : ""), cell))))),
  ]));
}

/** Campo con etiqueta + control. */
export const field = (label, control, id) => h("div.field", [h("label", { for: id }, label), control]);
export function select(id, options, value, onchange, { cls = "" } = {}) {
  const el = h("select.in" + (cls ? "." + cls : ""), { id }, options.map(([v, t]) => h("option", { value: v, selected: String(v) === String(value ?? "") }, t)));
  el.addEventListener("change", () => onchange(el.value));
  return el;
}
/** Botones excluyentes (una sola opción activa). */
export function segmented(options, value, onchange, label) {
  const box = h("div.seg", { role: "group", "aria-label": label });
  const set = (v) => box.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.v === String(v))));
  options.forEach(([v, t]) => box.append(h("button", { type: "button", "data-v": v, "aria-pressed": String(String(v) === String(value)), onclick: () => { set(v); onchange(v); } }, t)));
  return box;
}

/** Tabla ordenable. cols: [{t, v(row)->valor de orden, f(row)->celda (opcional), r:alineada a la derecha, desc:orden inicial descendente}] */
export function sortTable(cols, rows, { sort = 0, dir, limit = 25, rowHref, empty = "Sin resultados" } = {}) {
  let ci = sort, d = dir ?? (cols[sort].desc ? -1 : 1), shown = limit;
  const wrap = h("div");
  const draw = () => {
    const get = cols[ci].v;
    const list = rows.slice().sort((a, b) => {
      const x = get(a), y = get(b);
      if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;
      return (typeof x === "string" ? x.localeCompare(y, "es") : x - y) * d;
    });
    const head = h("tr", cols.map((c, i) => h("th.sortable" + (c.r ? ".r" : ""), {
      scope: "col", tabindex: 0, "aria-sort": i === ci ? (d > 0 ? "ascending" : "descending") : null,
      onclick: () => { if (ci === i) d = -d; else { ci = i; d = c.desc ? -1 : 1; } draw(); },
      onkeydown: (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); e.currentTarget.click(); } },
    }, c.t)));
    const body = list.slice(0, shown).map((r) => {
      const tr = h("tr" + (rowHref ? ".link-row" : ""), cols.map((c, i) => h("td" + (c.r ? ".r" : "") + (c.wrap ? ".wrapcell" : ""), c.f ? c.f(r) : c.v(r) ?? "—")));
      if (rowHref) tr.addEventListener("click", (e) => { if (!e.target.closest("a")) location.hash = rowHref(r); });
      return tr;
    });
    wrap.replaceChildren(
      list.length ? h("div.tblwrap", h("table.tbl", [h("thead", head), h("tbody", body)])) : h("p.muted", empty),
      list.length > shown ? h("div", { style: { marginTop: "14px" } }, h("button.btn.btn--ghost", { type: "button", onclick: () => { shown += limit; draw(); } }, `Mostrar más (${list.length - shown} restantes)`)) : null,
    );
  };
  draw();
  return wrap;
}

/** Lista de partidos con filtro por resultado y "mostrar más". */
export function matchBrowser(list, { limit = 15, order = -1 } = {}) {
  let res = "", shown = limit;
  const box = h("div"), out = h("div");
  const draw = () => {
    const l = list.filter((m) => !res || m.res === res).slice().sort((a, b) => order * (a.d.localeCompare(b.d) || a.id - b.id));
    out.replaceChildren(
      h("div.mlist", l.slice(0, shown).map((m) => matchRow(m))),
      l.length > shown ? h("div.pager", [h("button.btn.btn--ghost", { type: "button", onclick: () => { shown += limit * 2; draw(); } }, `Mostrar más (${l.length - shown} restantes)`)]) : null,
      !l.length ? h("p.muted", "No hay partidos con ese resultado.") : null,
    );
  };
  box.append(h("div.filters", segmented([["", `Todos (${list.length})`], ["G", "Ganó"], ["E", "Empató"], ["P", "Perdió"]], "", (v) => { res = v; shown = limit; draw(); }, "Resultado")), out);
  draw();
  return box;
}

/** Cambia el hash sin disparar la navegación (para filtros). */
export function setQuery(path, q) {
  const qs = new URLSearchParams(Object.entries(q).filter(([, v]) => v !== "" && v != null)).toString();
  history.replaceState(null, "", `#/${path}${qs ? "?" + qs : ""}`);
}

export const statRow = (items) => h("div.stats", items.map(([k, v, d]) => h("div.stat", [h("span.stat__k", k), h("span.stat__v.num", String(v)), d ? h("span.stat__d", d) : null])));
export const pageHead = (kicker, title, sub) => h("header.phead", [kicker ? h("p.eyebrow", kicker) : null, h("h1.h1", title), sub ? h("p.lead", sub) : null]);
export const crumbs = (...items) => h("nav.crumbs", { "aria-label": "Ruta" }, items.flatMap((it, i) => [i ? h("span", "›") : null, it.href ? h("a", { href: it.href }, it.t) : h("span", it.t)]));

export { dShort, dLong, resChip, n, pct, signed, score, sum };
