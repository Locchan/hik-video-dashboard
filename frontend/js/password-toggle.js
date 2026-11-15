(function (global) {
  function labelText() {
    return (global.HVDi18n && HVDi18n.t("password.show")) || "Show password";
  }

  function attachOne(input) {
    if (!input || input.getAttribute("data-pwd-enhanced") === "1") return;
    input.setAttribute("data-pwd-enhanced", "1");

    var row = document.createElement("label");
    row.className = "show-password";
    var cb = document.createElement("input");
    cb.type = "checkbox";
    cb.setAttribute("autocomplete", "off");
    var span = document.createElement("span");
    span.setAttribute("data-i18n", "password.show");
    span.textContent = labelText();
    row.appendChild(cb);
    row.appendChild(span);

    cb.addEventListener("change", function () {
      input.type = cb.checked ? "text" : "password";
    });

    var parent = input.parentNode;
    if (parent && parent.classList && parent.classList.contains("inline-pwd")) {
      var block = document.createElement("div");
      block.className = "pwd-field";
      parent.parentNode.insertBefore(block, parent);
      block.appendChild(parent);
      block.appendChild(row);
      return;
    }
    if (parent && parent.tagName === "LABEL") {
      parent.parentNode.insertBefore(row, parent.nextSibling);
      return;
    }
    parent.insertBefore(row, input.nextSibling);
  }

  function enhance(root) {
    root = root || document;
    var nodes = root.querySelectorAll('input[type="password"]');
    for (var i = 0; i < nodes.length; i++) {
      attachOne(nodes[i]);
    }
  }

  function boot() {
    enhance(document);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }

  global.HVDPasswordToggle = { enhance: enhance };
})(window);
