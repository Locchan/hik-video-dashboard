-- Feature enable/disable flags (name + enabled). Descriptions live in application code.
CREATE TABLE IF NOT EXISTS features (
    name TEXT NOT NULL PRIMARY KEY,
    enabled BOOLEAN NOT NULL DEFAULT FALSE
);
