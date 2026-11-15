(function (global) {
  /**
   * Mount shared app header into #site-header.
   * options.active: "app" | "configuration" | "alerts"
   */
  function mount(options) {
    options = options || {};
    var host = document.getElementById("site-header");
    if (!host) return;

    var session = HVDAuth.getSession();
    var username = session ? session.username : "";
    var showConfig = !HVDFeatures || HVDFeatures.isEnabled("CONFIG");
    var showAlerts = !HVDFeatures || HVDFeatures.isEnabled("ALERT_VIEW");

    host.innerHTML =
      '<header class="site-header">' +
      '<div class="site-header-inner">' +
      '<a class="site-brand" href="/app/">' +
      '<span data-i18n="header.brand">HIK Video Dashboard</span>' +
      "</a>" +
      '<nav class="site-nav" id="site-nav"></nav>' +
      '<div class="site-header-actions">' +
      '<span class="site-user" id="header-user"></span>' +
      '<button type="button" class="btn" id="header-logout" data-i18n="header.logout">Log out</button>' +
      "</div>" +
      "</div>" +
      "</header>";

    var nav = host.querySelector("#site-nav");

    function addNav(href, i18nKey, activeKey) {
      var a = document.createElement("a");
      a.href = href;
      a.className =
        "site-nav-link" + (options.active === activeKey ? " is-active" : "");
      a.setAttribute("data-i18n", i18nKey);
      a.textContent = HVDi18n.t(i18nKey);
      nav.appendChild(a);
    }

    if (showAlerts) {
      addNav("/alerts/", "header.nav.alerts", "alerts");
    }
    if (showConfig) {
      addNav("/configuration/", "header.nav.configuration", "configuration");
    }

    host.querySelector("#header-user").textContent = username;
    host.querySelector("#header-logout").addEventListener("click", function () {
      HVDAuth.clearSession();
      window.location.replace("/");
    });

    HVDi18n.apply(host);
  }

  global.HVDHeader = { mount: mount };
})(window);
