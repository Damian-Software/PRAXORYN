-- Reference schema for MariaDB/MySQL (InnoDB). Review for installed versions.
-- All application queries MUST scope by the authenticated tenant and subject.
CREATE TABLE agent_jobs (
  job_id CHAR(36) NOT NULL,
  tenant_id VARCHAR(64) NOT NULL,
  owner_subject VARCHAR(128) NOT NULL,
  operation VARCHAR(64) NOT NULL,
  state VARCHAR(24) NOT NULL,
  idempotency_key VARCHAR(128) NOT NULL,
  input_digest CHAR(64) NOT NULL,
  attempt_count INT UNSIGNED NOT NULL DEFAULT 0,
  lease_token VARCHAR(64) NULL,
  lease_until DATETIME(6) NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  PRIMARY KEY (job_id),
  UNIQUE KEY uq_job_dedup (tenant_id, owner_subject, idempotency_key),
  KEY idx_work_queue (state, lease_until, created_at),
  KEY idx_tenant_jobs (tenant_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE agent_outbox (
  event_id CHAR(36) NOT NULL PRIMARY KEY,
  tenant_id VARCHAR(64) NOT NULL,
  job_id CHAR(36) NOT NULL,
  event_type VARCHAR(64) NOT NULL,
  delivery_state VARCHAR(24) NOT NULL,
  created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
  KEY idx_outbox_delivery (delivery_state, created_at),
  CONSTRAINT fk_outbox_job FOREIGN KEY (job_id) REFERENCES agent_jobs(job_id)
) ENGINE=InnoDB;

-- Pseudocode outline (not an atomic script):
-- START TRANSACTION;
-- SELECT job_id FROM agent_jobs WHERE state='queued' ORDER BY created_at
--   LIMIT 1 FOR UPDATE SKIP LOCKED;
-- UPDATE agent_jobs SET state='leased', lease_token=?, lease_until=? WHERE job_id=?;
-- COMMIT;
-- Then execute outside the transaction. Only the current token may complete.
