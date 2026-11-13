import argparse
import json
import statistics
import time
import urllib.request


def run_once(url, model, max_tokens):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "List three benefits of local inference."}],
        "max_tokens": max_tokens,
        "temperature": 0,
        "stream": False,
    }
    request = urllib.request.Request(
        url.rstrip("/") + "/v1/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    started = time.perf_counter()
    with urllib.request.urlopen(request, timeout=180) as response:
        document = json.load(response)
        status = response.status
    elapsed = time.perf_counter() - started
    usage = document.get("usage") or {}
    return {
        "status": status,
        "elapsed_ms": round(elapsed * 1000, 2),
        "completion_tokens": usage.get("completion_tokens"),
        "model": document.get("model"),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", default="http://127.0.0.1:8080")
    parser.add_argument("--model", required=True)
    parser.add_argument("--runs", type=int, default=5)
    parser.add_argument("--max-tokens", type=int, default=128)
    args = parser.parse_args()
    if not 1 <= args.runs <= 100:
        parser.error("--runs must be between 1 and 100")
    if not 1 <= args.max_tokens <= 2048:
        parser.error("--max-tokens must be between 1 and 2048")
    run_once(args.url, args.model, args.max_tokens)  # Warm-up.
    results = [run_once(args.url, args.model, args.max_tokens)
               for _ in range(args.runs)]
    latencies = sorted(item["elapsed_ms"] for item in results)
    p95_index = max(0, int(0.95 * len(latencies) + 0.999999) - 1)
    print(json.dumps({
        "measurements": results,
        "p50_ms": statistics.median(latencies),
        "p95_ms": latencies[p95_index],
        "sample_size": len(latencies),
        "ttft_measured": False,
    }, indent=2))


if __name__ == "__main__":
    main()
