# API contract laboratory — edition 0.4

Local-client examples for **existing** AI HTTP APIs. The examples do not create an API service and do not require a GPU, a model, or external packages.

Run the tests:

```bash
cd api_labs_v04
python3 -m unittest -v test_local_api_client.py
```

Discover models on an existing llama.cpp-compatible API:

```bash
python3 local_api_client.py --family openai --base-url http://127.0.0.1:8080/v1 --action models
```

Discover models on the native Ollama API:

```bash
python3 local_api_client.py --family ollama --base-url http://127.0.0.1:11434/api --action models
```

Send a chat request (replace the model with a verified ID):

```bash
python3 local_api_client.py --family openai --base-url http://127.0.0.1:8080/v1 --model verified-model --action chat
```

Security limits: Loopback-only endpoints, bounded response size, finite timeout, no credentials in this laboratory client, no automatic generation retries, and no logging of prompt or response. This is intentionally not a multi-tenant production client; protect network-exposed inference servers separately.
