(function (global) {
  var USER_COOKIE = "hvd_user";
  var TOKEN_COOKIE = "hvd_token";

  function setCookie(name, value, days) {
    var maxAge = days ? "; max-age=" + days * 86400 : "";
    document.cookie =
      encodeURIComponent(name) +
      "=" +
      encodeURIComponent(value) +
      "; path=/" +
      maxAge +
      "; SameSite=Lax";
  }

  function getCookie(name) {
    var key = encodeURIComponent(name) + "=";
    var parts = document.cookie.split(";");
    for (var i = 0; i < parts.length; i++) {
      var part = parts[i].trim();
      if (part.indexOf(key) === 0) {
        return decodeURIComponent(part.slice(key.length));
      }
    }
    return null;
  }

  function clearCookie(name) {
    document.cookie =
      encodeURIComponent(name) + "=; path=/; max-age=0; SameSite=Lax";
  }

  function saveSession(username, token) {
    setCookie(USER_COOKIE, username, 7);
    setCookie(TOKEN_COOKIE, token, 7);
  }

  function clearSession() {
    clearCookie(USER_COOKIE);
    clearCookie(TOKEN_COOKIE);
  }

  function getSession() {
    var username = getCookie(USER_COOKIE);
    var token = getCookie(TOKEN_COOKIE);
    if (!username || !token) return null;
    return { username: username, token: token };
  }

  function requireSession(loginPath) {
    if (!getSession()) {
      window.location.replace(loginPath || "/");
      return null;
    }
    return getSession();
  }

  function api(path, options) {
    options = options || {};
    var headers = Object.assign({}, options.headers || {});
    if (options.body && !headers["Content-Type"]) {
      headers["Content-Type"] = "application/json";
    }
    return fetch(
      path,
      Object.assign({}, options, { headers: headers, credentials: "same-origin" })
    ).then(function (resp) {
      return resp.text().then(function (text) {
        var data = {};
        if (text) {
          try {
            data = JSON.parse(text);
          } catch (e) {
            data = { error: text };
          }
        }
        return { status: resp.status, ok: resp.ok, data: data };
      });
    });
  }

  global.HVDAuth = {
    saveSession: saveSession,
    clearSession: clearSession,
    getSession: getSession,
    requireSession: requireSession,
    api: api,
    USER_COOKIE: USER_COOKIE,
    TOKEN_COOKIE: TOKEN_COOKIE,
  };
})(window);
