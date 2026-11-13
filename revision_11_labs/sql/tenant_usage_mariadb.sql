-- Demonstration schema. Apply least-privilege user grants separately.
CREATE TABLE tenant_usage (
  tenant_id VARBINARY(64) NOT NULL,
  period_start DATE NOT NULL,
  token_limit BIGINT UNSIGNED NOT NULL,
  used_tokens BIGINT UNSIGNED NOT NULL DEFAULT 0,
  PRIMARY KEY (tenant_id, period_start),
  CHECK (used_tokens <= token_limit)
) ENGINE=InnoDB;
CREATE TABLE usage_events (
  tenant_id VARBINARY(64) NOT NULL,
  request_id VARBINARY(64) NOT NULL,
  occurred_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
  model_code VARCHAR(100) NOT NULL,
  input_tokens INT UNSIGNED NOT NULL,
  output_tokens INT UNSIGNED NOT NULL,
  state ENUM('reserved','confirmed','reversed') NOT NULL,
  PRIMARY KEY (tenant_id, request_id),
  INDEX idx_occurred_at (occurred_at)
) ENGINE=InnoDB;
-- Do not store prompts, completions, Authorization headers or secret API keys here.
