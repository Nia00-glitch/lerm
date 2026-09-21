# ADR-0001 — Execution plane

**Status:** ACCEPTED
**Date:** 2026-09-16
**Context:** spec §1.1. No Docker daemon inside the OpenHands container, so no container
sandbox, so SWE-bench Verified / Terminal-Bench 2.0 / CVE-Bench / CORE-bench cannot run at
all. Every phase after P1 is blocked on this.

## Decision

**Option A — control plane in WSL2 on the Windows 11 host, owning its own Docker daemon,
driving the OpenHands container over HTTP as one agent-under-test backend among several.**

## Why A over B and C

| | A: WSL2 control plane | B: mount host Docker socket into OpenHands | C: dedicated Linux host |
|---|---|---|---|
| Real container sandbox | yes, native | yes | yes |
| Privilege model | control plane holds Docker; agent container holds none | agent container gets effective root on the host — an agent that writes a malicious container escapes everything | clean |
| Ray / vLLM / SkyPilot | Linux-first, behave correctly | same as today | best |
| Scaffold as independent variable | natural: OpenHands becomes one backend, others can be added | hard: everything stays inside one container | natural |
| Extra hardware | none | none | yes, and another box to keep alive |
| Cost to reverse | low | low | high |

B is rejected on the privilege point specifically. This machine **generates untrusted code by
design** (§9), so handing the agent container a host Docker socket means a bad generation can
own the host. That is not a theoretical risk in a 24/7 unattended loop.

C is the right answer later if you outgrow one machine. It is not worth the setup cost today.

## Consequences

- The control plane (this repo) runs in WSL2 and treats OpenHands as a *remote* service at
  `OPENHANDS_BASE_URL`. Nothing in the existing runtime loop changes — required by spec §2.
- Sandboxes for the eval harness are created by the WSL2 Docker daemon, not by OpenHands.
- Agent containers get no host mounts, no credentials, and allow-listed egress (§9).
- WSL2 needs `systemd=true` in `/etc/wsl.conf` for Docker Engine to run cleanly, and a
  `.wslconfig` memory/CPU allocation sized for the warm sandbox pool at P3.
- `host.docker.internal` resolves differently from WSL2 than from inside the OpenHands
  container. OmniRoute is reachable from WSL2 at the Windows host IP — confirm with
  `scripts/preflight.py`, don't assume.

## Rejected non-options

Weakening the sandbox, or simulating one, so the harness "runs". Per §1.1 that produces
numbers with no meaning, which is worse than producing none. `scripts/preflight.py` exits 1
rather than let the build proceed without a working `docker run hello-world`.

## Verification

```bash
python3 scripts/preflight.py   # must print "P0 green"
```
