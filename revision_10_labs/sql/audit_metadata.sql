-- MySQL 8 / MariaDB 10.6+; intentionally does not store prompts, responses, IPs or tokens.
CREATE DATABASE IF NOT EXISTS localai_ops
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE localai_ops;
CREATE TABLE IF NOT EXISTS api_audit (
  id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
  created_at TIMESTAMP(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  request_id VARCHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
  event_type VARCHAR(40) NOT NULL,
  http_status SMALLINT UNSIGNED NOT NULL,
  duration_ms INT UNSIGNED NOT NULL,
  INDEX idx_audit_time (created_at),
  INDEX idx_audit_event_time (event_type, created_at)
) ENGINE=InnoDB;
-- Create an application account separately and grant INSERT only when appropriate.
-- Example manual retention, after testing/backups and legal review:
-- DELETE FROM api_audit WHERE created_at < NOW() - INTERVAL 7 DAY;
