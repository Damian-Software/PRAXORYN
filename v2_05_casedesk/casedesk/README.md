# CaseDesk — local AI-assisted casework (Debian 13)

This is a **single-organization reference application**, not a public SaaS platform. It uses PHP 8.4, MariaDB 11.8, Nginx, a one-shot systemd worker, and an already-running OpenAI-style chat completions API. No automatic external e-mail is sent. Drafts require explicit human approval.

## Prerequisites

- Debian 13 (physical/VM) or WSL2 Debian 13 (development only)
- Existing inference service on `127.0.0.1:8080` with `/v1/models` and `/v1/chat/completions`
- `sudo apt install nginx php-fpm php-cli php-mysql php-curl mariadb-server mariadb-client curl`
- `sudo systemctl enable --now mariadb php8.4-fpm nginx`
- Verify `php -m | grep -E 'PDO|pdo_mysql|curl'` and `sudo nginx -t`.

## Database (operator-controlled)

`sudo mariadb < db/schema.sql` creates the database/tables. **Do not use the application database user for schema management.** In `sudo mariadb`, manually create a narrowly scoped service account:

```sql
CREATE USER 'casedesk_app'@'127.0.0.1' IDENTIFIED BY 'REPLACE_WITH_RANDOM_PASSWORD';
GRANT SELECT, INSERT, UPDATE, DELETE ON casedesk.* TO 'casedesk_app'@'127.0.0.1';
```

Use a randomly generated password. Store it only in `/etc/casedesk.ini` mode `0640`, owned by `root:www-data`. This demonstration permits the service account to write each application table. A mature deployment should split frontend/worker identities and tighten grants further.

## Install files

```bash
sudo install -d -o root -g www-data -m 0750 /srv/casedesk
sudo cp -r app public bin /srv/casedesk/
sudo find /srv/casedesk -type d -exec chmod 0750 {} \;
sudo find /srv/casedesk -type f -exec chmod 0640 {} \;
sudo chown -R root:www-data /srv/casedesk
sudo cp config/casedesk.ini.example /etc/casedesk.ini
sudo chown root:www-data /etc/casedesk.ini
sudo chmod 0640 /etc/casedesk.ini
sudoedit /etc/casedesk.ini
sudo cp ops/casedesk.nginx /etc/nginx/sites-available/casedesk
sudo ln -s /etc/nginx/sites-available/casedesk /etc/nginx/sites-enabled/casedesk
sudo nginx -t && sudo systemctl reload nginx
```

In `/etc/casedesk.ini`, replace `REPLACE_*`, verify `model.id` from `GET /v1/models`, and keep `secure_cookie=false` **only** for loopback HTTP experiments. Before TLS exposure set it to `true`.

## Create admin account

Do not place a real password in shell arguments or source files. Execute:

```bash
read -rsp 'New admin password (16+ chars): ' CASEDESK_PASSWORD; printf '\n'
printf '%s\n' "$CASEDESK_PASSWORD" | sudo -u www-data php /srv/casedesk/bin/create_admin.php admin@example.invalid
unset CASEDESK_PASSWORD
```

The admin address shown is a placeholder. Use a dedicated operator account, not a customer account.

## Worker service

```bash
sudo cp ops/casedesk-worker.service /etc/systemd/system/
sudo cp ops/casedesk-worker.timer /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now casedesk-worker.timer
systemctl list-timers casedesk-worker.timer
journalctl -u casedesk-worker.service -n 20 --no-pager
```

Open `http://127.0.0.1:8088/` on the same Debian machine (or through an explicitly controlled development tunnel). Create a synthetic case classified as `public`, wait for the timer and review the AI-generated draft. The application will **not** send it anywhere automatically. A `restricted` case remains `manual_only`.

## Troubleshooting

```bash
curl -fsS http://127.0.0.1:8080/v1/models
curl -fsS http://127.0.0.1:8088/?action=health
sudo nginx -t
sudo systemctl status php8.4-fpm mariadb casedesk-worker.timer --no-pager
sudo journalctl -u casedesk-worker.service --since '-15 min' --no-pager
sudo -u www-data php /srv/casedesk/bin/recover_stale.php --list-only
```

- 503 / `DB_UNAVAILABLE`: verify PDO MySQL and database credentials; never echo secrets.
- `UPSTREAM_UNAVAILABLE`: inspect model server availability and token; avoid logging the prompt.
- `pending_review`: human action required.
- `manual_only`: sensitive case never sent to the model.
- stale `processing`: investigate, manually reconcile and only then requeue via an approved admin operation; there is intentionally no automatic retry.

## Security boundaries

- Keep port `8088` and model port `8080` on loopback. For internet-facing production, add independently reviewed HTTPS, client throttling, MFA/SSO, secure session storage, backups, monitoring, and a penetration test.
- This reference app implements **role-based visibility**, but not multi-tenant isolation or full data-subject request processing. It is **not** compliance certification.
- Audit events contain case ID, actor ID, action and timestamp. Raw prompts/answers are stored in the case/draft tables as **business content** and require a documented retention/deletion policy; they are **not written to application audit logs**.
- Storage must be encrypted as required by your organization's risk assessment. For regulated sectors, perform a DPIA/risk review, validate policy, and put an appropriately qualified human in charge of final decisions.
- Upstream HTTP allowlist is restricted to local loopback endpoints; callers cannot supply arbitrary URLs.

## Add a reviewer or viewer (offline operator action)

Do not edit a password hash by hand. For a non-admin example, use:

```bash
read -rsp 'New user password (16+ chars): ' CASEDESK_PASSWORD; printf '\n'
printf '%s\n' "$CASEDESK_PASSWORD" | sudo -u www-data php /srv/casedesk/bin/create_user.php reviewer@example.invalid reviewer
unset CASEDESK_PASSWORD
```

This must be run by an authorized OS operator. It is intentionally not exposed as a web endpoint.
