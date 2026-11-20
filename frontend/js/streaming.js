(function () {
  if (!HVDAuth.requireSession("/")) return;
  HVDi18n.initFromSystem();

  var listEl = document.getElementById("camera-list");
  var errorEl = document.getElementById("streaming-error");
  var emptyEl = document.getElementById("streaming-empty");
  var hintEl = document.getElementById("streaming-hint");
  var refreshBtn = document.getElementById("btn-refresh");

  var HIDDEN_KILL_MS = 30000;
  var NO_DATA_UI_MS = 10000;
  /** @type {Object<string, {NAME: string, CHANNELS: Object}>} */
  var dvrs = {};
  var openKey = null; // "dvrId\\tchannelId"
  /** @type {string|null} datetime-local value, or null for live */
  var playbackStart = null;
  /** @type {Object<string, {min: string|null, max: string|null}|undefined>} */
  var archiveBounds = {};
  var activePlayer = null;
  var activeVideo = null;
  var activeWs = null;
  var hiddenTimer = null;
  var noDataTimer = null;
  var sawMedia = false;

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
    if (String(key).indexOf("DVR_") === 0) return String(key).slice(4);
    return String(key);
  }

  function wsStreamUrl(dvrId, channelId, start) {
    var proto = window.location.protocol === "https:" ? "wss:" : "ws:";
    var url =
      proto +
      "//" +
      window.location.host +
      "/ws/streaming/stream?dvr=" +
      encodeURIComponent(dvrId) +
      "&channel=" +
      encodeURIComponent(channelId);
    if (start) url += "&start=" + encodeURIComponent(start);
    return url;
  }

  function clearNoDataTimer() {
    if (noDataTimer) {
      clearTimeout(noDataTimer);
      noDataTimer = null;
    }
  }

  function stopStream() {
    clearNoDataTimer();
    if (hiddenTimer) {
      clearTimeout(hiddenTimer);
      hiddenTimer = null;
    }
    if (activeWs) {
      try {
        activeWs.onmessage = null;
        activeWs.onerror = null;
        activeWs.onclose = null;
        activeWs.close();
      } catch (e) {}
      activeWs = null;
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
    sawMedia = false;
  }

  function findOpenPanel() {
    if (openKey == null) return null;
    var panels = listEl.querySelectorAll(".camera-panel");
    for (var i = 0; i < panels.length; i++) {
      if (panels[i].dataset.key === openKey) return panels[i];
    }
    return null;
  }

  function closeOpenPanel() {
    stopStream();
    var panel = findOpenPanel();
    if (panel) {
      hideCalendarPanel(panel);
      destroyPlaybackPicker(panel);
      panel.classList.remove("is-open");
      var body = panel.querySelector(".camera-panel-body");
      if (body) body.hidden = true;
      var btn = panel.querySelector(".camera-panel-toggle");
      if (btn) btn.setAttribute("aria-expanded", "false");
    }
    openKey = null;
  }

  function showNoRecording(statusEl) {
    statusEl.className = "camera-stream-status stream-no-data";
    statusEl.textContent = HVDi18n.t("streaming.no_recording");
  }

  function showStatus(statusEl, text, isError) {
    statusEl.className =
      "camera-stream-status" + (isError ? " stream-no-data" : " muted");
    statusEl.textContent = text || "";
  }

  function markMedia(statusEl) {
    if (sawMedia) return;
    sawMedia = true;
    clearNoDataTimer();
    showStatus(statusEl, "", false);
  }

  /**
   * Own the WebSocket so JSON {code:no_recording} from the server is readable.
   * Binary MPEG-TS is handed to mpegts via a second connection on the same URL
   * once we know data exists (probe closes immediately after first TS byte).
   */
  function startStream(dvrId, channelId, videoEl, statusEl) {
    stopStream();
    if (typeof mpegts === "undefined" || !mpegts.getFeatureList().mseLivePlayback) {
      showStatus(statusEl, HVDi18n.t("streaming.player_unsupported"), true);
      return;
    }
    var isPlayback = !!playbackStart;
    showStatus(
      statusEl,
      isPlayback
        ? HVDi18n.t("streaming.connecting_playback")
        : HVDi18n.t("streaming.connecting"),
      false
    );

    var url = wsStreamUrl(dvrId, channelId, playbackStart);
    var ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";
    activeWs = ws;
    activeVideo = videoEl;
    var handedOff = false;

    noDataTimer = setTimeout(function () {
      noDataTimer = null;
      if (!handedOff && !sawMedia) {
        try {
          ws.close();
        } catch (e) {}
        showNoRecording(statusEl);
        stopStream();
      }
    }, NO_DATA_UI_MS);

    ws.onmessage = function (ev) {
      if (typeof ev.data === "string") {
        clearNoDataTimer();
        var msg = {};
        try {
          msg = JSON.parse(ev.data);
        } catch (e) {
          msg = { error: ev.data };
        }
        if (msg.code === "no_recording" || isPlayback) {
          showNoRecording(statusEl);
        } else {
          showStatus(
            statusEl,
            msg.error || HVDi18n.t("streaming.stream_failed"),
            true
          );
        }
        try {
          ws.close();
        } catch (e2) {}
        return;
      }
      if (handedOff) return;
      handedOff = true;
      clearNoDataTimer();
      try {
        ws.onmessage = null;
        ws.close();
      } catch (e) {}
      activeWs = null;
      attachMpegts(url, videoEl, statusEl, isPlayback);
    };

    ws.onerror = function () {
      if (handedOff) return;
      clearNoDataTimer();
      if (isPlayback) showNoRecording(statusEl);
      else showStatus(statusEl, HVDi18n.t("streaming.stream_failed"), true);
    };
  }

  function attachMpegts(url, videoEl, statusEl, isPlayback) {
    var player = mpegts.createPlayer(
      {
        type: "mpegts",
        isLive: !isPlayback,
        url: url,
      },
      {
        enableWorker: true,
        liveBufferLatencyChasing: !isPlayback,
        liveBufferLatencyMaxLatency: 1.5,
        liveBufferLatencyMinRemain: 0.3,
      }
    );
    player.attachMediaElement(videoEl);
    player.on(mpegts.Events.ERROR, function () {
      if (!sawMedia && isPlayback) showNoRecording(statusEl);
      else if (!sawMedia) {
        showStatus(statusEl, HVDi18n.t("streaming.stream_failed"), true);
      }
    });
    videoEl.addEventListener(
      "loadeddata",
      function onLoaded() {
        videoEl.removeEventListener("loadeddata", onLoaded);
        markMedia(statusEl);
      }
    );
    videoEl.addEventListener(
      "playing",
      function onPlaying() {
        videoEl.removeEventListener("playing", onPlaying);
        markMedia(statusEl);
      }
    );
    player.load();
    var playPromise = player.play();
    if (playPromise && typeof playPromise.then === "function") {
      playPromise
        .then(function () {
          markMedia(statusEl);
        })
        .catch(function () {
          if (!sawMedia && isPlayback) showNoRecording(statusEl);
          else if (!sawMedia) {
            showStatus(statusEl, HVDi18n.t("streaming.stream_failed"), true);
          }
        });
    }
    activePlayer = player;
    activeVideo = videoEl;

    // Second chance watchdog after handoff (ffmpeg may still die empty).
    noDataTimer = setTimeout(function () {
      noDataTimer = null;
      if (!sawMedia) {
        if (isPlayback) showNoRecording(statusEl);
        else showStatus(statusEl, HVDi18n.t("streaming.stream_failed"), true);
        stopStream();
      }
    }, NO_DATA_UI_MS);
  }

  function clampDateTimeLocal(value, min, max) {
    var v = value || "";
    if (min && (!v || v < min)) v = min;
    if (max && (!v || v > max)) v = max;
    return v;
  }

  function ymdFromDate(d) {
    var y = d.getFullYear();
    var m = String(d.getMonth() + 1).padStart(2, "0");
    var day = String(d.getDate()).padStart(2, "0");
    return y + "-" + m + "-" + day;
  }

  function flatpickrLocale() {
    var lang = (HVDi18n.getLanguage && HVDi18n.getLanguage()) || "en";
    if (
      lang === "ru" &&
      typeof flatpickr !== "undefined" &&
      flatpickr.l10ns &&
      flatpickr.l10ns.ru
    ) {
      return flatpickr.l10ns.ru;
    }
    return "default";
  }

  function destroyPlaybackPicker(panel) {
    if (!panel) return;
    var input = panel.querySelector(".playback-start");
    if (input && input._flatpickr) {
      try {
        input._flatpickr.destroy();
      } catch (e) {}
    }
  }

  function hideCalendarPanel(panel) {
    if (!panel) return;
    var cal = panel.querySelector(".stream-calendar-panel");
    if (cal) cal.hidden = true;
  }

  function showCalendarPanel(panel) {
    if (!panel) return;
    var cal = panel.querySelector(".stream-calendar-panel");
    if (cal) cal.hidden = false;
  }

  function mountPlaybackPicker(panel, bounds) {
    if (!panel || typeof flatpickr === "undefined") return null;
    var input = panel.querySelector(".playback-start");
    var host = panel.querySelector(".stream-calendar-host");
    if (!input || !host) return null;
    destroyPlaybackPicker(panel);
    var daySet = {};
    var days = (bounds && bounds.days) || [];
    for (var i = 0; i < days.length; i++) daySet[days[i]] = true;
    var hasDays = days.length > 0;
    var seed =
      playbackStart ||
      (bounds && bounds.max) ||
      defaultDateTimeLocalValue();
    if (bounds && bounds.min && bounds.max) {
      seed = clampDateTimeLocal(seed, bounds.min, bounds.max);
    }
    var cfg = {
      enableTime: true,
      time_24hr: true,
      minuteIncrement: 1,
      allowInput: false,
      clickOpens: false,
      disableMobile: true,
      inline: true,
      static: true,
      appendTo: host,
      dateFormat: "Y-m-d\\TH:i",
      locale: flatpickrLocale(),
      defaultDate: seed,
    };
    if (bounds && bounds.min) cfg.minDate = bounds.min.slice(0, 10);
    if (bounds && bounds.max) cfg.maxDate = bounds.max.slice(0, 10);
    if (hasDays) {
      cfg.enable = [
        function (date) {
          return !!daySet[ymdFromDate(date)];
        },
      ];
    }
    return flatpickr(input, cfg);
  }

  function applyArchiveBounds(panel, bounds) {
    if (!panel) return;
    var applyBtn = panel.querySelector(".btn-apply-time");
    var calNote = panel.querySelector(".stream-calendar-note");
    var recordingBtn = panel.querySelector(".btn-recording");
    if (bounds && bounds.min && bounds.max) {
      if (calNote) {
        calNote.hidden = true;
        calNote.textContent = "";
      }
      if (applyBtn) {
        applyBtn.disabled = false;
        applyBtn.title = "";
      }
      if (recordingBtn) recordingBtn.disabled = false;
      mountPlaybackPicker(panel, bounds);
    } else {
      destroyPlaybackPicker(panel);
      if (calNote) {
        calNote.hidden = false;
        calNote.textContent = HVDi18n.t("streaming.no_archive");
      }
      if (applyBtn) {
        applyBtn.disabled = true;
        applyBtn.title = HVDi18n.t("streaming.no_archive");
      }
    }
  }

  function loadArchiveBounds(dvrId, channelId, panel) {
    var key = panelKey(dvrId, channelId);
    var cached = archiveBounds[key];
    if (cached !== undefined) {
      applyArchiveBounds(panel, cached);
      return Promise.resolve(cached);
    }
    var path =
      "/api/streaming/recordings?dvr=" +
      encodeURIComponent(dvrId) +
      "&channel=" +
      encodeURIComponent(channelId);
    return HVDAuth.api(path).then(function (res) {
      if (handleAuthFailure(res)) return null;
      var bounds =
        res.ok && res.data
          ? {
              min: res.data.min || null,
              max: res.data.max || null,
              days: res.data.days || [],
            }
          : { min: null, max: null, days: [] };
      archiveBounds[key] = bounds;
      if (openKey !== key) return bounds;
      applyArchiveBounds(panel, bounds);
      return bounds;
    });
  }

  function syncTimeControls(panel) {
    if (!panel) return;
    var liveBtn = panel.querySelector(".btn-live");
    var recordingBtn = panel.querySelector(".btn-recording");
    var nowEl = panel.querySelector(".playback-now");
    var isLive = !playbackStart;
    if (liveBtn) liveBtn.disabled = isLive;
    if (recordingBtn) recordingBtn.disabled = false;
    if (nowEl) {
      var mode = isLive
        ? HVDi18n.t("streaming.mode_live")
        : HVDi18n.t("streaming.mode_playback");
      nowEl.textContent = HVDi18n.t("streaming.currently_playing", {
        mode: mode,
      });
    }
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
    syncTimeControls(panel);
    var ids = parsePanelKey(key);
    loadArchiveBounds(ids.dvrId, ids.channelId, panel);
    if (video && statusEl) startStream(ids.dvrId, ids.channelId, video, statusEl);
  }

  function restartOpenStream() {
    var panel = findOpenPanel();
    if (!panel || !openKey) return;
    syncTimeControls(panel);
    var ids = parsePanelKey(openKey);
    var video = panel.querySelector("video");
    var statusEl = panel.querySelector(".camera-stream-status");
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

  function defaultDateTimeLocalValue() {
    var d = new Date();
    d.setSeconds(0, 0);
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16);
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

          var toolbar = document.createElement("div");
          toolbar.className = "stream-toolbar";

          var modeBlock = document.createElement("div");
          modeBlock.className = "stream-mode-block";

          var viewLabel = document.createElement("span");
          viewLabel.className = "stream-view-label";
          viewLabel.textContent = HVDi18n.t("streaming.view");

          var modeButtons = document.createElement("div");
          modeButtons.className = "stream-mode-buttons";

          var liveBtn = document.createElement("button");
          liveBtn.type = "button";
          liveBtn.className = "btn btn-live";
          liveBtn.textContent = HVDi18n.t("streaming.live");
          liveBtn.disabled = true;
          liveBtn.addEventListener("click", function () {
            hideCalendarPanel(panel);
            playbackStart = null;
            restartOpenStream();
          });

          var recordingBtn = document.createElement("button");
          recordingBtn.type = "button";
          recordingBtn.className = "btn btn-recording";
          recordingBtn.textContent = HVDi18n.t("streaming.recording");
          recordingBtn.addEventListener("click", function () {
            showCalendarPanel(panel);
            var bounds = archiveBounds[key];
            if (bounds) applyArchiveBounds(panel, bounds);
            else {
              var note = panel.querySelector(".stream-calendar-note");
              if (note) {
                note.hidden = false;
                note.textContent = HVDi18n.t("streaming.loading_archive");
              }
              loadArchiveBounds(dvrId, channelId, panel);
            }
          });

          modeButtons.appendChild(liveBtn);
          modeButtons.appendChild(recordingBtn);
          modeBlock.appendChild(viewLabel);
          modeBlock.appendChild(modeButtons);

          var nowEl = document.createElement("span");
          nowEl.className = "playback-now muted";
          nowEl.textContent = HVDi18n.t("streaming.currently_playing", {
            mode: HVDi18n.t("streaming.mode_live"),
          });

          var calendarPanel = document.createElement("div");
          calendarPanel.className = "stream-calendar-panel";
          calendarPanel.hidden = true;

          var calendarNote = document.createElement("p");
          calendarNote.className = "stream-calendar-note muted";
          calendarNote.hidden = true;

          var calendarHost = document.createElement("div");
          calendarHost.className = "stream-calendar-host";

          var timeInput = document.createElement("input");
          timeInput.type = "text";
          timeInput.className = "playback-start";
          timeInput.tabIndex = -1;
          timeInput.setAttribute("aria-hidden", "true");
          timeInput.value = defaultDateTimeLocalValue();

          var calendarActions = document.createElement("div");
          calendarActions.className = "stream-calendar-actions";

          var applyBtn = document.createElement("button");
          applyBtn.type = "button";
          applyBtn.className = "btn btn-apply-time";
          applyBtn.textContent = HVDi18n.t("streaming.apply");
          applyBtn.addEventListener("click", function () {
            var statusLine = panel.querySelector(".camera-stream-status");
            var fp = timeInput._flatpickr;
            var val = "";
            if (fp && fp.selectedDates && fp.selectedDates[0]) {
              val = fp.formatDate(fp.selectedDates[0], "Y-m-d\\TH:i");
            } else {
              val = (timeInput.value || "").trim().replace(" ", "T");
            }
            if (!val) {
              if (statusLine) {
                showStatus(statusLine, HVDi18n.t("streaming.time_required"), true);
              }
              return;
            }
            var bounds = archiveBounds[key];
            if (bounds && bounds.min && bounds.max) {
              val = clampDateTimeLocal(val, bounds.min, bounds.max);
            }
            applyBtn.disabled = true;
            if (statusLine) {
              showStatus(statusLine, HVDi18n.t("streaming.loading_archive"), false);
            }
            var checkPath =
              "/api/streaming/recordings?dvr=" +
              encodeURIComponent(dvrId) +
              "&channel=" +
              encodeURIComponent(channelId) +
              "&at=" +
              encodeURIComponent(val);
            HVDAuth.api(checkPath).then(function (res) {
              applyBtn.disabled = false;
              if (handleAuthFailure(res)) return;
              if (
                !res.ok ||
                !res.data ||
                !res.data.available ||
                !res.data.start
              ) {
                if (statusLine) showNoRecording(statusLine);
                return;
              }
              playbackStart = res.data.start;
              hideCalendarPanel(panel);
              restartOpenStream();
            });
          });

          calendarActions.appendChild(applyBtn);
          calendarHost.appendChild(timeInput);
          calendarPanel.appendChild(calendarNote);
          calendarPanel.appendChild(calendarHost);
          calendarPanel.appendChild(calendarActions);
          modeBlock.appendChild(calendarPanel);

          toolbar.appendChild(modeBlock);
          toolbar.appendChild(nowEl);

          var statusLine = document.createElement("p");
          statusLine.className = "camera-stream-status muted";

          var video = document.createElement("video");
          video.className = "camera-video";
          video.controls = false;
          video.muted = true;
          video.playsInline = true;
          video.autoplay = true;

          var pauseBtn = document.createElement("button");
          pauseBtn.type = "button";
          pauseBtn.className = "btn stream-play-pause";
          pauseBtn.textContent = HVDi18n.t("streaming.pause");

          function syncPauseBtn() {
            pauseBtn.textContent = video.paused
              ? HVDi18n.t("streaming.play")
              : HVDi18n.t("streaming.pause");
          }

          function togglePause() {
            if (video.paused) {
              var p = video.play();
              if (p && typeof p.catch === "function") p.catch(function () {});
            } else {
              video.pause();
            }
            syncPauseBtn();
          }

          pauseBtn.addEventListener("click", togglePause);
          video.addEventListener("click", togglePause);
          video.addEventListener("play", syncPauseBtn);
          video.addEventListener("pause", syncPauseBtn);

          body.appendChild(toolbar);
          body.appendChild(statusLine);
          body.appendChild(video);
          body.appendChild(pauseBtn);
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
    archiveBounds = {};
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
