-- Marker migration: records that the HVD migration harness is active.
-- Auth/config baseline tables are still created via SQLAlchemy create_all;
-- subsequent schema changes belong in later YYYYMMDDHHMMSS_*.sql files (PostgreSQL).
SELECT 1;
