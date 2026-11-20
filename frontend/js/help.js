(function () {
  if (!HVDAuth.requireSession("/")) return;
  HVDi18n.initFromSystem();

  var host = document.getElementById("help-features");

  function handleAuthFailure(res) {
    if (res.status === 401) {
      HVDAuth.clearSession();
      window.location.replace("/");
      return true;
    }
    return false;
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function sectionId(featureId) {
    return "feature-" + featureId;
  }

  function render() {
    host.innerHTML = "";
    var catalog = (window.HVDHelpContent && HVDHelpContent.features) || [];
    for (var i = 0; i < catalog.length; i++) {
      (function (feat) {
        var details = document.createElement("details");
        details.className = "help-feature";
        details.id = sectionId(feat.id);

        var summary = document.createElement("summary");
        summary.className = "help-feature-summary";
        var title = HVDi18n.t("feature." + feat.id + ".title");
        summary.innerHTML =
          escapeHtml(title) +
          ' <span class="muted">(' +
          escapeHtml(feat.id) +
          ")</span>";
        details.appendChild(summary);

        var body = document.createElement("div");
        body.className = "help-feature-body";

        var overview = document.createElement("p");
        overview.textContent = HVDi18n.t("help." + feat.id + ".body");
        body.appendChild(overview);

        var opts = feat.options || [];
        if (opts.length) {
          var optHeading = document.createElement("h3");
          optHeading.textContent = HVDi18n.t("help.options_heading");
          body.appendChild(optHeading);

          var dl = document.createElement("dl");
          dl.className = "help-options";
          for (var j = 0; j < opts.length; j++) {
            var opt = opts[j];
            var dt = document.createElement("dt");
            var code = document.createElement("code");
            code.textContent = opt.key;
            dt.appendChild(code);
            if (opt.kind === "env") {
              var badge = document.createElement("span");
              badge.className = "help-badge";
              badge.textContent = HVDi18n.t("help.badge.env");
              dt.appendChild(document.createTextNode(" "));
              dt.appendChild(badge);
            }
            var dd = document.createElement("dd");
            dd.textContent = HVDi18n.t("help." + feat.id + ".opt." + opt.id);
            dl.appendChild(dt);
            dl.appendChild(dd);
          }
          body.appendChild(dl);
        } else {
          var none = document.createElement("p");
          none.className = "muted";
          none.textContent = HVDi18n.t("help.no_options");
          body.appendChild(none);
        }

        details.appendChild(body);
        host.appendChild(details);
      })(catalog[i]);
    }
  }

  function openFromHash() {
    var hash = (window.location.hash || "").replace(/^#/, "");
    if (!hash) return;
    var el = document.getElementById(hash);
    if (!el || el.tagName.toLowerCase() !== "details") return;
    el.open = true;
    try {
      el.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      el.scrollIntoView(true);
    }
  }

  HVDAuth.api("/api/auth/whoami")
    .then(function (res) {
      if (handleAuthFailure(res)) return null;
      if (res.ok && res.data && res.data.language) {
        HVDi18n.setLanguage(res.data.language);
      }
      return HVDFeatures.load();
    })
    .then(function (featRes) {
      if (!featRes) return;
      HVDHeader.mount({ active: "help" });
      render();
      openFromHash();
    });

  window.addEventListener("hashchange", openFromHash);
})();
