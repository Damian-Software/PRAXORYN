-- Educational MariaDB/MySQL schema; review version-specific syntax.
CREATE TABLE generated_artifacts (
    artifact_id CHAR(36) PRIMARY KEY,
    owner_id VARCHAR(128) NOT NULL,
    job_id CHAR(36) NOT NULL,
    artifact_kind VARCHAR(32) NOT NULL,
    media_type VARCHAR(100) NOT NULL,
    storage_key VARCHAR(512) NOT NULL,
    sha256 CHAR(64) NOT NULL,
    size_bytes BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    expires_at TIMESTAMP NULL,
    INDEX idx_artifact_owner (owner_id),
    INDEX idx_artifact_job (job_id)
);
