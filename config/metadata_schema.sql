-- Metadata-only example. Review privileges, retention, and migrations before use.
CREATE TABLE model_alias (
    alias VARCHAR(80) PRIMARY KEY,
    backend VARCHAR(80) NOT NULL,
    model_identifier VARCHAR(160) NOT NULL,
    revision VARCHAR(120) NOT NULL,
    enabled TINYINT(1) NOT NULL DEFAULT 0,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE job (
    id CHAR(36) PRIMARY KEY,
    principal_id VARCHAR(100) NOT NULL,
    model_alias VARCHAR(80) NOT NULL,
    state VARCHAR(20) NOT NULL,
    idempotency_key CHAR(64) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    UNIQUE KEY uq_job_principal_operation (principal_id, idempotency_key),
    INDEX idx_job_expiry (expires_at),
    CONSTRAINT fk_job_model FOREIGN KEY (model_alias)
        REFERENCES model_alias(alias)
) ENGINE=InnoDB;

CREATE TABLE audit_event (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    request_id CHAR(36) NOT NULL,
    principal_ref VARCHAR(100) NOT NULL,
    action_name VARCHAR(80) NOT NULL,
    decision VARCHAR(20) NOT NULL,
    reason_code VARCHAR(40) NOT NULL,
    INDEX idx_audit_time (occurred_at),
    INDEX idx_audit_request (request_id)
) ENGINE=InnoDB;
