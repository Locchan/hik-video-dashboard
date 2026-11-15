(function () {
  if (!HVDAuth.requireSession("/")) return;

  var tbody = document.getElementById("config-body");
  var errorEl = document.getElementById("page-error");
  var newBtn = document.getElementById("btn-new");
  var logoutBtn = document.getElementById("btn-logout");
  var userLabel = document.getElementById("user-label");
  var entries = [];
  var mode = null; // null | "edit" | "delete" | "create"
  var activeName = null;

  var session = HVDAuth.getSession();
  userLabel.textContent = session.username;

  logoutBtn.addEventListener("click", function () {
    HVDAuth.clearSession();
    window.location.replace("/");
  });

  newBtn.addEventListener("click", function () {
    if (mode) return;
    mode = "create";
    activeName = null;
    render();
  });

  function setError(msg) {
    errorEl.textContent = msg || "";
  }

  function validatePair(name, value, excludeName) {
    name = (name || "").trim();
    value = (value || "").trim();
    if (!name) return "Key must not be empty.";
    if (!value) return "Value must not be empty.";
    for (var i = 0; i < entries.length; i++) {
      if (excludeName && entries[i].name === excludeName) continue;
      if (entries[i].name === name) {
        return "Key already exists for your group.";
      }
    }
    return null;
  }

  function load() {
    setError("");
    return HVDAuth.api("/api/config").then(function (res) {
      if (res.status === 401) {
        HVDAuth.clearSession();
        window.location.replace("/");
        return;
      }
      if (!res.ok) {
        setError((res.data && res.data.error) || "Failed to load config.");
        entries = [];
        render();
        return;
      }
      entries = (res.data && res.data.entries) || [];
      mode = null;
      activeName = null;
      render();
    });
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
    newBtn.disabled = !!mode;

    if (mode === "create") {
      var createRow = document.createElement("tr");
      createRow.innerHTML =
        '<td><input class="cell" id="new-key" type="text" placeholder="key"></td>' +
        '<td><input class="cell" id="new-value" type="text" placeholder="value"></td>' +
        '<td class="actions"><button type="button" id="new-submit">submit</button></td>';
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
            setError((res.data && res.data.error) || "Create failed.");
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
            '<button type="button" class="btn-edit">edit</button>' +
            '<button type="button" class="btn-delete">delete</button>';
        } else if (isEdit) {
          actionsHtml = '<button type="button" class="btn-submit">submit</button>';
        } else if (isDelete) {
          actionsHtml = '<button type="button" class="btn-confirm">confirm</button>';
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
                setError((res.data && res.data.error) || "Update failed.");
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
                setError((res.data && res.data.error) || "Delete failed.");
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

  load();
})();
