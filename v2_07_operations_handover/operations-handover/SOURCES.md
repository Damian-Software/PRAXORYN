# Sources and version checkpoints

These are primary references for verifying behavior against the **installed** version of each product. The book does not claim that every API endpoint is available in every release.

- llama.cpp server: https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md
- Ollama API: https://docs.ollama.com/api
- Microsoft WSL: https://learn.microsoft.com/windows/wsl/
- NVIDIA CUDA on WSL: https://docs.nvidia.com/cuda/wsl-user-guide/
- Debian 13: https://www.debian.org/releases/trixie/
- systemd exec sandbox: https://www.freedesktop.org/software/systemd/man/latest/systemd.exec.html
- systemd timers: https://www.freedesktop.org/software/systemd/man/latest/systemd.timer.html
- Nginx reverse proxy: https://nginx.org/en/docs/http/ngx_http_proxy_module.html
- MariaDB logical backup: https://mariadb.com/docs/server/clients-and-utilities/backup-restore-and-import-clients/mariadb-dump
- OWASP API Security Top 10: https://owasp.org/API-Security/
- GDPR: https://eur-lex.europa.eu/eli/reg/2016/679/oj
- EU AI Act: https://eur-lex.europa.eu/eli/reg/2024/1689/oj

All examples use synthetic inputs. Production use requires configuration review, legal/security review where applicable, measured capacity, verified backup restoration and a documented rollback path.
