#!/usr/bin/env python3
"""P0 gate. Run this first, on the execution plane, before anything else.

It checks the five things that decide whether this machine can produce real
results at all. It does NOT paper over a missing sandbox: if Docker is absent it
exits non-zero and tells you to go implement ADR-0001 Option A. Per spec §1.1,
building a fake sandbox is worse than stopping.

    python3 scripts/preflight.py
"""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

OK, FAIL, WARN = "PASS", "FAIL", "WARN"
results: list[tuple[str, str, str]] = []


def add(name: str, status: str, detail: str) -> None:
    results.append((name, status, detail))


def sh(cmd: list[str], timeout: int = 20) -> tuple[int, str]:
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return p.returncode, (p.stdout + p.stderr).strip()
    except FileNotFoundError:
        return 127, f"{cmd[0]} not found"
    except subprocess.TimeoutExpired:
        return 124, "timeout"


def check_platform() -> None:
    uname = platform.uname()
    is_wsl = "microsoft" in uname.release.lower()
    if uname.system == "Windows":
        add("execution_plane", FAIL,
            "running on native Windows. Ray/vLLM/SkyPilot are Linux-first and will "
            "waste days here. Move to WSL2 (ADR-0001 Option A).")
    elif is_wsl:
        add("execution_plane", OK, f"WSL2 ({uname.release})")
    else:
        add("execution_plane", OK, f"{uname.system} {uname.release}")


def check_docker() -> None:
    if not shutil.which("docker"):
        add("docker_cli", FAIL, "docker CLI not on PATH")
        return
    rc, out = sh(["docker", "info", "--format", "{{.ServerVersion}}"])
    if rc != 0:
        add("docker_daemon", FAIL,
            "docker CLI present but no daemon reachable. This is THE blocker: no "
            "container sandbox means SWE-bench/Terminal-Bench/CVE-Bench cannot run. "
            "Resolve ADR-0001 before writing more code. Do not weaken the sandbox.")
        return
    add("docker_daemon", OK, f"server {out.splitlines()[0] if out else '?'}")
    rc, out = sh(["docker", "run", "--rm", "hello-world"], timeout=120)
    add("docker_run_hello_world", OK if rc == 0 else FAIL, out.splitlines()[-1] if out else "")


def check_omniroute() -> None:
    from lerm.adapters.openhands import OmniRoute, AdapterError
    if not os.environ.get("OMNIROUTE_API_KEY"):
        add("omniroute_auth", FAIL, "OMNIROUTE_API_KEY unset (endpoint 401s without it)")
        return
    try:
        info = OmniRoute().health()
        add("omniroute", OK, f"reachable, {info.get('n_models')} models")
    except AdapterError as e:
        add("omniroute", FAIL, str(e)[:200])


def check_model_pin() -> None:
    model = os.environ.get("LLM_MODEL", "")
    if not model:
        add("model_pin", WARN, "LLM_MODEL unset — pin an exact current model ID")
    elif "2024" in model or "claude-3-5" in model:
        add("model_pin", FAIL,
            f"LLM_MODEL={model} is a 2024-era model, stale for 2026 work. "
            "Pick a current ID from the OmniRoute catalog and pin it exactly.")
    else:
        add("model_pin", OK, model)


def check_openhands() -> None:
    from lerm.adapters.openhands import OpenHandsAgent, AdapterError
    try:
        OpenHandsAgent().health()
        add("openhands_server", OK, os.environ.get("OPENHANDS_BASE_URL", "http://localhost:3000"))
    except (AdapterError, Exception) as e:  # noqa: BLE001 - preflight reports, never raises
        add("openhands_server", WARN, f"not reachable ({str(e)[:120]}) — fine until P2")


def check_repo() -> None:
    rc, out = sh(["git", "log", "--oneline", "-n", "1"])
    add("git_history", OK if rc == 0 and out else FAIL,
        out or "0 commits — commit the scaffold now, secrets excluded")
    leaked = []
    rc, tracked = sh(["git", "ls-files"])
    for f in tracked.splitlines():
        if f.endswith((".env",)) or "secret" in f.lower():
            leaked.append(f)
    add("no_secrets_tracked", OK if not leaked else FAIL, ", ".join(leaked) or "clean")


def _load_env() -> None:
    env_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env")
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    k, v = k.strip(), v.strip()
                    if k and k not in os.environ and v:
                        os.environ[k] = v


def main() -> int:
    _load_env()
    check_platform()
    check_docker()
    check_omniroute()
    check_model_pin()
    check_openhands()
    check_repo()

    width = max(len(n) for n, _, _ in results)
    print("\nLERM preflight (P0 gate)\n" + "=" * (width + 40))
    for name, status, detail in results:
        print(f"{status:<4} {name:<{width}}  {detail}")
    failures = [n for n, s, _ in results if s == FAIL]
    print("=" * (width + 40))
    if failures:
        print(f"\n{len(failures)} blocking failure(s): {', '.join(failures)}")
        print("P0 is not green. Per spec §1.1, stop and fix these before building on top.")
        return 1
    print("\nP0 green. Proceed to P1 (trace layer).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
