(function (global) {
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

  function mount() {
    render({
      backend: "…",
      frontend: bakedFrontend() || "…",
      purest: "…",
    });

    var req = global.HVDAuth
      ? HVDAuth.api("/api/version")
      : fetch("/api/version", { credentials: "same-origin" }).then(function (
          resp
        ) {
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
        });

    return req
      .then(function (res) {
        if (res && res.ok && res.data) {
          render(res.data);
        } else {
          render({
            backend: "?",
            frontend: bakedFrontend() || "?",
            purest: "?",
          });
        }
      })
      .catch(function () {
        render({
          backend: "?",
          frontend: bakedFrontend() || "?",
          purest: "?",
        });
      });
  }

  global.HVDFooter = { mount: mount };
})(window);
