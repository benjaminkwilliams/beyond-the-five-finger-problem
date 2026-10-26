#!/usr/bin/env python3
"""Portable client for Meta Model API, for the hackathon build.

No credential lives in this file or in the repo. The key is read only from
the META_API_KEY environment variable at run time. Set it from the Model API
dashboard key for the account that holds the hackathon credits.

Endpoints, verified 2026-10-26 against api.meta.ai:
  GET  /v1/models
  POST /v1/chat/completions  with {"model": ..., "messages": [...]}

Commands:
  python3 model_api.py models
  python3 model_api.py chat --model muse-spark-1.3 --prompt "Reply with exactly: ready"
"""
import argparse
import json
import os
import sys
import urllib.error
import urllib.request

BASE = "https://api.meta.ai/v1"


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        raise RuntimeError("redirect refused, verify the endpoint")


def _api_key():
    key = os.environ.get("META_API_KEY", "").strip()
    if not key:
        raise SystemExit("META_API_KEY is not set in the environment")
    return key


def call(method, path, payload=None):
    request = urllib.request.Request(BASE + path, method=method)
    request.add_header("Authorization", "Bearer " + _api_key())
    if payload is not None:
        request.add_header("Content-Type", "application/json")
        request.data = json.dumps(payload).encode("utf-8")
    try:
        with urllib.request.build_opener(NoRedirect()).open(request, timeout=60) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"HTTP {exc.code}: {body[:1000]}", file=sys.stderr)
        raise SystemExit(1)


def list_models():
    data = call("GET", "/models")
    models = data.get("data", data)
    if isinstance(models, list):
        return [str(m.get("id", m)) for m in models]
    return data


def chat(model, prompt):
    data = call("POST", "/chat/completions", {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
    })
    choices = data.get("choices", [])
    if choices:
        return choices[0].get("message", {}).get("content", "")
    return json.dumps(data, indent=2)[:2000]


def main():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("models")
    chat_parser = sub.add_parser("chat")
    chat_parser.add_argument("--model", default="muse-spark-1.3")
    chat_parser.add_argument("--prompt", required=True)
    args = parser.parse_args()

    if args.command == "models":
        result = list_models()
        if isinstance(result, list):
            print("\n".join(result))
        else:
            print(json.dumps(result, indent=2)[:2000])
        return
    print(chat(args.model, args.prompt))


if __name__ == "__main__":
    main()
