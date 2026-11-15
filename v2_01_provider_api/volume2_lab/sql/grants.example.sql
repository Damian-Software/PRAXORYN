-- Run as a database administrator. Replace both example secrets using a safe channel.
CREATE USER IF NOT EXISTS 'gateway_runtime'@'127.0.0.1' IDENTIFIED BY 'REPLACE_RUNTIME_SECRET';
CREATE USER IF NOT EXISTS 'gateway_admin'@'127.0.0.1' IDENTIFIED BY 'REPLACE_ADMIN_SECRET';
GRANT SELECT ON local_ai_gateway.api_keys TO 'gateway_runtime'@'127.0.0.1';
GRANT SELECT, UPDATE ON local_ai_gateway.tenants TO 'gateway_runtime'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE ON local_ai_gateway.requests TO 'gateway_runtime'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE ON local_ai_gateway.tenants TO 'gateway_admin'@'127.0.0.1';
GRANT SELECT, INSERT, UPDATE ON local_ai_gateway.api_keys TO 'gateway_admin'@'127.0.0.1';
GRANT SELECT, UPDATE ON local_ai_gateway.requests TO 'gateway_admin'@'127.0.0.1';
