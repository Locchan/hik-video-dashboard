(function () {
  if (!HVDAuth.requireSession("/")) return;
  HVDi18n.initFromSystem();

  HVDAuth.api("/api/auth/whoami").then(function (res) {
    if (res.status === 401) {
      HVDAuth.clearSession();
      window.location.replace("/");
      return;
    }
    if (res.ok && res.data && res.data.language != null && String(res.data.language).trim() !== "") {
      HVDi18n.setLanguage(res.data.language);
    }
    return HVDFeatures.load().then(function () {
      HVDHeader.mount({ active: "app" });
    });
  });
})();
