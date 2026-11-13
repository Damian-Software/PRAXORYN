CREATE DATABASE IF NOT EXISTS local_ai CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE local_ai;
CREATE TABLE IF NOT EXISTS request_audit (
    request_id CHAR(24) PRIMARY KEY,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status_code SMALLINT UNSIGNED NOT NULL,
    upstream_status SMALLINT UNSIGNED NOT NULL,
    duration_ms INT UNSIGNED NOT NULL,
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB;
-- Create an application account separately and grant INSERT only.
-- No prompts, answers, bearer tokens or client IP addresses are stored here.
