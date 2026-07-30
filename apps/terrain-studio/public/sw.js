/* Terrain Studio service worker.
 *
 * WHY IT LIVES IN public/ AND NOT src/. Vite emits nothing from src/ except what the module graph
 * imports, so a worker registered at ./src/pwa/sw.js 404s under `vite preview` and the PWA gate
 * fails with no code to blame. public/ is copied verbatim to the dist root, which also gives the
 * worker ROOT SCOPE - required, because a worker served from /assets/ can only control /assets/.
 * It must also keep a stable URL: bundling it to sw-<hash>.js would make every build look like a
 * different worker and break the update model outright.
 *
 * THE PRECACHE LIST IS INJECTED AT BUILD TIME. Asset names are content-hashed, so this file cannot
 * know them; the sw-precache plugin in vite.config.ts rewrites the two placeholder tokens on the
 * lines below, after the bundle exists. Do not repeat those tokens anywhere else in this file: the
 * substitution is a plain string replace, so a second occurrence in prose would consume the
 * rewrite and leave the code untouched. (That is not hypothetical - this comment used to name
 * them, the comment got substituted, and the plugin's own assertion caught it.)
 * In dev they stay as-is and the worker is never registered anyway (see legacy.js -
 * registration is behind import.meta.env.PROD, so a developer's browser never cache-firsts a dev
 * shell).
 *
 * STRATEGY. Cache-first for the app shell, because the shell is immutable per build: every asset
 * name carries a content hash, so a cached hit is by definition the right bytes. index.html is the
 * one mutable name, so it is network-first with a cache fallback - that is what lets a new build be
 * discovered while still working offline.
 */
const VERSION = '__VERSION__';
const CACHE = `terrain-studio-${VERSION}`;
const PRECACHE = __PRECACHE__;

self.addEventListener('install', (e) => {
  e.waitUntil((async () => {
    const c = await caches.open(CACHE);
    // Individually, not addAll: addAll is atomic, so one 404 discards the whole precache and the
    // app silently has no offline mode. A missing asset should cost that asset, not the feature.
    await Promise.all(PRECACHE.map((u) => c.add(u).catch(() => {})));
    // Take over immediately. Without this a new build sits "waiting" until every tab closes, and
    // for a single-tab tool that reads as "the update never arrived".
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', (e) => {
  e.waitUntil((async () => {
    // Drop every cache from a previous build. The version is the build hash, so this is exact
    // rather than a heuristic on names.
    const keys = await caches.keys();
    await Promise.all(keys.filter((k) => k.startsWith('terrain-studio-') && k !== CACHE)
      .map((k) => caches.delete(k)));
    await self.clients.claim();
  })());
});

self.addEventListener('fetch', (e) => {
  const req = e.request;
  // Only GET, only same-origin, and never the range requests a media element issues - a partial
  // response cached as if it were whole is a corruption that survives reloads.
  if (req.method !== 'GET' || req.headers.has('range')) return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  const isDocument = req.mode === 'navigate' || url.pathname.endsWith('/index.html');

  if (isDocument) {
    // Network-first: index.html is the only name that does not change between builds, so it is the
    // only way a client can learn that a new bundle exists.
    e.respondWith((async () => {
      try {
        const fresh = await fetch(req);
        const c = await caches.open(CACHE);
        c.put(req, fresh.clone());
        return fresh;
      } catch (_) {
        const hit = await caches.match(req) || await caches.match('index.html');
        if (hit) return hit;
        return new Response('Terrain Studio is offline and has no cached copy of this page.',
          { status: 503, headers: { 'content-type': 'text/plain' } });
      }
    })());
    return;
  }

  // Everything else is content-hashed, so a cache hit is provably the right bytes.
  e.respondWith((async () => {
    const hit = await caches.match(req);
    if (hit) return hit;
    const res = await fetch(req);
    if (res.ok && res.type === 'basic') {
      const c = await caches.open(CACHE);
      c.put(req, res.clone());
    }
    return res;
  })());
});
