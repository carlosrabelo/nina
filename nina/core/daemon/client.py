"""HTTP client for communicating with the running Nina daemon."""

import json
import os
import urllib.error
import urllib.request
from typing import Any

from nina.cli._env import load_project_dotenv


def _base_url() -> str:
    load_project_dotenv()
    port = int(os.environ.get("NINA_HTTP_PORT", "8765"))
    return f"http://127.0.0.1:{port}"


def _request(method: str, path: str, body: dict | None = None) -> Any:
    load_project_dotenv()
    url = _base_url() + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"} if data else {}
    api_key = os.environ.get("NINA_API_KEY", "").strip()
    if api_key:
        headers["X-Api-Key"] = api_key
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        if e.code == 403:
            raise ConnectionError(
                "Nina daemon rejected the request (invalid_api_key). "
                "Set NINA_API_KEY in your local .env to match the daemon."
            )
        raise
    except urllib.error.URLError:
        raise ConnectionError(
            "Nina daemon is not running. Start it with: nina daemon"
        )


def get(path: str) -> Any:
    return _request("GET", path)


def put(path: str, body: dict) -> Any:
    return _request("PUT", path, body)


def post(path: str, body: dict) -> Any:
    return _request("POST", path, body)
