/* BOOT THE MAP CONSOLE IN A HIDDEN BROWSER PANE. Paste into the page console, then await it.
 *
 * ⭐ THIS RETIRES A LIMITATION THE DOCS CALLED PERMANENT. Every handoff since 2026-08-17 says
 * "the map does NOT boot headless -- verify by calling handler functions directly." That is true
 * but it is not the whole story, and the real cause is both narrower and fixable.
 *
 * THE CAUSE, measured 2026-08-19b. The pane is not headless, it is HIDDEN
 * (`document.visibilityState === "hidden"`), and Chrome PAUSES requestAnimationFrame in a hidden
 * document. MapLibre applies an inline style object inside `browser.frame()` -- a rAF callback --
 * so `Style._load` never runs, `map.style.sourceCaches` stays EMPTY, `load` never fires, and the
 * entire app.js boot chain behind `map.on("load")` never executes: no payloads, no layers, no
 * click bindings. Nothing errors. The console is silent. It looks like the app is broken.
 *
 * ⚠ DIAGNOSING IT IS THE HARD PART, so here is the fingerprint:
 *     map.style              -> truthy (the Style object exists)
 *     map.style.sourceCaches -> {}      (but it never loaded anything)
 *     map.isStyleLoaded()    -> false   (and stays false forever)
 *     document.hidden        -> true
 * ⛔ `map.redraw()` and `map.triggerRepaint()` DO NOT HELP -- they only schedule another rAF,
 * which is the thing that is paused. Pumping `map._render()` by hand does not help either: the
 * style was never applied, so there is nothing to render. Both were tried.
 *
 * THE FIX: replace rAF with a timer, then re-trigger the style load with `setStyle`. `load` has
 * not fired yet, so MapLibre fires it when the style finally lands -- and app.js's real handler,
 * registered at parse time, runs normally. Everything after that is the genuine application.
 *
 * ⚠ THIS IS A TEST HARNESS, NOT A SHIM. It is never loaded by a page. It changes nothing about
 * how the app behaves for a real user, whose document is visible and whose rAF runs. Do not
 * "fix" app.js against this -- there is no defect in app.js here.
 *
 *     const r = await bootMapHarness();   // { loadFired, nLayers, gz, ... }
 */
async function bootMapHarness(timeoutMs = 60000) {
  if (typeof map === "undefined") throw new Error("no `map` in scope - is this index.html?");

  // Already booted (visible pane, or a previous harness run): do not double-apply the style.
  if (map.isStyleLoaded && map.isStyleLoaded() && Object.keys(map.style.sourceCaches || {}).length) {
    return { alreadyBooted: true, nLayers: (map.getStyle().layers || []).length };
  }

  if (!window.__rafPatched) {
    window.__rafPatched = true;
    window.requestAnimationFrame = (cb) =>
      setTimeout(() => { try { cb(performance.now()); } catch (e) { console.error("raf cb", e); } }, 16);
  }

  let loadFired = false;
  map.on("load", () => { loadFired = true; });

  /* ⚠ Must MATCH app.js's own style block. If the basemap definition there changes and this does
     not, the harness boots a map the application would not have drawn -- a test that passes
     against a fiction. Keep them together. */
  map.setStyle({
    version: 8,
    glyphs: "https://fonts.openmaptiles.org/{fontstack}/{range}.pbf",
    sources: {
      basemap: {
        type: "raster",
        tiles: ["https://basemaps.cartocdn.com/light_all/{z}/{x}/{y}@2x.png"],
        tileSize: 256,
        attribution: "© OpenStreetMap contributors © CARTO",
      },
    },
    layers: [{ id: "basemap", type: "raster", source: "basemap" }],
  });

  const t0 = Date.now();
  while (Date.now() - t0 < timeoutMs) {
    await new Promise((r) => setTimeout(r, 250));
    if (loadFired && (map.getStyle().layers || []).length > 20) break;
  }

  const gz = performance.getEntriesByType("resource")
    .map((x) => x.name.replace(location.origin + "/", ""))
    .filter((x) => x.includes(".gz"));

  return {
    loadFired,
    styleLoaded: map.isStyleLoaded(),
    nLayers: (map.getStyle().layers || []).length,
    gz: gz.length,
    gzMissingVersion: gz.filter((x) => !x.includes("?v=")),   // G101 regression probe
    waitedMs: Date.now() - t0,
  };
}
