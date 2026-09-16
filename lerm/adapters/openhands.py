"""Agent-under-test adapter: OpenHands agent-server driven over HTTP, with all
model traffic going through OmniRoute.

The existing runtime loop is NOT modified. This wraps around it, which is what
lets the scaffold itself become an independent variable later.

Stdlib-only HTTP (urllib) on purpose: this module has to work on a bare WSL2
Python before anything is pip-installed.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any

from ..trace import RunRecord

DEFAULT_OMNIROUTE = os.environ.get("OMNIROUTE_BASE_URL", "http://host.docker.internal:20128/v1")
DEFAULT_OPENHANDS = os.environ.get("OPENHANDS_BASE_URL", "http://localhost:3000")


class AdapterError(RuntimeError):
    pass


def _request(url: str, method: str = "GET", headers: dict | None = None,
             body: dict | None = None, timeout: float = 60.0) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8", "replace")
            try:
                return resp.status, json.loads(raw)
            except json.JSONDecodeError:
                return resp.status, raw
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")
    except urllib.error.URLError as e:
        raise AdapterError(f"{url} unreachable: {e.reason}") from e


@dataclass
class OmniRoute:
    """Model plane. Auth is X-Session-API-Key; a bare request returns 401."""

    base_url: str = DEFAULT_OMNIROUTE
    api_key: str | None = None

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.environ.get("OMNIROUTE_API_KEY")

    @property
    def headers(self) -> dict:
        if not self.api_key:
            raise AdapterError(
                "OMNIROUTE_API_KEY is not set. OmniRoute returns 401 without "
                "X-Session-API-Key; refusing to send unauthenticated traffic."
            )
        return {"X-Session-API-Key": self.api_key}

    def health(self) -> dict:
        status, body = _request(f"{self.base_url}/models", headers=self.headers, timeout=15)
        if status == 401:
            raise AdapterError("OmniRoute rejected the session key (401)")
        if status >= 400:
            raise AdapterError(f"OmniRoute /models returned {status}: {body}")
        models = body.get("data", body) if isinstance(body, dict) else body
        return {"ok": True, "n_models": len(models) if hasattr(models, "__len__") else None}

    def list_model_ids(self) -> list[str]:
        _, body = _request(f"{self.base_url}/models", headers=self.headers, timeout=30)
        data = body.get("data", []) if isinstance(body, dict) else []
        return sorted(str(m.get("id")) for m in data if isinstance(m, dict) and m.get("id"))

    def complete(self, model: str, messages: list[dict], record: RunRecord | None = None,
                 **kw) -> dict:
        """One chat completion, fully traced (tokens, latency, cost, fingerprint)."""
        t0 = time.perf_counter()
        status, body = _request(
            f"{self.base_url}/chat/completions", method="POST", headers=self.headers,
            body={"model": model, "messages": messages, **kw}, timeout=kw.pop("timeout", 300),
        )
        dt = time.perf_counter() - t0
        if status >= 400 or not isinstance(body, dict):
            if record is not None:
                record.record_llm(model_id=model, model_fingerprint=None, prompt_tokens=0,
                                  completion_tokens=0, cached_tokens=0, latency_s=dt,
                                  cost_usd=0.0, error=f"{status}: {str(body)[:200]}")
            raise AdapterError(f"completion failed {status}: {str(body)[:300]}")
        usage = body.get("usage") or {}
        if record is not None:
            record.record_llm(
                model_id=model,
                model_fingerprint=body.get("system_fingerprint"),
                prompt_tokens=int(usage.get("prompt_tokens", 0)),
                completion_tokens=int(usage.get("completion_tokens", 0)),
                cached_tokens=int((usage.get("prompt_tokens_details") or {}).get("cached_tokens", 0)),
                latency_s=dt,
                cost_usd=float(usage.get("cost", 0.0) or 0.0),
                provider=body.get("provider"),
            )
        return body


@dataclass
class OpenHandsAgent:
    """Agent-under-test. One conversation per (task, condition, seed)."""

    base_url: str = DEFAULT_OPENHANDS
    api_key: str | None = None

    def __post_init__(self) -> None:
        self.api_key = self.api_key or os.environ.get("OPENHANDS_API_KEY")

    @property
    def headers(self) -> dict:
        return {"X-Session-API-Key": self.api_key} if self.api_key else {}

    def health(self) -> dict:
        status, body = _request(f"{self.base_url}/health", headers=self.headers, timeout=10)
        if status >= 400:
            raise AdapterError(f"OpenHands /health returned {status}: {str(body)[:200]}")
        return {"ok": True, "body": body}

    def start_conversation(self, instruction: str, model: str, workspace: str,
                           extra: dict | None = None) -> str:
        status, body = _request(
            f"{self.base_url}/api/conversations", method="POST", headers=self.headers,
            body={"initial_user_msg": instruction, "llm_model": model,
                  "selected_repository": workspace, **(extra or {})},
        )
        if status >= 400 or not isinstance(body, dict):
            raise AdapterError(f"could not start conversation ({status}): {str(body)[:300]}")
        cid = body.get("conversation_id") or body.get("id")
        if not cid:
            raise AdapterError(f"no conversation id in response: {str(body)[:300]}")
        return str(cid)

    def poll(self, conversation_id: str, timeout_s: float = 1800, interval_s: float = 5.0) -> dict:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            status, body = _request(
                f"{self.base_url}/api/conversations/{conversation_id}", headers=self.headers)
            if status < 400 and isinstance(body, dict):
                state = str(body.get("status") or body.get("state") or "").lower()
                if state in {"stopped", "finished", "error", "completed"}:
                    return body
            time.sleep(interval_s)
        raise TimeoutError(f"conversation {conversation_id} did not finish in {timeout_s}s")

    def events(self, conversation_id: str) -> list[dict]:
        status, body = _request(
            f"{self.base_url}/api/conversations/{conversation_id}/events",
            headers=self.headers, timeout=120)
        if status >= 400:
            return []
        return body if isinstance(body, list) else body.get("events", [])
