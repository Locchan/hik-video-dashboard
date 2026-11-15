(function () {
  HVDi18n.initFromSystem();

  var form = document.getElementById("login-form");
  var errorEl = document.getElementById("login-error");

  if (HVDAuth.getSession()) {
    window.location.replace("/app/");
    return;
  }

  if (window.location.search.indexOf("pwd=changed") !== -1) {
    errorEl.className = "ok";
    errorEl.textContent = HVDi18n.t("login.pwd_changed");
  }

  form.addEventListener("submit", function (ev) {
    errorEl.className = "error";
    ev.preventDefault();
    errorEl.textContent = "";
    var username = document.getElementById("username").value.trim();
    var password = document.getElementById("password").value;
    if (!username || !password) {
      errorEl.textContent = HVDi18n.t("login.required");
      return;
    }
    HVDAuth.api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: username, password: password }),
    })
      .then(function (res) {
        if (!res.ok) {
          errorEl.textContent =
            (res.data && res.data.error) || HVDi18n.t("login.failed");
          return;
        }
        HVDAuth.saveSession(res.data.username || username, res.data.token);
        return ensureLanguageThenGo();
      })
      .catch(function () {
        errorEl.textContent = HVDi18n.t("login.network");
      });
  });

  function goApp() {
    window.location.replace("/app/");
  }

  function ensureLanguageThenGo() {
    var systemLang = HVDi18n.systemLanguage();
    return HVDAuth.api("/api/auth/whoami").then(function (res) {
      if (!res.ok) {
        goApp();
        return;
      }
      var raw = res.data && res.data.language;
      if (raw != null && String(raw).trim() !== "") {
        HVDi18n.setLanguage(raw);
        goApp();
        return;
      }
      // No language set yet — persist system language when CONFIG is on.
      return HVDFeatures.load().then(function () {
        if (!HVDFeatures.isEnabled("CONFIG")) {
          HVDi18n.setLanguage(systemLang);
          goApp();
          return;
        }
        var q =
          "/api/config?entry_name=" +
          encodeURIComponent("language") +
          "&value=" +
          encodeURIComponent(systemLang);
        return HVDAuth.api(q, { method: "PUT" }).then(function () {
          HVDi18n.setLanguage(systemLang);
          goApp();
        });
      });
    });
  }
})();

