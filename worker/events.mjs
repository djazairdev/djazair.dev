// Fixed, aggregate dimensions only. Never store request headers or arbitrary URLs.
export const events = ['landing_view','hub_view','meetups_view','task_browse','task_open','meetup_find','meetup_host','share_open','share_complete','share_copy'];
export const pages = ['home','hub','meetups'];
export const sections = ['hero','contribution-start','local-team','hub-teaser','other'];
export function validEvent(body) {
  if (!body || typeof body !== 'object' || Array.isArray(body)) return false;
  const keys = ['event','page','language','section','source','medium','campaign'];
  if (Object.keys(body).length !== keys.length || keys.some(k => typeof body[k] !== 'string')) return false;
  return events.includes(body.event) && pages.includes(body.page) && ['en','ar'].includes(body.language)
    && sections.includes(body.section)
    && ['source','medium','campaign'].every(k => /^[a-z0-9_-]{1,64}$/.test(body[k]));
}
function response(status) {
  return new Response(null, {status, headers:{'Cache-Control':'no-store','X-Content-Type-Options':'nosniff'}});
}
export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (url.pathname !== '/api/events') return env.ASSETS.fetch(request);
    if (request.method !== 'POST') return response(405);
    if (env.ACTION_ANALYTICS_ENABLED !== 'true' || !env.EVENTS) return response(503);
    if (request.headers.get('Origin') !== url.origin) return response(403);
    if (request.headers.get('DNT') === '1' || request.headers.get('Sec-GPC') === '1') return response(204);
    if (request.headers.get('Content-Type') !== 'application/json') return response(415);
    if (Number(request.headers.get('Content-Length')) > 1024) return response(413);
    // Bound reads even for a chunked body with no Content-Length.
    const reader = request.body?.getReader();
    if (!reader) return response(400);
    const chunks = []; let size = 0;
    for (;;) {
      const {value,done} = await reader.read();
      if (done) break;
      size += value.byteLength;
      if (size > 1024) { await reader.cancel(); return response(413); }
      chunks.push(value);
    }
    const bytes = new Uint8Array(size); let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk,offset); offset += chunk.length; }
    let body;
    try { body = JSON.parse(new TextDecoder().decode(bytes)); } catch { return response(400); }
    if (!validEvent(body)) return response(400);
    try {
      env.EVENTS.writeDataPoint({indexes:[body.campaign], doubles:[1],
        blobs:[body.event,body.page,body.language,body.section,body.source,body.medium,body.campaign]});
    } catch { return response(503); }
    return response(204);
  }
};
