(function (global) {
  /**
   * Mount shared app header into #site-header.
   * options.active: "app" | "configuration" | "alerts" | "streaming" | "help"
   */
  function mount(options) {
    options = options || {};
    var host = document.getElementById("site-header");
    if (!host) return;

    var session = HVDAuth.getSession();
    var username = session ? session.username : "";
    var showConfig = !HVDFeatures || HVDFeatures.isEnabled("CONFIG");
    var showAlerts = !HVDFeatures || HVDFeatures.isEnabled("ALERT_VIEW");
    var showStreaming = !HVDFeatures || HVDFeatures.isEnabled("STREAMING");

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
    if (showStreaming) {
      addNav("/streaming/", "header.nav.streaming", "streaming");
    }
    if (showConfig) {
      addNav("/configuration/", "header.nav.configuration", "configuration");
    }
    addNav("/help/", "header.nav.help", "help");

    host.querySelector("#header-user").textContent = username;
    host.querySelector("#header-logout").addEventListener("click", function () {
      HVDAuth.clearSession();
      window.location.replace("/");
    });

    HVDi18n.apply(host);

    if (global.HVDFooter) HVDFooter.mount();
  }

  /** Same feature-gated destinations as the header nav. */
  function navItems() {
    var items = [];
    if (!HVDFeatures || HVDFeatures.isEnabled("ALERT_VIEW")) {
      items.push({
        href: "/alerts/",
        titleKey: "header.nav.alerts",
        descKey: "app.section.alerts.desc",
      });
    }
    if (!HVDFeatures || HVDFeatures.isEnabled("STREAMING")) {
      items.push({
        href: "/streaming/",
        titleKey: "header.nav.streaming",
        descKey: "app.section.streaming.desc",
      });
    }
    if (!HVDFeatures || HVDFeatures.isEnabled("CONFIG")) {
      items.push({
        href: "/configuration/",
        titleKey: "header.nav.configuration",
        descKey: "app.section.configuration.desc",
      });
    }
    return items;
  }

  global.HVDHeader = { mount: mount, navItems: navItems };
})(window);
