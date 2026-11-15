# LOCAL AI · Volume II · Multi-tenant API gateway laboratory

This lab is a **reference implementation**, not a production certification.
It fronts an existing OpenAI-compatible `/v1/chat/completions` endpoint (for
example a compatible llama.cpp server). It does not implement a new inference
protocol, Docker setup, payment provider, or GPU inference engine.

## Components

- PHP 8.2+ with PDO MySQL and cURL extensions
- MariaDB/MySQL with InnoDB transactions
- Nginx and PHP-FPM (loopback only)
- Existing inference backend on `127.0.0.1:8080`
- Bash, Python 3 and `curl` for smoke testing

## Deployment sequence (staging only)

1. Read the relevant chapters in Volume II, starting at 253.
2. Check Debian, model backend and `/v1/models`.
3. Install `nginx php-fpm php-cli php-curl php-mysql mariadb-server`.
4. Apply `sql/schema.sql` using a privileged DBA account.
5. Edit and apply `sql/grants.example.sql` using fresh secrets; never commit secrets.
6. Copy `app/` to `/opt/local-ai-gateway/app/` and make source files root-owned.
7. Copy and edit `app/config.example.php` to `/etc/local-ai/gateway.php` as root:www-data 0640.
8. Copy and edit `app/config-admin.example.php` to `/etc/local-ai/gateway-admin.php` as root:root 0600.
9. Check the PHP-FPM socket path in `ops/nginx.conf`, then `nginx -t`.
10. Run `php tests/policy_test.php` and lint the source.
11. Create synthetic tenants with the administrator-only CLI utility.
12. Verify a controlled request using `ops/gateway-smoke.sh` with a unique idempotency key.
13. Perform the negative, concurrent, recovery and privacy tests in the book.

## Secrets and responsibility boundaries

The `create_tenant.php` tool prints a new token once; use an authorized console
and a secure distribution channel. Do not paste secrets into command history,
chat conversations or incident tickets. The HTTP runtime DB account must not
be able to provision new API keys. Administrators should not expose the SQL
admin config file through the document root. This code is synchronous, has no
queue-based fairness and charges one credit per approved successful request,
not actual model tokens. It is **not ready for public internet sale** without
TLS, comprehensive rate limits, independent integration tests, billing and
financial compliance controls.

## Validation completed with the supplied release

PHP policy tests and PHP/Bash syntax checks run offline. MariaDB integration,
PHP-FPM HTTP transport, CUDA inference and GPU benchmarks are NOT_TESTED in the
artifact build environment. Perform those before production use.

## Reference URLs

- https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- https://mariadb.com/docs/server/reference/sql-statements/data-manipulation/selecting-data/for-update
- https://owasp.org/www-project-api-security/
- https://nginx.org/en/docs/http/ngx_http_limit_req_module.html
