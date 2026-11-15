-- Alert clip index and cached PNG thumbnails.
CREATE TABLE IF NOT EXISTS alert (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    camera TEXT NOT NULL,
    path TEXT NOT NULL,
    CONSTRAINT uq_alert_camera_timestamp UNIQUE (camera, timestamp),
    CONSTRAINT uq_alert_path UNIQUE (path)
);

CREATE TABLE IF NOT EXISTS alert_thumbnail (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMPTZ NOT NULL,
    camera TEXT NOT NULL,
    png BYTEA NOT NULL,
    CONSTRAINT uq_alert_thumbnail_camera_timestamp UNIQUE (camera, timestamp)
);
