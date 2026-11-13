# Local AI Portal — practical lab for Volume I

This is a **single-client, loopback-only internal pilot**. It consumes an existing llama.cpp-compatible chat completions endpoint. It is **not a production-ready paid multi-tenant service**.

## Included files

- `portal/public/index.html`: browser UI, never persists the client token.
- `portal/public/api/chat.php`: guarded request path to the existing inference API.
- `portal/lib/Policy.php`: bearer-token check, input validation, fixed request policy.
- `portal/config.example.php`: placeholder configuration; install outside the web root.
- `portal/schema.sql`: metadata-only audit table.
- `ops/portal-nginx.conf`: loopback-bound Nginx and PHP-FPM example.
- `ops/pilot-smoke.sh`: live smoke test; requires a working local backend and DB.
- `tests/policy_test.php`: offline policy unit tests, independent of GPU/DB.

## Safe development sequence

1. Read chapters 238–252. Verify Debian 13, PHP-FPM socket, and the model server.
2. Run `php tests/policy_test.php` and `find portal -name '*.php' -exec php -l {} \;`.
3. Create the restricted `/etc/local-ai/` directory and install PHP configuration outside the Nginx webroot.
4. Generate a client token with `openssl rand -hex 32`; store only its SHA-256 hash in the PHP configuration. Put the **separate** model-server token in the `upstream_token` setting.
5. Create the MariaDB audit schema and the INSERT-only application account.
6. Copy `portal/public` and `portal/lib` to `/var/www/local-ai/`; use `root:www-data` ownership and non-writable PHP source permissions.
7. Install and verify the supplied Nginx server block, adjusting the PHP-FPM socket to the installed version.
8. Only after the inference endpoint and DB are working, run `AI_CLIENT_TOKEN=... ops/pilot-smoke.sh` on the local test host. For a real secret, read it interactively rather than storing it in shell history.
9. Confirm no public network listener and no prompt/answer content in audit rows.

Security limitations: one client token, no per-tenant identities, no metered billing, no TLS termination, and simple per-IP rate limiting. Do not open this example to the Internet or regulated personal data before a dedicated security and legal review. Do not count unit tests as production acceptance tests.
