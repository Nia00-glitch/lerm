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
DEFAULT_OPENHANDS = os.environ.get("OPENHANDS_BASE_URL", "http://127.0.0.1:3000")


class AdapterError(RuntimeError):
    pass


def _request(url: str, method: str = "GET", headers: dict | None = None,
             body: dict | None = None, timeout: float = 60.0, max_retries: int = 3) -> tuple[int, Any]:
    data = json.dumps(body).encode() if body is not None else None
    for attempt in range(max_retries + 1):
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
            if e.code == 429 and attempt < max_retries:
                time.sleep(2.0 * (attempt + 1))
                continue
            return e.code, e.read().decode("utf-8", "replace")
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            if attempt < max_retries:
                time.sleep(2.0 * (attempt + 1))
                continue
            raise AdapterError(f"{url} unreachable or timed out: {e}") from e
    return 500, "Max retries exceeded"



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
        # Try v1 first (OpenHands 1.8+)
        body_v1 = {
            "initial_message": {
                "role": "user",
                "content": [{"type": "text", "text": instruction}],
                "run": False,
            },
            "title": "lerm-eval",
            **(extra or {}),
        }
        if model:
            body_v1["llm_model"] = model
        if workspace and not workspace.startswith("/"):
            body_v1["selected_repository"] = workspace
        status, body = _request(
            f"{self.base_url}/api/v1/app-conversations", method="POST", headers=self.headers,
            body=body_v1,
        )
        if status < 400 and isinstance(body, dict):
            task_id = body.get("id")
            t_info: dict = {}
            for _ in range(120):
                try:
                    s, t_resp = _request(
                        f"{self.base_url}/api/v1/app-conversations/start-tasks?ids={task_id}",
                        headers=self.headers,
                        timeout=15.0,
                    )
                    if s < 400 and isinstance(t_resp, list) and t_resp and t_resp[0]:
                        t_info = t_resp[0]
                        if t_info.get("app_conversation_id"):
                            return str(t_info["app_conversation_id"])
                        if str(t_info.get("status")).upper() in {"FAILED", "ERROR"}:
                            raise AdapterError(f"start task failed: {t_info}")
                except Exception:
                    pass
                time.sleep(2.5)
            if t_info and t_info.get("app_conversation_id"):
                return str(t_info["app_conversation_id"])
            raise AdapterError(f"timed out waiting for conversation startup: {t_info or task_id}")

        # Fallback to legacy v0 /api/conversations
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
            # Check v1
            status, body = _request(
                f"{self.base_url}/api/v1/app-conversations?ids={conversation_id}", headers=self.headers)
            if status < 400 and isinstance(body, list) and body and body[0]:
                meta = body[0]
                exec_state = str(meta.get("execution_status") or meta.get("status") or meta.get("state") or "").lower()
                if exec_state in {"stopped", "finished", "error", "completed", "idle", "paused"}:
                    return meta
            # Check legacy v0
            status, body = _request(
                f"{self.base_url}/api/conversations/{conversation_id}", headers=self.headers)
            if status < 400 and isinstance(body, dict):
                state = str(body.get("execution_status") or body.get("status") or body.get("state") or "").lower()
                if state in {"stopped", "finished", "error", "completed", "idle", "paused"}:
                    return body
            time.sleep(interval_s)
        raise TimeoutError(f"conversation {conversation_id} did not finish in {timeout_s}s")

    def events(self, conversation_id: str) -> list[dict]:
        # Try v1 search
        status, body = _request(
            f"{self.base_url}/api/v1/conversation/{conversation_id}/events/search",
            headers=self.headers, timeout=120)
        if status < 400 and isinstance(body, dict) and "items" in body:
            return body["items"]
        if status < 400 and isinstance(body, list):
            return body
        # Fallback to legacy v0
        status, body = _request(
            f"{self.base_url}/api/conversations/{conversation_id}/events",
            headers=self.headers, timeout=120)
        if isinstance(body, dict):
            return body.get("events", [])
        return []

    def get_sandbox(self, conversation_id: str) -> str | None:
        """Retrieve the sandbox container ID for the given conversation."""
        status, body = _request(
            f"{self.base_url}/api/v1/app-conversations?ids={conversation_id}",
            headers=self.headers, timeout=60,
        )
        if status < 400 and isinstance(body, list) and body and body[0]:
            return body[0].get("sandbox_id")
        return None

    def activate_profile(self, profile_name: str) -> bool:
        """Globally activate a named LLM profile (e.g. 'Ollama-1.5b' or 'Ollama-14b') without restarting."""
        try:
            status, _ = _request(
                f"{self.base_url}/api/v1/settings/profiles/{profile_name}/activate",
                method="POST", headers=self.headers, timeout=30.0,
            )
            return status < 400
        except Exception:
            return False

    def switch_conversation_profile(self, conversation_id: str, profile_name: str) -> bool:
        """Switch an active conversation's LLM to a saved profile on the fly."""
        status, _ = _request(
            f"{self.base_url}/api/v1/app-conversations/{conversation_id}/switch_profile",
            method="POST", headers=self.headers, body={"profile_name": profile_name}, timeout=15,
        )
        return status < 400

