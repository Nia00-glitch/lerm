"""Hardware-aware resource manager for ₹0 local inference.

Monitors system RAM and coordinates model eviction in Ollama to prevent
OOM / memory thrashing on a 16 GB shared RAM system without discrete GPU.
"""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_OLLAMA_HOST = "http://127.0.0.1:11434"


def evict_ollama_model(model_name: str, host: str = DEFAULT_OLLAMA_HOST) -> bool:
    """Explicitly evict a model from system memory using Ollama's keep_alive=0.
    
    Returns True if the eviction call succeeded, False otherwise.
    """
    url = f"{host.rstrip('/')}/api/generate"
    payload = json.dumps({"model": model_name, "keep_alive": 0}).encode("utf-8")
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return resp.status == 200
    except Exception as e:
        logger.warning("Failed to evict %s from Ollama: %s", model_name, e)
        return False


def get_loaded_models(host: str = DEFAULT_OLLAMA_HOST) -> list[dict[str, Any]]:
    """List all models currently residing in RAM from Ollama."""
    url = f"{host.rstrip('/')}/api/ps"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            return data.get("models", [])
    except Exception as e:
        logger.warning("Failed to query running models from Ollama: %s", e)
        return []


def evict_all_loaded_models(host: str = DEFAULT_OLLAMA_HOST) -> list[str]:
    """Evicts all models currently residing in RAM to free memory."""
    loaded = get_loaded_models(host)
    evicted = []
    for m in loaded:
        name = m.get("name") or m.get("model")
        if name:
            if evict_ollama_model(name, host):
                evicted.append(name)
    return evicted


def get_free_memory_mb() -> float:
    """Get visible free system physical memory in MB."""
    import ctypes
    class MEMORYSTATUSEX(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("sullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]
    try:
        stat = MEMORYSTATUSEX()
        stat.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
        ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
        return stat.ullAvailPhys / (1024 * 1024)
    except Exception:
        # Fallback for non-Windows or if ctypes fails
        return 4096.0


def ensure_safe_memory_for_model(model_name: str, host: str = DEFAULT_OLLAMA_HOST) -> None:
    """If loading a 14B model (~10GB), proactively evict smaller models to guarantee stability."""
    if "14b" in model_name.lower():
        # 14B model requires maximal available RAM
        evicted = evict_all_loaded_models(host)
        if evicted:
            logger.info("Evicted %s to prepare memory for 14B model.", evicted)
