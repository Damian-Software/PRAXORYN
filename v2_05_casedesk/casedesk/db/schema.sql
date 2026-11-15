CREATE DATABASE IF NOT EXISTS casedesk CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE casedesk;
CREATE TABLE IF NOT EXISTS users (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    email VARCHAR(190) NOT NULL UNIQUE,
    pass_hash VARCHAR(255) NOT NULL,
    role ENUM('admin','reviewer','viewer') NOT NULL,
    active TINYINT(1) NOT NULL DEFAULT 1,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS cases (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    subject VARCHAR(180) NOT NULL,
    body TEXT NOT NULL,
    classification ENUM('public','internal','restricted') NOT NULL,
    status ENUM('queued','manual_only','processing','pending_review','approved','rejected','failed') NOT NULL,
    created_by BIGINT UNSIGNED NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    claimed_at TIMESTAMP NULL DEFAULT NULL,
    error_code VARCHAR(60) DEFAULT NULL,
    FOREIGN KEY (created_by) REFERENCES users(id),
    INDEX idx_worker (status, id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS drafts (
    case_id BIGINT UNSIGNED PRIMARY KEY,
    content TEXT NOT NULL,
    reviewed_by BIGINT UNSIGNED NULL,
    reviewed_at TIMESTAMP NULL DEFAULT NULL,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE CASCADE,
    FOREIGN KEY (reviewed_by) REFERENCES users(id)
) ENGINE=InnoDB;
CREATE TABLE IF NOT EXISTS audit_events (
    id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
    case_id BIGINT UNSIGNED NULL,
    actor_id BIGINT UNSIGNED NULL,
    action VARCHAR(60) NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (case_id) REFERENCES cases(id) ON DELETE SET NULL,
    INDEX idx_audit (created_at)
) ENGINE=InnoDB;
