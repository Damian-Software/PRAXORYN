-- MariaDB 10.6+ / MySQL 8.0+; use InnoDB and utf8mb4.
CREATE DATABASE IF NOT EXISTS local_ai_gateway CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE local_ai_gateway;

CREATE TABLE tenants (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    slug VARCHAR(64) NOT NULL UNIQUE,
    active TINYINT(1) NOT NULL DEFAULT 1,
    remaining_units BIGINT UNSIGNED NOT NULL DEFAULT 0,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE api_keys (
    id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    key_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL UNIQUE,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    revoked_at TIMESTAMP NULL,
    CONSTRAINT fk_api_keys_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
) ENGINE=InnoDB;

CREATE TABLE requests (
    request_id CHAR(36) CHARACTER SET ascii COLLATE ascii_bin NOT NULL PRIMARY KEY,
    tenant_id BIGINT UNSIGNED NOT NULL,
    idem_hash CHAR(64) CHARACTER SET ascii COLLATE ascii_bin NOT NULL,
    status ENUM('reserved', 'succeeded', 'failed', 'expired') NOT NULL,
    reserved_units SMALLINT UNSIGNED NOT NULL DEFAULT 1,
    latency_ms INT UNSIGNED NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP NULL,
    UNIQUE KEY uq_tenant_idem (tenant_id, idem_hash),
    KEY ix_requests_pending (status, created_at),
    CONSTRAINT fk_requests_tenant FOREIGN KEY (tenant_id) REFERENCES tenants(id)
) ENGINE=InnoDB;
