import json
import os
import urllib.error
import urllib.request

BASE_URL = os.environ.get("LOCALAI_URL", "http://127.0.0.1:8080")
MODEL_ID = os.environ["LOCALAI_MODEL"]

payload = {
    "model": MODEL_ID,
    "messages": [{"role": "user", "content": "Define GPU offload."}],
    "temperature": 0.1,
    "max_tokens": 128,
    "stream": False,
}

request = urllib.request.Request(
    f"{BASE_URL}/v1/chat/completions",
    data=json.dumps(payload).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)

try:
    with urllib.request.urlopen(request, timeout=120) as response:
        document = json.load(response)
        print(document["choices"][0]["message"]["content"])
except urllib.error.HTTPError as exc:
    print(f"HTTP request failed with status {exc.code}")
    raise SystemExit(1)
except urllib.error.URLError as exc:
    print(f"Connection failed: {type(exc.reason).__name__}")
    raise SystemExit(2)
