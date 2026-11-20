(function () {
  if (!HVDAuth.requireSession("/")) return;
  HVDi18n.initFromSystem();

  var listEl = document.getElementById("camera-list");
  var errorEl = document.getElementById("streaming-error");
  var emptyEl = document.getElementById("streaming-empty");
  var hintEl = document.getElementById("streaming-hint");
  var refreshBtn = document.getElementById("btn-refresh");

  var HIDDEN_KILL_MS = 30000;
  /** @type {Object<string, {NAME: string, CHANNELS: Object}>} */
  var dvrs = {};
  var openKey = null; // "dvrId\\tchannelId"
  var activePlayer = null;
  var activeVideo = null;
  var hiddenTimer = null;

  function handleAuthFailure(res) {
    if (res.status === 401) {
      HVDAuth.clearSession();
      window.location.replace("/");
      return true;
    }
    return false;
  }

  function panelKey(dvrId, channelId) {
    return dvrId + "\t" + channelId;
  }

  function parsePanelKey(key) {
    var parts = String(key).split("\t");
    return { dvrId: parts[0], channelId: parts[1] };
  }

  function dvrIdFromResponseKey(key) {
    // API keys are DVR_{X}; stream query wants X.
    if (String(key).indexOf("DVR_") === 0) return String(key).slice(4);
    return String(key);
  }

  function wsStreamUrl(dvrId, channelId) {
    var proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    return (
      proto +
      "//" +
      window.location.host +
      "/ws/streaming/stream?dvr=" +
      encodeURIComponent(dvrId) +
      "&channel=" +
      encodeURIComponent(channelId)
    );
  }

  function stopStream() {
    if (hiddenTimer) {
      clearTimeout(hiddenTimer);
      hiddenTimer = null;
    }
    if (activePlayer) {
      try {
        activePlayer.pause();
      } catch (e) {}
      try {
        activePlayer.unload();
      } catch (e) {}
      try {
        activePlayer.detachMediaElement();
      } catch (e) {}
      try {
        activePlayer.destroy();
      } catch (e) {}
      activePlayer = null;
    }
    if (activeVideo) {
      try {
        activeVideo.removeAttribute("src");
        activeVideo.load();
      } catch (e) {}
      activeVideo = null;
    }
  }

  function closeOpenPanel() {
    stopStream();
    if (openKey == null) return;
    var panel = null;
    var panels = listEl.querySelectorAll(".camera-panel");
    for (var i = 0; i < panels.length; i++) {
      if (panels[i].dataset.key === openKey) {
        panel = panels[i];
        break;
      }
    }
    if (panel) {
      panel.classList.remove("is-open");
      var body = panel.querySelector(".camera-panel-body");
      if (body) body.hidden = true;
      var btn = panel.querySelector(".camera-panel-toggle");
      if (btn) btn.setAttribute("aria-expanded", "false");
    }
    openKey = null;
  }

  function startStream(dvrId, channelId, videoEl, statusEl) {
    stopStream();
    if (typeof mpegts === "undefined" || !mpegts.getFeatureList().mseLivePlayback) {
      statusEl.textContent = HVDi18n.t("streaming.player_unsupported");
      return;
    }
    statusEl.textContent = HVDi18n.t("streaming.connecting");
    var url = wsStreamUrl(dvrId, channelId);
    var player = mpegts.createPlayer(
      {
        type: "mpegts",
        isLive: true,
        url: url,
      },
      {
        enableWorker: true,
        liveBufferLatencyChasing: true,
        liveBufferLatencyMaxLatency: 1.5,
        liveBufferLatencyMinRemain: 0.3,
      }
    );
    player.attachMediaElement(videoEl);
    player.on(mpegts.Events.ERROR, function () {
      statusEl.textContent = HVDi18n.t("streaming.stream_failed");
    });
    player.load();
    var playPromise = player.play();
    if (playPromise && typeof playPromise.then === "function") {
      playPromise
        .then(function () {
          statusEl.textContent = "";
        })
        .catch(function () {
          statusEl.textContent = HVDi18n.t("streaming.stream_failed");
        });
    } else {
      statusEl.textContent = "";
    }
    activePlayer = player;
    activeVideo = videoEl;
  }

  function openPanel(key) {
    if (openKey === key) {
      closeOpenPanel();
      return;
    }
    closeOpenPanel();
    var panel = null;
    var panels = listEl.querySelectorAll(".camera-panel");
    for (var i = 0; i < panels.length; i++) {
      if (panels[i].dataset.key === key) {
        panel = panels[i];
        break;
      }
    }
    if (!panel) return;
    openKey = key;
    panel.classList.add("is-open");
    var body = panel.querySelector(".camera-panel-body");
    var video = panel.querySelector("video");
    var statusEl = panel.querySelector(".camera-stream-status");
    var btn = panel.querySelector(".camera-panel-toggle");
    if (body) body.hidden = false;
    if (btn) btn.setAttribute("aria-expanded", "true");
    var ids = parsePanelKey(key);
    if (video && statusEl) startStream(ids.dvrId, ids.channelId, video, statusEl);
  }

  function sortedKeys(obj) {
    return Object.keys(obj).sort(function (a, b) {
      var na = String(a).toLowerCase();
      var nb = String(b).toLowerCase();
      if (na < nb) return -1;
      if (na > nb) return 1;
      return 0;
    });
  }

  function render() {
    listEl.innerHTML = "";
    var dvrKeys = sortedKeys(dvrs);
    var anyChannel = false;
    for (var d = 0; d < dvrKeys.length; d++) {
      var dvrKey = dvrKeys[d];
      var dvr = dvrs[dvrKey];
      var channels = (dvr && dvr.CHANNELS) || {};
      var chKeys = sortedKeys(channels);
      if (chKeys.length) anyChannel = true;

      var section = document.createElement("section");
      section.className = "dvr-section";

      var heading = document.createElement("h2");
      heading.className = "dvr-section-title";
      heading.textContent = (dvr && dvr.NAME) || dvrKey;
      section.appendChild(heading);

      if (!chKeys.length) {
        var none = document.createElement("p");
        none.className = "muted";
        none.textContent = HVDi18n.t("streaming.no_channels");
        section.appendChild(none);
      }

      for (var c = 0; c < chKeys.length; c++) {
        (function (dvrResponseKey, channelId) {
          var dvrId = dvrIdFromResponseKey(dvrResponseKey);
          var ch = dvrs[dvrResponseKey].CHANNELS[channelId];
          var key = panelKey(dvrId, channelId);
          var panel = document.createElement("section");
          panel.className = "camera-panel";
          panel.dataset.key = key;

          var toggle = document.createElement("button");
          toggle.type = "button";
          toggle.className = "camera-panel-toggle";
          toggle.setAttribute("aria-expanded", "false");

          var nameSpan = document.createElement("span");
          nameSpan.className = "camera-panel-name";
          nameSpan.textContent =
            (ch.NAME || channelId) + " (" + channelId + ")";
          toggle.appendChild(nameSpan);
          toggle.addEventListener("click", function () {
            openPanel(key);
          });

          var body = document.createElement("div");
          body.className = "camera-panel-body";
          body.hidden = true;

          var statusLine = document.createElement("p");
          statusLine.className = "camera-stream-status muted";

          var video = document.createElement("video");
          video.className = "camera-video";
          video.controls = true;
          video.muted = true;
          video.playsInline = true;
          video.autoplay = true;

          body.appendChild(statusLine);
          body.appendChild(video);
          panel.appendChild(toggle);
          panel.appendChild(body);
          section.appendChild(panel);
        })(dvrKey, chKeys[c]);
      }
      listEl.appendChild(section);
    }
    emptyEl.hidden = dvrKeys.length > 0;
    hintEl.hidden = !anyChannel;
  }

  function loadChannels() {
    errorEl.textContent = "";
    return HVDAuth.api("/api/streaming/channels").then(function (res) {
      if (handleAuthFailure(res)) return;
      if (!res.ok) {
        errorEl.textContent =
          (res.data && res.data.error) || HVDi18n.t("streaming.load_failed");
        dvrs = {};
        closeOpenPanel();
        render();
        return;
      }
      // Response is the DVR map itself (not wrapped).
      dvrs = res.data || {};
      var keep = openKey;
      closeOpenPanel();
      render();
      if (keep) openPanel(keep);
    });
  }

  refreshBtn.addEventListener("click", function () {
    loadChannels();
  });

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) {
      if (!openKey || hiddenTimer) return;
      hiddenTimer = setTimeout(function () {
        hiddenTimer = null;
        closeOpenPanel();
      }, HIDDEN_KILL_MS);
    } else if (hiddenTimer) {
      clearTimeout(hiddenTimer);
      hiddenTimer = null;
    }
  });

  window.addEventListener("beforeunload", function () {
    stopStream();
  });

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
      if (!HVDFeatures.isEnabled("STREAMING")) {
        errorEl.textContent = HVDi18n.t("streaming.disabled");
        HVDHeader.mount({ active: "streaming" });
        return;
      }
      HVDHeader.mount({ active: "streaming" });
      return loadChannels();
    });
})();
