(function () {
  var form = document.getElementById("login-form");
  var errorEl = document.getElementById("login-error");

  if (HVDAuth.getSession()) {
    window.location.replace("/configuration/");
    return;
  }

  form.addEventListener("submit", function (ev) {
    ev.preventDefault();
    errorEl.textContent = "";
    var username = document.getElementById("username").value.trim();
    var password = document.getElementById("password").value;
    if (!username || !password) {
      errorEl.textContent = "Username and password are required.";
      return;
    }
    HVDAuth.api("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username: username, password: password }),
    }).then(function (res) {
      if (!res.ok) {
        errorEl.textContent =
          (res.data && res.data.error) || "Login failed.";
        return;
      }
      HVDAuth.saveSession(res.data.username || username, res.data.token);
      window.location.replace("/configuration/");
    }).catch(function () {
      errorEl.textContent = "Network error.";
    });
  });
})();
