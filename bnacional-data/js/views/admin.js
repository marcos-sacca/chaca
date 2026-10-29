import { route } from "../app.js";
import { S, getLocal, setLocal, emptyDelta, mergeResources, pkey, hasLocal } from "../store.js";
import { h, imgSrc } from "../util.js";
import { head, sec, T, crest } from "./common.js";

const TIPOS = [["goles", "Compilado de goles"], ["final", "Final, festejo o ascenso"], ["partido", "Partido de archivo"]];
const clubName = (slug) => (slug === "general" ? "General (sin club)" : S.teamBy.has(slug) ? T(S.teamBy.get(slug)).n : slug);

// "https://youtu.be/xxxx", "https://www.youtube.com/watch?v=xxxx" o el id suelto
const ytId = (s) => { s = (s || "").trim(); const m = /(?:v=|youtu\.be\/|embed\/|shorts\/)([\w-]{11})/.exec(s) || /^([\w-]{11})$/.exec(s); return m ? m[1] : null; };

// achica la foto antes de guardarla en el navegador
function resize(file, max = 1000) {
  return new Promise((ok, no) => {
    const url = URL.createObjectURL(file), im = new Image();
    im.onload = () => { const k = Math.min(1, max / Math.max(im.width, im.height)), c = document.createElement("canvas"); c.width = Math.round(im.width * k); c.height = Math.round(im.height * k); c.getContext("2d").drawImage(im, 0, 0, c.width, c.height); URL.revokeObjectURL(url); ok(c.toDataURL("image/jpeg", 0.82)); };
    im.onerror = () => { URL.revokeObjectURL(url); no(new Error("No pude leer esa imagen.")); };
    im.src = url;
  });
}
async function saveFile(filename, text) {
  try { const dl = await window.claude?.use?.("downloads"); if (dl) { await dl.save({ filename, data: text }); return; } } catch (e) { if (e && e.code === "declined") return; }
  const a = h("a", { href: URL.createObjectURL(new Blob([text], { type: "application/json" })), download: filename }); document.body.append(a); a.click(); a.remove();
}
// lo que queda para publicar: data/extra.json + cambios locales, sin lo que se sacó
function exportable() {
  const ex = S.extra || emptyDelta(), lo = getLocal();
  const hideP = new Set([...(ex.ocultos?.fotos || []), ...lo.ocultos.fotos]), hideV = new Set([...(ex.ocultos?.videos || []), ...lo.ocultos.videos]);
  const baseP = new Set([...Object.values(S._base.clubs).flat(), ...S._base.general].map(pkey)), baseV = new Set(S._base.videos.map((v) => v.id));
  const clean = (L) => L.map((p) => { const q = { ...p }; delete q._src; return q; });
  return { version: 1, fotos: clean([...(ex.fotos || []), ...lo.fotos].filter((p) => !hideP.has(pkey(p)))), videos: clean([...(ex.videos || []), ...lo.videos].filter((v) => !hideV.has(v.id))), ocultos: { fotos: [...hideP].filter((k) => baseP.has(k)), videos: [...hideV].filter((k) => baseV.has(k)) } };
}

route("admin", async () => {
  const page = h("div.wrap.page"), body = h("div"), msg = h("p.adm__msg", { role: "status" });
  let tab = "fotos";
  const say = (t, bad) => { msg.textContent = t; msg.classList.toggle("is-bad", !!bad); };
  const clubOpts = (withGeneral) => [withGeneral ? h("option", { value: "general" }, "General (sin club)") : null, ...S.teams.map((t) => ({ t, n: t.short })).sort((a, b) => a.n.localeCompare(b.n)).map(({ t }) => h("option", { value: t.s }, t.n))].filter(Boolean);
  const bad = (e) => say(e.message || String(e), true);
  const put = (fn) => { const d = getLocal(); fn(d); if (!setLocal(d)) return say("No pude guardar en este navegador (¿modo privado o sin espacio?).", true); draw(); };

  const photoForm = () => {
    const club = h("select#a-club", clubOpts(true)), file = h("input", { type: "file", accept: "image/*" }), url = h("input", { type: "url", placeholder: "…o la dirección de una imagen (https://…)" });
    const cap = h("input", { type: "text", placeholder: "Qué se ve (ej. Plantel campeón 1992/93)" }), au = h("input", { type: "text", placeholder: "Autor o quién la aportó" }), lic = h("input", { type: "text", placeholder: "Licencia o permiso (ej. CC BY-SA 4.0, la mandó un hincha)" }), src = h("input", { type: "url", placeholder: "Link de origen (opcional)" });
    return h("form.adm__form", { onsubmit: async (e) => {
      e.preventDefault();
      try {
        let img = url.value.trim(); if (file.files[0]) img = await resize(file.files[0]); if (!img) throw new Error("Subí una imagen o pegá su dirección.");
        if (!cap.value.trim()) throw new Error("Poné una descripción.");
        put((d) => d.fotos.push({ id: "f" + Date.now().toString(36), club: club.value, img, caption: cap.value.trim(), alt: cap.value.trim(), author: au.value.trim(), lic: lic.value.trim() || "Aportada por la comunidad", page: src.value.trim() || "", kind: "club" }));
        say("Foto agregada. Está en este navegador; exportá el archivo para publicarla.");
      } catch (er) { bad(er); }
    } }, [h("label", ["Club", club]), h("label", ["Imagen", file]), url, cap, au, lic, src, h("button.btn", { type: "submit" }, "Agregar foto")]);
  };
  const videoForm = () => {
    const club = h("select#a-vclub", [h("option", { value: "" }, "Sin club"), ...clubOpts(false)]), tipo = h("select", TIPOS.map(([v, l]) => h("option", { value: v }, l)));
    const link = h("input", { type: "text", placeholder: "Link de YouTube" }), tit = h("input", { type: "text", placeholder: "Título" }), year = h("input", { type: "text", placeholder: "Año o temporada" });
    return h("form.adm__form", { onsubmit: (e) => {
      e.preventDefault(); const id = ytId(link.value);
      if (!id) return say("No entendí ese link de YouTube.", true);
      if (!tit.value.trim()) return say("Poné un título.", true);
      put((d) => d.videos.push({ id, title: tit.value.trim(), year: year.value.trim(), tipo: tipo.value, club: club.value || undefined }));
      say("Video agregado. Exportá el archivo para publicarlo.");
    } }, [h("label", ["Club", club]), h("label", ["Tipo", tipo]), link, tit, year, h("button.btn", { type: "submit" }, "Agregar video")]);
  };

  const mark = (src) => (src === "local" ? h("span.adm__tag.is-new", "Nueva (sin publicar)") : src === "extra" ? h("span.adm__tag", "Publicada") : h("span.adm__tag.is-base", "De la base"));
  const removeP = (p, src) => put((d) => { if (src === "local") d.fotos = d.fotos.filter((x) => pkey(x) !== pkey(p)); else d.ocultos.fotos.push(pkey(p)); });
  const removeV = (v, src) => put((d) => { if (src === "local") d.videos = d.videos.filter((x) => x.id !== v.id); else d.ocultos.videos.push(v.id); });

  const hiddenList = () => {
    const ex = S.extra || emptyDelta(), lo = getLocal(), hp = [...new Set([...(ex.ocultos?.fotos || []), ...lo.ocultos.fotos])], hv = [...new Set([...(ex.ocultos?.videos || []), ...lo.ocultos.videos])];
    if (!hp.length && !hv.length) return null;
    const baseP = [...Object.entries(S._base.clubs).flatMap(([c, L]) => L.map((p) => ({ ...p, club: c }))), ...S._base.general.map((p) => ({ ...p, club: "general" }))], baseV = S._base.videos;
    return sec("Sacados", [h("p.muted", "Estos recursos ya no se muestran. Podés devolverlos."), h("ul.adm__list", [
      ...hp.map((k) => { const p = baseP.find((x) => pkey(x) === k); return p ? h("li", [h("img", { src: imgSrc(p.img), alt: "" }), h("span", [h("b", clubName(p.club)), p.caption]), h("button.btn.btn--ghost", { type: "button", onclick: () => put((d) => { d.ocultos.fotos = d.ocultos.fotos.filter((x) => x !== k); if ((S.extra.ocultos?.fotos || []).includes(k)) say("Este está sacado en data/extra.json; para devolverlo editá ese archivo.", true); }) }, "Devolver")]) : null; }),
      ...hv.map((id) => { const v = baseV.find((x) => x.id === id); return v ? h("li", [h("span", [h("b", "Video"), v.title]), h("button.btn.btn--ghost", { type: "button", onclick: () => put((d) => { d.ocultos.videos = d.ocultos.videos.filter((x) => x !== id); }) }, "Devolver")]) : null; }),
    ].filter(Boolean))]);
  };

  function draw() {
    const nloc = getLocal();
    const tabs = h("div.chips", [["fotos", "Fotos"], ["videos", "Videos"]].map(([k, l]) => h("button.chip", { type: "button", "aria-pressed": String(tab === k), onclick: () => { tab = k; say(""); draw(); } }, l)));
    const items = [];
    if (tab === "fotos") {
      const all = [...Object.entries(S.galeria.clubs).map(([c, L]) => [c, L]), ["general", S.galeria.general]].filter(([, L]) => L.length).sort((a, b) => clubName(a[0]).localeCompare(clubName(b[0])));
      for (const [c, L] of all) items.push(h("section.adm__club", [h("h3", [S.teamBy.has(c) ? crest(S.teamBy.get(c)) : null, clubName(c), h("small", ` ${L.length}`)]), h("ul.adm__list", L.map((p) => h("li", [h("img", { src: imgSrc(p.img), alt: "", loading: "lazy" }), h("span", [mark(p._src), p.caption]), h("button.btn.btn--ghost.btn--danger", { type: "button", onclick: () => removeP(p, p._src) }, "Sacar")])))]));
    } else {
      items.push(h("ul.adm__list", S.videos.map((v) => h("li", [h("img", { src: imgSrc(`assets/img/videos/${v.id}.jpg`), alt: "", loading: "lazy", onerror: (e) => { e.target.style.visibility = "hidden"; } }), h("span", [mark(v._src), h("b", v.title), ` ${v.year || ""}${v.club && S.teamBy.has(v.club) ? " · " + T(S.teamBy.get(v.club)).short : ""}`]), h("button.btn.btn--ghost.btn--danger", { type: "button", onclick: () => removeV(v, v._src) }, "Sacar")]))));
    }
    const changed = hasLocal();
    body.replaceChildren(
      h("div.adm__bar", [
        h("p", changed ? "Tenés cambios en este navegador que todavía no están publicados." : "No hay cambios sin publicar."),
        h("div.adm__btns", [
          h("button.btn", { type: "button", disabled: !changed, onclick: () => saveFile("extra.json", JSON.stringify(exportable(), null, 1)).then(() => say("Archivo listo. Reemplazá data/extra.json del repositorio con ese archivo y subilo.")).catch(bad) }, "Exportar para publicar"),
          h("label.btn.btn--ghost", ["Importar cambios", h("input", { type: "file", accept: "application/json", hidden: true, onchange: async (e) => { try { const j = JSON.parse(await e.target.files[0].text()); const d = { ...emptyDelta(), ...j, ocultos: { fotos: [], videos: [], ...(j.ocultos || {}) } }; setLocal(d); say("Importado."); draw(); } catch (er) { bad(er); } } })]),
          h("button.btn.btn--ghost.btn--danger", { type: "button", disabled: !changed, onclick: () => { if (confirm("¿Descartar todos los cambios de este navegador?")) { setLocal(emptyDelta()); say("Cambios descartados."); draw(); } } }, "Descartar cambios"),
        ]),
      ]),
      tabs, tab === "fotos" ? photoForm() : videoForm(), hiddenList(), h("h2", { style: { marginTop: "34px" } }, tab === "fotos" ? "Fotos de la galería" : "Videos"), ...items);
  }
  page.append(head("Administración", "Recursos de la galería", "Agregá o sacá fotos y videos. Los cambios se ven enseguida acá y se guardan en este navegador; para publicarlos, exportá el archivo y reemplazá data/extra.json del repositorio. No hace falta ninguna contraseña porque nada se publica solo."), msg, body);
  draw();
  return { page, title: "Administración" };
});
