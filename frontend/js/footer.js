(function (global) {
  var CACHE_KEY = "hvd_version_cache";
  var CACHE_TTL_MS = 15 * 60 * 1000;

  function ensureHost() {
    var host = document.getElementById("site-footer");
    if (host) return host;
    host = document.createElement("div");
    host.id = "site-footer";
    document.body.appendChild(host);
    return host;
  }

  function bakedFrontend() {
    return (
      (typeof global.HVD_FRONTEND_VERSION === "string" &&
        global.HVD_FRONTEND_VERSION) ||
      ""
    );
  }

  function readCache() {
    try {
      var raw = localStorage.getItem(CACHE_KEY);
      if (!raw) return null;
      var parsed = JSON.parse(raw);
      if (
        !parsed ||
        typeof parsed.ts !== "number" ||
        !parsed.data ||
        typeof parsed.data !== "object"
      ) {
        return null;
      }
      if (Date.now() - parsed.ts > CACHE_TTL_MS) return null;
      return parsed.data;
    } catch (e) {
      return null;
    }
  }

  function writeCache(data) {
    try {
      localStorage.setItem(
        CACHE_KEY,
        JSON.stringify({ ts: Date.now(), data: data })
      );
    } catch (e) {
      /* ignore quota / private mode */
    }
  }

  function render(versions) {
    var host = ensureHost();
    var backend = (versions && versions.backend) || "?";
    // Prefer the version baked into this frontend image so UI-only deploys
    // do not depend on recreating the backend for /api/version.
    var frontend = bakedFrontend() || (versions && versions.frontend) || "?";
    var purest = (versions && versions.purest) || "?";

    host.innerHTML =
      '<footer class="site-footer">' +
      '<div class="site-footer-inner">' +
      '<span><span data-i18n="footer.backend">backend</span> ' +
      escapeHtml(backend) +
      "</span>" +
      '<span class="site-footer-sep" aria-hidden="true">·</span>' +
      '<span><span data-i18n="footer.frontend">frontend</span> ' +
      escapeHtml(frontend) +
      "</span>" +
      '<span class="site-footer-sep" aria-hidden="true">·</span>' +
      '<span><span data-i18n="footer.purest">purest</span> ' +
      escapeHtml(purest) +
      "</span>" +
      "</div>" +
      "</footer>";

    if (global.HVDi18n) HVDi18n.apply(host);
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fetchVersion() {
    if (global.HVDAuth) return HVDAuth.api("/api/version");
    return fetch("/api/version", { credentials: "same-origin" }).then(
      function (resp) {
        return resp.text().then(function (text) {
          var data = {};
          if (text) {
            try {
              data = JSON.parse(text);
            } catch (e) {
              data = {};
            }
          }
          return { ok: resp.ok, data: data };
        });
      }
    );
  }

  function mount() {
    var cached = readCache();
    if (cached) {
      render(cached);
      return Promise.resolve(cached);
    }

    render({
      backend: "…",
      frontend: bakedFrontend() || "…",
      purest: "…",
    });

    return fetchVersion()
      .then(function (res) {
        if (res && res.ok && res.data) {
          writeCache(res.data);
          render(res.data);
          return res.data;
        }
        render({
          backend: "?",
          frontend: bakedFrontend() || "?",
          purest: "?",
        });
        return null;
      })
      .catch(function () {
        render({
          backend: "?",
          frontend: bakedFrontend() || "?",
          purest: "?",
        });
        return null;
      });
  }

  global.HVDFooter = { mount: mount };
})(window);
