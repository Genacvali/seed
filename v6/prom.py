# v6/prom.py
# Мини-клиент Prometheus HTTP API: /api/v1/query и /api/v1/query_range
import os, time, requests

PROM_URL = os.getenv("PROM_URL", "").rstrip("/")
VERIFY   = os.getenv("PROM_VERIFY_SSL", "1") == "1"
TIMEOUT  = float(os.getenv("PROM_TIMEOUT", "3"))
BEARER   = os.getenv("PROM_BEARER", "")

def _headers():
    h = {"Accept": "application/json"}
    if BEARER:
        h["Authorization"] = f"Bearer {BEARER}"
    return h

def _call(path: str, params: dict):
    if not PROM_URL:
        return []
    url = PROM_URL + path
    r = requests.get(url, params=params, headers=_headers(),
                     timeout=TIMEOUT, verify=VERIFY)
    r.raise_for_status()
    data = r.json()
    if data.get("status") != "success":
        raise RuntimeError(f"Prometheus API error: {data}")
    return data["data"]["result"]

def query(expr: str, ts: float = None):
    """Мгновенная выборка /api/v1/query"""
    p = {"query": expr}
    if ts is not None:
        p["time"] = str(ts)
    return _call("/api/v1/query", p)

def query_range(expr: str, start: float, end: float, step: str = "30s"):
    """Диапазон /api/v1/query_range"""
    p = {"query": expr, "start": start, "end": end, "step": step}
    return _call("/api/v1/query_range", p)

def last_value(result: list) -> float:
    """Достаём последнее число из ответа Prometheus (vector/scalar)"""
    try:
        if not result:
            return None
        row = result[0]
        if "value" in row:
            return float(row["value"][1])
        if "values" in row and row["values"]:
            return float(row["values"][-1][1])
    except Exception:
        pass
    return None