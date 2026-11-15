(function () {
  if (!HVDAuth.requireSession("/")) return;

  HVDi18n.initFromSystem();

  var tbody = document.getElementById("config-body");
  var errorEl = document.getElementById("page-error");
  var newBtn = document.getElementById("btn-new");
  var selfForm = document.getElementById("self-password-form");
  var selfError = document.getElementById("self-password-error");
  var adminPanel = document.getElementById("admin-panel");
  var adminError = document.getElementById("admin-error");
  var usersBody = document.getElementById("users-body");
  var createForm = document.getElementById("create-user-form");
  var languageSelect = document.getElementById("language-select");
  var configSection = document.getElementById("config-section");
  var configDisabled = document.getElementById("config-disabled");
  var featuresSection = document.getElementById("features-section");
  var featuresBody = document.getElementById("features-body");
  var featuresError = document.getElementById("features-error");
  var entries = [];
  var mode = null; // null | "edit" | "delete" | "create"
  var activeName = null;
  var capabilities = [];
  var isAdmin = false;
  var canCreate = false;
  var languageSaving = false;
  var configFeatureOn = false;

  var session = HVDAuth.getSession();

  newBtn.addEventListener("click", function () {
    if (mode || !configFeatureOn) return;
    mode = "create";
    activeName = null;
    render();
  });

  function setError(msg) {
    errorEl.textContent = msg || "";
  }

  function hasCap(cap) {
    return capabilities.indexOf(cap) !== -1;
  }

  function validatePair(name, value, excludeName) {
    name = (name || "").trim();
    value = (value || "").trim();
    if (!name) return HVDi18n.t("config.key_empty");
    if (!value) return HVDi18n.t("config.value_empty");
    for (var i = 0; i < entries.length; i++) {
      if (excludeName && entries[i].name === excludeName) continue;
      if (entries[i].name === name) {
        return HVDi18n.t("config.key_exists");
      }
    }
    return null;
  }

  function handleAuthFailure(res) {
    if (res.status === 401) {
      HVDAuth.clearSession();
      window.location.replace("/");
      return true;
    }
    return false;
  }

  function findLanguageEntry() {
    for (var i = 0; i < entries.length; i++) {
      if (entries[i].name === "language") return entries[i];
    }
    return null;
  }

  function syncLanguageSelect() {
    var entry = findLanguageEntry();
    var raw = entry ? entry.value : null;
    var ui = HVDi18n.normalize(raw);
    languageSelect.value = ui;
    HVDi18n.setLanguage(ui);
  }

  function persistLanguage(value) {
    if (!configFeatureOn) {
      HVDi18n.setLanguage(value);
      return Promise.resolve();
    }
    var ui = HVDi18n.normalize(value);
    HVDi18n.setLanguage(ui);
    languageSaving = true;
    languageSelect.disabled = true;
    var entry = findLanguageEntry();
    var q =
      "/api/config?entry_name=" +
      encodeURIComponent("language") +
      "&value=" +
      encodeURIComponent(ui);
    var method = entry ? "UPDATE" : "PUT";
    return HVDAuth.api(q, { method: method }).then(function (res) {
      languageSaving = false;
      languageSelect.disabled = false;
      if (handleAuthFailure(res)) return;
      if (!res.ok) {
        setError((res.data && res.data.error) || HVDi18n.t("config.update_failed"));
        syncLanguageSelect();
        return;
      }
      return loadConfig();
    });
  }

  languageSelect.addEventListener("change", function () {
    if (languageSaving) return;
    persistLanguage(languageSelect.value).then(function () {
      renderFeatures();
      HVDHeader.mount({ active: "configuration" });
    });
  });

  function applyConfigVisibility() {
    configFeatureOn = HVDFeatures.isEnabled("CONFIG");
    configSection.hidden = !configFeatureOn;
    configDisabled.hidden = configFeatureOn;
    newBtn.hidden = !configFeatureOn;
  }

  function renderFeatures() {
    featuresBody.innerHTML = "";
    if (!isAdmin) {
      featuresSection.hidden = true;
      return;
    }
    featuresSection.hidden = false;
    var list = HVDFeatures.all();
    for (var i = 0; i < list.length; i++) {
      (function (feature) {
        var tr = document.createElement("tr");
        var title = HVDFeatures.title(feature.name);
        var desc = HVDFeatures.description(feature);
        tr.innerHTML =
          "<td>" +
          escapeHtml(title) +
          ' <span class="muted">(' +
          escapeHtml(feature.name) +
          ")</span></td><td>" +
          escapeHtml(desc) +
          '</td><td class="actions">' +
          '<label class="feature-toggle">' +
          '<input type="checkbox" class="feat-enabled" ' +
          (feature.enabled ? "checked " : "") +
          "/>" +
          '<span data-i18n="features.enabled">' +
          escapeHtml(HVDi18n.t("features.enabled")) +
          "</span></label></td>";
        featuresBody.appendChild(tr);
        tr.querySelector(".feat-enabled").addEventListener("change", function (ev) {
          var enabled = ev.target.checked;
          featuresError.textContent = "";
          HVDFeatures.setEnabled(feature.name, enabled).then(function (res) {
            if (handleAuthFailure(res)) return;
            if (!res.ok) {
              ev.target.checked = !enabled;
              featuresError.textContent =
                (res.data && res.data.error) ||
                HVDi18n.t("features.update_failed");
              return;
            }
            applyConfigVisibility();
            HVDHeader.mount({ active: "configuration" });
            if (configFeatureOn) loadConfig();
            else {
              entries = [];
              render();
            }
          });
        });
      })(list[i]);
    }
  }

  function loadWhoami() {
    return HVDAuth.api("/api/auth/whoami").then(function (res) {
      if (handleAuthFailure(res)) return;
      if (!res.ok) return;
      capabilities = (res.data && res.data.capabilities) || [];
      isAdmin =
        hasCap("PUR_CAP_ADMIN") ||
        hasCap("PUR_CAP_ROOT") ||
        hasCap("PUR_CAP_ALL");
      canCreate =
        hasCap("PUR_CAP_CREATE_USER") ||
        hasCap("PUR_CAP_ROOT") ||
        hasCap("PUR_CAP_ALL");
      adminPanel.hidden = !(isAdmin || canCreate);
      createForm.hidden = !canCreate;
      document.getElementById("users-table-wrap").hidden = !isAdmin;
      if (res.data && res.data.language != null && String(res.data.language).trim() !== "") {
        HVDi18n.setLanguage(res.data.language);
        languageSelect.value = HVDi18n.getLanguage();
      }
      if (isAdmin) loadUsers();
    });
  }

  function loadConfig() {
    if (!configFeatureOn) {
      entries = [];
      render();
      return Promise.resolve();
    }
    setError("");
    return HVDAuth.api("/api/config").then(function (res) {
      if (handleAuthFailure(res)) return;
      if (!res.ok) {
        setError((res.data && res.data.error) || HVDi18n.t("config.load_failed"));
        entries = [];
        render();
        return;
      }
      entries = (res.data && res.data.entries) || [];
      mode = null;
      activeName = null;
      syncLanguageSelect();
      render();
    });
  }

  function loadUsers() {
    adminError.textContent = "";
    return HVDAuth.api("/api/auth/users").then(function (res) {
      if (handleAuthFailure(res)) return;
      if (!res.ok) {
        adminError.textContent =
          (res.data && res.data.error) || HVDi18n.t("users.load_failed");
        usersBody.innerHTML = "";
        return;
      }
      renderUsers((res.data && res.data.users) || []);
    });
  }

  function setPassword(username, password, errorEl) {
    return HVDAuth.api("/api/auth/set_password", {
      method: "POST",
      body: JSON.stringify({ username: username, password: password }),
    }).then(function (res) {
      if (handleAuthFailure(res)) return null;
      if (!res.ok) {
        if (errorEl) {
          errorEl.className = "error";
          errorEl.textContent =
            (res.data && res.data.error) || HVDi18n.t("account.pwd_failed");
        }
        return null;
      }
      return res;
    });
  }

  selfForm.addEventListener("submit", function (ev) {
    ev.preventDefault();
    selfError.textContent = "";
    var password = document.getElementById("self-password").value;
    var confirm = document.getElementById("self-password-confirm").value;
    if (password.length < 8) {
      selfError.textContent = HVDi18n.t("account.pwd_min");
      return;
    }
    if (password !== confirm) {
      selfError.textContent = HVDi18n.t("account.pwd_mismatch");
      return;
    }
    setPassword(session.username, password, selfError).then(function (res) {
      if (!res) return;
      HVDAuth.clearSession();
      window.location.replace("/?pwd=changed");
    });
  });

  createForm.addEventListener("submit", function (ev) {
    ev.preventDefault();
    adminError.textContent = "";
    var username = document.getElementById("create-username").value.trim();
    var password = document.getElementById("create-password").value;
    if (username.length < 4) {
      adminError.textContent = HVDi18n.t("users.username_min");
      return;
    }
    if (password.length < 8) {
      adminError.textContent = HVDi18n.t("account.pwd_min");
      return;
    }
    HVDAuth.api("/api/auth/create_user", {
      method: "POST",
      body: JSON.stringify({ username: username, password: password }),
    }).then(function (res) {
      if (handleAuthFailure(res)) return;
      if (!res.ok) {
        adminError.textContent =
          (res.data && res.data.error) || HVDi18n.t("users.create_failed");
        return;
      }
      document.getElementById("create-username").value = "";
      document.getElementById("create-password").value = "";
      loadUsers();
    });
  });

  function renderUsers(users) {
    usersBody.innerHTML = "";
    for (var i = 0; i < users.length; i++) {
      (function (user) {
        var tr = document.createElement("tr");
        tr.innerHTML =
          "<td>" +
          escapeHtml(user.username) +
          "</td><td>" +
          escapeHtml(user.group_name || "") +
          "</td><td>" +
          (user.loginable ? HVDi18n.t("users.yes") : HVDi18n.t("users.no")) +
          '</td><td class="actions">' +
          '<div class="inline-pwd">' +
          '<input type="password" class="admin-pwd" placeholder="' +
          escapeHtml(HVDi18n.t("users.pwd_placeholder")) +
          '" minlength="8" />' +
          '<button type="button" class="btn-set-pwd">' +
          escapeHtml(HVDi18n.t("users.pwd_set")) +
          "</button>" +
          "</div></td>";
        usersBody.appendChild(tr);
        if (window.HVDPasswordToggle) HVDPasswordToggle.enhance(tr);
        tr.querySelector(".btn-set-pwd").addEventListener("click", function () {
          adminError.className = "error";
          adminError.textContent = "";
          var input = tr.querySelector(".admin-pwd");
          var password = input.value;
          if (password.length < 8) {
            adminError.textContent = HVDi18n.t("account.pwd_min");
            return;
          }
          setPassword(user.username, password, adminError).then(function (res) {
            if (!res) return;
            input.value = "";
            adminError.className = "ok";
            adminError.textContent = HVDi18n.t("users.pwd_updated", {
              user: user.username,
            });
            if (user.username === session.username) {
              HVDAuth.clearSession();
              window.location.replace("/?pwd=changed");
            }
          });
        });
      })(users[i]);
    }
  }

  function hideOtherRowButtons(exceptRow) {
    var rows = tbody.querySelectorAll("tr");
    for (var i = 0; i < rows.length; i++) {
      if (rows[i] === exceptRow) continue;
      var actions = rows[i].querySelector(".actions");
      if (actions) actions.innerHTML = "";
    }
    newBtn.disabled = true;
  }

  function render() {
    tbody.innerHTML = "";
    newBtn.disabled = !!mode || !configFeatureOn;
    if (!configFeatureOn) return;

    if (mode === "create") {
      var createRow = document.createElement("tr");
      createRow.innerHTML =
        '<td><input class="cell" id="new-key" type="text" placeholder="' +
        escapeHtml(HVDi18n.t("config.placeholder.key")) +
        '"></td>' +
        '<td><input class="cell" id="new-value" type="text" placeholder="' +
        escapeHtml(HVDi18n.t("config.placeholder.value")) +
        '"></td>' +
        '<td class="actions"><button type="button" id="new-submit">' +
        escapeHtml(HVDi18n.t("config.submit")) +
        "</button></td>";
      tbody.appendChild(createRow);
      createRow.querySelector("#new-submit").addEventListener("click", function () {
        var key = createRow.querySelector("#new-key").value;
        var value = createRow.querySelector("#new-value").value;
        var err = validatePair(key, value);
        if (err) {
          setError(err);
          return;
        }
        setError("");
        var q =
          "/api/config?entry_name=" +
          encodeURIComponent(key.trim()) +
          "&value=" +
          encodeURIComponent(value.trim());
        HVDAuth.api(q, { method: "PUT" }).then(function (res) {
          if (!res.ok) {
            setError(
              (res.data && res.data.error) || HVDi18n.t("config.create_failed")
            );
            return;
          }
          window.location.reload();
        });
      });
    }

    for (var i = 0; i < entries.length; i++) {
      (function (entry) {
        var tr = document.createElement("tr");
        var isEdit = mode === "edit" && activeName === entry.name;
        var isDelete = mode === "delete" && activeName === entry.name;
        var showActions = !mode || isEdit || isDelete;

        var valueCell = isEdit
          ? '<input class="cell edit-value" type="text">'
          : escapeHtml(entry.value);

        var actionsHtml = "";
        if (showActions && !mode) {
          actionsHtml =
            '<button type="button" class="btn-edit">' +
            escapeHtml(HVDi18n.t("config.edit")) +
            "</button>" +
            '<button type="button" class="btn-delete">' +
            escapeHtml(HVDi18n.t("config.delete")) +
            "</button>";
        } else if (isEdit) {
          actionsHtml =
            '<button type="button" class="btn-submit">' +
            escapeHtml(HVDi18n.t("config.submit")) +
            "</button>";
        } else if (isDelete) {
          actionsHtml =
            '<button type="button" class="btn-confirm">' +
            escapeHtml(HVDi18n.t("config.confirm")) +
            "</button>";
        }

        tr.innerHTML =
          "<td>" +
          escapeHtml(entry.name) +
          "</td><td>" +
          valueCell +
          '</td><td class="actions">' +
          actionsHtml +
          "</td>";
        tbody.appendChild(tr);

        if (isEdit) {
          tr.querySelector(".edit-value").value = entry.value;
        }

        var editBtn = tr.querySelector(".btn-edit");
        var deleteBtn = tr.querySelector(".btn-delete");
        var submitBtn = tr.querySelector(".btn-submit");
        var confirmBtn = tr.querySelector(".btn-confirm");

        if (editBtn) {
          editBtn.addEventListener("click", function () {
            mode = "edit";
            activeName = entry.name;
            render();
            hideOtherRowButtons(tr);
          });
        }
        if (deleteBtn) {
          deleteBtn.addEventListener("click", function () {
            mode = "delete";
            activeName = entry.name;
            render();
            hideOtherRowButtons(tr);
          });
        }
        if (submitBtn) {
          submitBtn.addEventListener("click", function () {
            var value = tr.querySelector(".edit-value").value;
            var err = validatePair(entry.name, value, entry.name);
            if (err) {
              setError(err);
              return;
            }
            setError("");
            var q =
              "/api/config?entry_name=" +
              encodeURIComponent(entry.name) +
              "&value=" +
              encodeURIComponent(value.trim());
            HVDAuth.api(q, { method: "UPDATE" }).then(function (res) {
              if (!res.ok) {
                setError(
                  (res.data && res.data.error) ||
                    HVDi18n.t("config.update_failed")
                );
                return;
              }
              window.location.reload();
            });
          });
        }
        if (confirmBtn) {
          confirmBtn.addEventListener("click", function () {
            var q =
              "/api/config?entry_name=" + encodeURIComponent(entry.name);
            HVDAuth.api(q, { method: "DELETE" }).then(function (res) {
              if (!res.ok) {
                setError(
                  (res.data && res.data.error) ||
                    HVDi18n.t("config.delete_failed")
                );
                return;
              }
              window.location.reload();
            });
          });
        }
      })(entries[i]);
    }
  }

  function escapeHtml(s) {
    return String(s)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  loadWhoami()
    .then(function () {
      return HVDFeatures.load();
    })
    .then(function (res) {
      if (res && !res.ok) {
        featuresError.textContent =
          (res.data && res.data.error) || HVDi18n.t("features.load_failed");
      }
      applyConfigVisibility();
      renderFeatures();
      HVDHeader.mount({ active: "configuration" });
      return loadConfig();
    });
})();
