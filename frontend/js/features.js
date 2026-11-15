(function (global) {
  var cache = null;

  function load() {
    return HVDAuth.api("/api/features").then(function (res) {
      if (!res.ok) {
        cache = null;
        return res;
      }
      cache = {};
      var list = (res.data && res.data.features) || [];
      for (var i = 0; i < list.length; i++) {
        cache[list[i].name] = list[i];
      }
      return res;
    });
  }

  function get(name) {
    return cache && cache[name] ? cache[name] : null;
  }

  function isEnabled(name) {
    var f = get(name);
    return !!(f && f.enabled);
  }

  function all() {
    if (!cache) return [];
    return Object.keys(cache)
      .sort()
      .map(function (k) {
        return cache[k];
      });
  }

  function title(name) {
    var key = "feature." + name + ".title";
    var translated = HVDi18n.t(key);
    if (translated !== key) return translated;
    return name;
  }

  function description(feature) {
    var name = feature && feature.name;
    if (!name) return "";
    var key = "feature." + name + ".desc";
    var translated = HVDi18n.t(key);
    if (translated !== key) return translated;
    return feature.description || "";
  }

  function setEnabled(name, enabled) {
    var q =
      "/api/features?name=" +
      encodeURIComponent(name) +
      "&enabled=" +
      encodeURIComponent(enabled ? "true" : "false");
    return HVDAuth.api(q, { method: "UPDATE" }).then(function (res) {
      if (res.ok && cache && res.data) {
        cache[name] = res.data;
      }
      return res;
    });
  }

  global.HVDFeatures = {
    load: load,
    get: get,
    isEnabled: isEnabled,
    all: all,
    title: title,
    description: description,
    setEnabled: setEnabled,
  };
})(window);
