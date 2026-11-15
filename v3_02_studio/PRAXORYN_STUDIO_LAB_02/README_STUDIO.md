# PRAXORYN Studio — second laboratory

This laboratory is additive to the MediaOps files in this archive. It implements a
private SQLite task queue, an offline media/document worker, an explicit human
approval step, integrity checks, a ZIP export, and a loopback-only read-only API
with a PHP dashboard. It is not a production SaaS application.

## Start

```bash
sudo apt update
sudo apt install --no-install-recommends python3 python3-venv ffmpeg libreoffice php-cli
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m praxoryn_studio --home studio-private init
python -m praxoryn_studio --home studio-private submit --tenant demo_school --kind education --prompt-file examples/studio/school.txt
python -m praxoryn_studio --home studio-private work-once
python -m praxoryn_studio --home studio-private list --tenant demo_school
```

To approve a job, inspect each generated file, then run:

```bash
python -m praxoryn_studio --home studio-private approve --tenant demo_school --reviewer operator01 JOB_ID
python -m praxoryn_studio --home studio-private export --tenant demo_school JOB_ID
```

Replace `JOB_ID` with the ID printed by `submit`.

## Read-only browser view

```bash
export STUDIO_READ_TOKEN="$(python -c 'import secrets;print(secrets.token_urlsafe(32))')"
python -m praxoryn_studio --home studio-private serve-readonly
# In a second terminal inheriting the same token:
php -S 127.0.0.1:8877 -t portal
```

Open `http://127.0.0.1:8877/?tenant=demo_school` in a local browser.
Do not bind the PHP or Python development servers to `0.0.0.0`.
This dashboard has no full user authentication, and therefore must not be made
public. Deploy behind an authenticated server only after adding tenant identity,
role-based authorization and an independent security review.

## Important constraints

- Offline worker output uses synthetic placeholder text and image, not a real AI model.
- The demo is intentionally single-worker; the SQLite claim mechanism is safe for
  claim contention, but crashed workers require an operator runbook.
- Full prompts remain stored in `payload_json`; this database therefore needs
  access limits, encryption at rest where required, and a retention policy.
- The metadata event table does not log prompts or produced documents.
- Human approval is mandatory before ZIP export.
- PDF and MP4 creation require local LibreOffice and FFmpeg.
- `portal/index.php` only lists metadata and cannot submit or approve jobs.
