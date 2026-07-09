-- Migration 001: Add roboflow_image_id column to images table
-- The column was added to the SQLAlchemy Image model but the PostgreSQL
-- table was created before this column existed.
--
-- Applied automatically on application startup by app/db/migrate.py.

ALTER TABLE images
ADD COLUMN IF NOT EXISTS roboflow_image_id VARCHAR(64) NULL;
