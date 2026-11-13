-- Example schema for MariaDB/MySQL; review engine version, isolation and access grants.
CREATE TABLE IF NOT EXISTS ai_job (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL,
  job_uuid CHAR(36) NOT NULL,
  idempotency_key VARCHAR(128) NOT NULL,
  kind VARCHAR(32) NOT NULL,
  status VARCHAR(16) NOT NULL DEFAULT 'queued',
  attempt_count SMALLINT UNSIGNED NOT NULL DEFAULT 0,
  requested_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  started_at DATETIME(6) NULL,
  finished_at DATETIME(6) NULL,
  artifact_uuid CHAR(36) NULL,
  UNIQUE KEY uq_tenant_job (tenant_id, job_uuid),
  UNIQUE KEY uq_tenant_idempotency (tenant_id, idempotency_key),
  KEY idx_status_created (status, requested_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS ai_outbox (
  id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL,
  event_uuid CHAR(36) NOT NULL,
  job_uuid CHAR(36) NOT NULL,
  event_type VARCHAR(32) NOT NULL,
  published_at DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  UNIQUE KEY uq_tenant_event (tenant_id, event_uuid),
  KEY idx_unpublished (published_at, created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
