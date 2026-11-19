(function () {
  if (!HVDAuth.requireSession("/")) return;
  HVDi18n.initFromSystem();

  var listEl = document.getElementById("alerts-list");
  var errorEl = document.getElementById("alerts-error");
  var emptyEl = document.getElementById("alerts-empty");

  function handleAuthFailure(res) {
    if (res.status === 401) {
      HVDAuth.clearSession();
      window.location.replace("/");
      return true;
    }
    return false;
  }

  function parseAlertDate(iso) {
    var d = new Date(iso);
    if (isNaN(d.getTime())) return null;
    return d;
  }

  function dayKey(d) {
    return (
      d.getFullYear() +
      "-" +
      String(d.getMonth() + 1).padStart(2, "0") +
      "-" +
      String(d.getDate()).padStart(2, "0")
    );
  }

  function startOfLocalDay(d) {
    return new Date(d.getFullYear(), d.getMonth(), d.getDate());
  }

  function formatSectionTitle(d) {
    var today = startOfLocalDay(new Date());
    var day = startOfLocalDay(d);
    var diffDays = Math.round((today - day) / 86400000);
    if (diffDays === 0) return HVDi18n.t("alerts.day.today");
    if (diffDays === 1) return HVDi18n.t("alerts.day.yesterday");

    var monthName = HVDi18n.t("alerts.month." + (d.getMonth() + 1));
    var lang = HVDi18n.getLanguage();
    var key = lang === "ru" ? "alerts.date.ru" : "alerts.date.en";
    return HVDi18n.t(key, {
      month: monthName,
      day: String(d.getDate()),
      year: String(d.getFullYear()),
    });
  }

  function formatTime(d) {
    return (
      String(d.getHours()).padStart(2, "0") +
      ":" +
      String(d.getMinutes()).padStart(2, "0")
    );
  }

  function groupAlerts(alerts) {
    var groups = [];
    var index = {};
    for (var i = 0; i < alerts.length; i++) {
      var alert = alerts[i];
      var d = parseAlertDate(alert.timestamp);
      if (!d) continue;
      var key = dayKey(d);
      if (!index[key]) {
        index[key] = {
          key: key,
          date: startOfLocalDay(d),
          title: formatSectionTitle(d),
          items: [],
        };
        groups.push(index[key]);
      }
      index[key].items.push({ alert: alert, date: d });
    }
    // Alerts arrive newer→older; keep section order as first-seen (newer days first).
    return groups;
  }

  var thumbObserver = null;

  function resetThumbObserver() {
    if (thumbObserver) {
      thumbObserver.disconnect();
      thumbObserver = null;
    }
  }

  function ensureThumbObserver() {
    if (thumbObserver) return thumbObserver;
    if (typeof IntersectionObserver === "undefined") return null;
    thumbObserver = new IntersectionObserver(
      function (entries) {
        for (var i = 0; i < entries.length; i++) {
          var entry = entries[i];
          if (!entry.isIntersecting) continue;
          var box = entry.target;
          thumbObserver.unobserve(box);
          var load = box._loadThumb;
          box._loadThumb = null;
          if (typeof load === "function") load();
        }
      },
      // Small margin so thumbs start just before they scroll into view.
      { root: null, rootMargin: "80px 0px", threshold: 0.01 }
    );
    return thumbObserver;
  }

  function scheduleThumb(box, loadFn) {
    var obs = ensureThumbObserver();
    if (!obs) {
      loadFn();
      return;
    }
    box._loadThumb = loadFn;
    obs.observe(box);
  }

  function makeBox(alert, date) {
    var box = document.createElement("article");
    box.className = "alert-box is-loading";
    box.dataset.videoId = String(alert.video_id);

    var media = document.createElement("div");
    media.className = "alert-box-media";

    var spinner = document.createElement("div");
    spinner.className = "alert-spinner";
    media.appendChild(spinner);

    var err = document.createElement("p");
    err.className = "alert-thumb-error";
    err.hidden = true;
    err.textContent = HVDi18n.t("alerts.thumb_error");
    media.appendChild(err);

    var img = document.createElement("img");
    img.className = "alert-thumb";
    img.alt = "";
    img.hidden = true;
    media.appendChild(img);

    var play = document.createElement("button");
    play.type = "button";
    play.className = "alert-play";
    play.setAttribute("aria-label", HVDi18n.t("alerts.play"));
    play.hidden = true;
    play.addEventListener("click", function (ev) {
      ev.preventDefault();
      ev.stopPropagation();
      openVideoPlayer(alert.video_id);
    });
    media.appendChild(play);

    var meta = document.createElement("div");
    meta.className = "alert-box-meta";
    meta.textContent = (alert.camera || "") + " · " + formatTime(date);

    box.appendChild(media);
    box.appendChild(meta);

    scheduleThumb(box, function () {
      loadThumb(alert.video_id, box, img, play, err, spinner);
    });
    return box;
  }

  function renderAlerts(alerts) {
    resetThumbObserver();
    listEl.innerHTML = "";
    var groups = groupAlerts(alerts);
    emptyEl.hidden = groups.length > 0;
    for (var i = 0; i < groups.length; i++) {
      var group = groups[i];
      var section = document.createElement("section");
      section.className = "alerts-day";

      var heading = document.createElement("h2");
      heading.className = "alerts-day-title";
      heading.textContent = group.title;
      section.appendChild(heading);

      var grid = document.createElement("div");
      grid.className = "alerts-grid";
      for (var j = 0; j < group.items.length; j++) {
        grid.appendChild(makeBox(group.items[j].alert, group.items[j].date));
      }
      section.appendChild(grid);
      listEl.appendChild(section);
    }
  }

  var activePlayer = null;

  function closeVideoPlayer() {
    if (!activePlayer) return;
    if (activePlayer.overlay && activePlayer.overlay.parentNode) {
      activePlayer.overlay.parentNode.removeChild(activePlayer.overlay);
    }
    document.removeEventListener("keydown", activePlayer.onKey);
    activePlayer = null;
  }

  function openVideoPlayer(videoId) {
    closeVideoPlayer();
    if (!HVDAuth.getSession()) return;

    var overlay = document.createElement("div");
    overlay.className = "alert-video-overlay";
    overlay.setAttribute("role", "dialog");
    overlay.setAttribute("aria-modal", "true");

    var dialog = document.createElement("div");
    dialog.className = "alert-video-dialog";

    var closeBtn = document.createElement("button");
    closeBtn.type = "button";
    closeBtn.className = "btn alert-video-close";
    closeBtn.textContent = HVDi18n.t("alerts.video_close");
    closeBtn.addEventListener("click", function (ev) {
      ev.preventDefault();
      closeVideoPlayer();
    });

    var video = document.createElement("video");
    video.controls = true;
    video.autoplay = true;
    video.playsInline = true;

    var err = document.createElement("p");
    err.className = "alert-video-error";
    err.hidden = true;
    err.textContent = HVDi18n.t("alerts.video_failed");

    dialog.appendChild(closeBtn);
    dialog.appendChild(video);
    dialog.appendChild(err);
    overlay.appendChild(dialog);
    document.body.appendChild(overlay);

    overlay.addEventListener("click", function (ev) {
      if (ev.target === overlay) closeVideoPlayer();
    });

    function onKey(ev) {
      if (ev.key === "Escape") closeVideoPlayer();
    }
    document.addEventListener("keydown", onKey);

    activePlayer = { overlay: overlay, onKey: onKey };

    video.addEventListener("error", function () {
      if (!activePlayer || activePlayer.overlay !== overlay) return;
      video.hidden = true;
      err.hidden = false;
    });
    video.src = "/api/alert_video?id=" + encodeURIComponent(videoId);
    video.play().catch(function () {
      /* autoplay may be blocked; controls remain */
    });
  }

  function showThumbError(box, img, play, err, spinner) {
    spinner.hidden = true;
    img.hidden = true;
    play.hidden = true;
    err.hidden = false;
    box.classList.remove("is-loading", "is-ready");
    box.classList.add("is-error");
    if (img._objectUrl) {
      URL.revokeObjectURL(img._objectUrl);
      img._objectUrl = null;
    }
  }

  function showThumbReady(box, img, play, err, spinner) {
    spinner.hidden = true;
    img.hidden = false;
    play.hidden = false;
    err.hidden = true;
    box.classList.remove("is-loading", "is-error");
    box.classList.add("is-ready");
  }

  function loadThumb(videoId, box, img, play, err, spinner) {
    if (!HVDAuth.getSession()) return;
    var url = "/api/thumbnail?video=" + encodeURIComponent(videoId);
    // Fetch the full PNG first so the <img> never paints a progressive partial.
    fetch(url, { credentials: "same-origin" })
      .then(function (resp) {
        if (resp.status === 401) {
          HVDAuth.clearSession();
          window.location.replace("/");
          return null;
        }
        if (!resp.ok) throw new Error("thumb " + resp.status);
        return resp.blob();
      })
      .then(function (blob) {
        if (!blob) return;
        if (img._objectUrl) URL.revokeObjectURL(img._objectUrl);
        var objectUrl = URL.createObjectURL(blob);
        img._objectUrl = objectUrl;
        function reveal() {
          showThumbReady(box, img, play, err, spinner);
        }
        img.onerror = function () {
          showThumbError(box, img, play, err, spinner);
        };
        img.onload = function () {
          if (typeof img.decode === "function") {
            img.decode().then(reveal).catch(reveal);
          } else {
            reveal();
          }
        };
        img.src = objectUrl;
      })
      .catch(function () {
        showThumbError(box, img, play, err, spinner);
      });
  }

  HVDAuth.api("/api/auth/whoami")
    .then(function (res) {
      if (handleAuthFailure(res)) return null;
      if (res.ok && res.data && res.data.language) {
        HVDi18n.setLanguage(res.data.language);
      }
      return HVDFeatures.load();
    })
    .then(function (featRes) {
      if (!featRes) return;
      if (!HVDFeatures.isEnabled("ALERT_VIEW")) {
        errorEl.textContent = HVDi18n.t("alerts.load_failed");
        HVDHeader.mount({ active: "alerts" });
        return;
      }
      HVDHeader.mount({ active: "alerts" });
      return HVDAuth.api("/api/alerts").then(function (res) {
        if (handleAuthFailure(res)) return;
        if (!res.ok) {
          errorEl.textContent =
            (res.data && res.data.error) || HVDi18n.t("alerts.load_failed");
          return;
        }
        renderAlerts((res.data && res.data.alerts) || []);
      });
    });
})();
