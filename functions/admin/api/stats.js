// Estadísticas de tráfico para el panel (/admin/api/stats). La sesión ya la verificó functions/admin/_middleware.js.
// Lee Cloudflare Web Analytics por GraphQL. Necesita tres secretos del proyecto:
//   CF_ACCOUNT_ID, CF_SITE_TAG (el siteTag de Web Analytics) y CF_ANALYTICS_TOKEN (token con "Account Analytics: Read").
// Sin ellos responde {configured:false} y el panel muestra los pasos para activarlo.
const json = (o, status = 200) => new Response(JSON.stringify(o), { status, headers: { "Content-Type": "application/json" } });

export async function onRequestGet({ env, request }) {
  if (!env.CF_ANALYTICS_TOKEN || !env.CF_ACCOUNT_ID || !env.CF_SITE_TAG) return json({ configured: false });
  const days = Math.min(90, Math.max(1, +new URL(request.url).searchParams.get("days") || 30));
  const since = new Date(Date.now() - days * 864e5).toISOString();
  const f = `{siteTag: "${env.CF_SITE_TAG}", datetime_gt: "${since}"}`;
  const q = `query { viewer { accounts(filter: {accountTag: "${env.CF_ACCOUNT_ID}"}) {
    total: rumPageloadEventsAdaptiveGroups(limit: 1, filter: ${f}) { count sum { visits } }
    byDay: rumPageloadEventsAdaptiveGroups(limit: 100, filter: ${f}, orderBy: [date_ASC]) { count sum { visits } dimensions { date } }
    byCountry: rumPageloadEventsAdaptiveGroups(limit: 12, filter: ${f}, orderBy: [sum_visits_DESC]) { count sum { visits } dimensions { countryName } }
    byDevice: rumPageloadEventsAdaptiveGroups(limit: 6, filter: ${f}, orderBy: [sum_visits_DESC]) { count sum { visits } dimensions { deviceType } }
    byReferrer: rumPageloadEventsAdaptiveGroups(limit: 10, filter: ${f}, orderBy: [sum_visits_DESC]) { count sum { visits } dimensions { refererHost } }
  } } }`;
  try {
    const r = await fetch("https://api.cloudflare.com/client/v4/graphql", { method: "POST", headers: { Authorization: `Bearer ${env.CF_ANALYTICS_TOKEN}`, "Content-Type": "application/json" }, body: JSON.stringify({ query: q }) });
    const j = await r.json();
    if (j.errors?.length) return json({ configured: true, error: j.errors[0].message }, 502);
    const a = j.data.accounts[0], row = (g) => ({ visitas: g.sum.visits, paginas: g.count });
    return json({
      configured: true, days,
      total: a.total[0] ? row(a.total[0]) : { visitas: 0, paginas: 0 },
      porDia: a.byDay.map((g) => ({ fecha: g.dimensions.date, ...row(g) })),
      paises: a.byCountry.map((g) => ({ nombre: g.dimensions.countryName || "—", ...row(g) })),
      dispositivos: a.byDevice.map((g) => ({ nombre: g.dimensions.deviceType || "—", ...row(g) })),
      origen: a.byReferrer.map((g) => ({ nombre: g.dimensions.refererHost || "Directo", ...row(g) })),
    });
  } catch (e) { return json({ configured: true, error: "No se pudo consultar Cloudflare." }, 502); }
}
