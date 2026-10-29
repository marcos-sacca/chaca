import { route } from "../app.js";
import { S } from "../store.js";
import { h, n, fdate } from "../util.js";
import { head, sec } from "./common.js";

route("datos", async () => {
  const M = S.meta, page = h("div.wrap.page");
  page.append(head("Datos", "De dónde sale cada cosa", `Actualizado hasta el ${fdate(M.ultimo)}. ${n(M.partidos)} partidos y ${n(M.goles)} goles de ${M.temporadas} torneos.`));
  const li = (b, t) => h("li", [h("b", b), t]);
  page.append(sec("Fuentes", h("ul.plain", [
    li("Historia y Fútbol", " (José Carluccio, josecarluccio.blogspot.com): resultados, goleadores y sedes de 1986/87 a 2018/19."),
    li("Solo Ascenso", " (soloascenso.com.ar): resultados, goleadores y árbitros de 2017/18 en adelante; también controla 2014 a 2018/19."),
    li("RSSSF y Transfermarkt", ": segunda fuente para corregir marcadores que no cerraban con la tabla publicada."),
    li("Wikipedia", ": lista de clubes que ascendieron cada año y campeones."),
    li("Wikimedia Commons", ": las fotos, con su autor y licencia."),
    li("TheSportsDB y Wikipedia", ": los escudos. Son marcas de cada club y se muestran solo para identificarlo."),
  ])));
  page.append(sec("Cómo se controló", h("ul.plain", [
    li("Tablas: ", "cada tabla calculada se compara con la publicada. Hay unas 130 tablas de equipos que todavía no coinciden (sobre todo 1996/97 y los torneos de transición) y están marcadas en los archivos de datos."),
    li("Marcadores: ", "se cruzan con una segunda fuente. Si al corregir un marcador los puntos coinciden con la tabla oficial, se corrige y queda anotado."),
    li("Goleadores: ", "hasta 2018/19 los nombres traen la inicial del segundo nombre; desde 2017/18 vienen completos, por eso un jugador puede aparecer en dos filas."),
    li("Ascensos: ", "2026 sigue en disputa; el 2019/20 no tuvo ascensos por la pandemia; en la Transición 2014 subieron diez clubes porque Primera pasó de 20 a 30."),
  ])));
  page.append(sec("Fotos", h("p", "Las fotos vienen de Wikimedia Commons con licencia libre. Viven en la Galería, agrupadas por club (algunas son de una temporada puntual y otras del club en general); en los ascensos cada club se identifica solo con su escudo."), h("p.cap", `Fotos cargadas: ${new Set([...Object.values(S.fotos.entries || {}), ...Object.values(S.fotos.clubs || {}), ...(S.fotos.general || [])].map((p) => p.img)).size}.`)));
  const nc = Object.keys(S.crests || {}).length;
  page.append(sec("Escudos y planteles", h("p", `Hay escudo de ${nc} de ${M.clubes} clubes; los que faltan aparecen con sus iniciales. Los planteles de cada ascenso salen de las fichas de partido de Solo Ascenso (titulares y suplentes que entraron), por eso existen desde 2014; en los ascensos anteriores se muestran los goleadores del club en esa temporada.`)));
  page.append(sec("Actualizar", h("p", "Los datos se regeneran con un solo comando (python3 -I bnacional/tools/run.py) y el sitio con bnacional-data/tools/build_data.py. El repositorio explica cada paso.")));
  return { page, title: "Datos" };
});
