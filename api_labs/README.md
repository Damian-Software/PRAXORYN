# LOCAL AI · Test Materials for Revision 0.2

Author: Damián Zelený.

## What Is Actually Implemented Here

`api_client.py` is a lightweight **client for existing** local interfaces—specifically llama.cpp and Ollama. It does not create its own server or model API. Endpoints are hardcoded and point exclusively to the loopback interface. `safe_tools.py` serves as an example of an allowlist-based approach for diagnostic commands (excluding shell access); it does not grant the model the ability to execute Bash commands directly. `test_lab.py` contains tests that can be run without a network connection or a GPU.

## Verification Without a GPU

```bash
python3 -m unittest -v test_lab
python3 safe_tools.py kernel
python3 safe_tools.py 'rm -rf /'  # must be rejected
```

## Verification With an Existing Local Server Installed

```bash
python3 api_client.py llama models
python3 api_client.py llama chat --model REPLACE_WITH_ID --prompt 'What is a token?'
python3 api_client.py ollama models
python3 api_client.py ollama chat --model REPLACE_WITH_ID --prompt 'What is a token?'
```

On Windows 11, please execute these commands **within a Debian environment in WSL2**. The files do not require a GPU for syntax or unit testing; however, actual inference requires a model server, a compatible model, and the necessary hardware.

## Limitations

These are educational clients, not production-grade enterprise proxies. They lack network authentication, distributed quotas, SSO, and a robust streaming parser. Before exposing it outside an isolated laboratory, you need a reverse proxy, authentication, authorization, TLS, auditing, egress restrictions, and tests tailored to the specific organization.