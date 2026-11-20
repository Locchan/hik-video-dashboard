/**
 * Help catalog: feature ids + config/env option keys.
 * Descriptions live in i18n (help.<FEATURE>.body / help.<FEATURE>.opt.<id>).
 * Keep in sync when adding features or config keys (see .cursor/rules/hvd-feature-help.mdc).
 */
(function (global) {
  global.HVDHelpContent = {
    features: [
      {
        id: "CONFIG",
        options: [
          { id: "language", key: "language" },
        ],
      },
      {
        id: "ALERT_VIEW",
        options: [
          { id: "ALERTS_DIR", key: "ALERTS_DIR", kind: "env" },
        ],
      },
      {
        id: "STREAMING",
        options: [
          { id: "NAME", key: "STREAMING_DVR_X_NAME" },
          { id: "HTTP_ADDR", key: "STREAMING_DVR_X_HTTP_ADDR" },
          { id: "RTSP_ADDR", key: "STREAMING_DVR_X_RTSP_ADDR" },
          { id: "USERNAME", key: "STREAMING_DVR_X_USERNAME" },
          { id: "PASSWORD", key: "STREAMING_DVR_X_PASSWORD" },
          { id: "CH_NAME", key: "STREAMING_DVR_X_CH_Y_NAME" },
        ],
      },
    ],
  };
})(window);
