-- Filenames were GMT+3 but previously stored as if UTC. Shift existing rows to real UTC.
UPDATE alert
SET timestamp = timestamp - INTERVAL '3 hours';

UPDATE alert_thumbnail
SET timestamp = timestamp - INTERVAL '3 hours';
