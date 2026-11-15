(function () {
  if (!HVDAuth.requireSession("/")) return;
  HVDi18n.initFromSystem();

  function renderHome() {
    var list = document.getElementById("home-sections");
    var empty = document.getElementById("home-empty");
    if (!list || !empty) return;

    list.innerHTML = "";
    var items = HVDHeader.navItems();
    if (!items.length) {
      empty.hidden = false;
      return;
    }
    empty.hidden = true;
    items.forEach(function (item) {
      var a = document.createElement("a");
      a.className = "home-section-link";
      a.href = item.href;
      a.innerHTML =
        '<span class="home-section-title" data-i18n="' +
        item.titleKey +
        '"></span>' +
        '<span class="home-section-desc muted" data-i18n="' +
        item.descKey +
        '"></span>';
      list.appendChild(a);
    });
    HVDi18n.apply(list);
  }

  HVDAuth.api("/api/auth/whoami").then(function (res) {
    if (res.status === 401) {
      HVDAuth.clearSession();
      window.location.replace("/");
      return;
    }
    if (
      res.ok &&
      res.data &&
      res.data.language != null &&
      String(res.data.language).trim() !== ""
    ) {
      HVDi18n.setLanguage(res.data.language);
    }
    return HVDFeatures.load().then(function () {
      HVDHeader.mount({ active: "app" });
      renderHome();
    });
  });
})();
