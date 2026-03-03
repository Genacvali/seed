# v6/prom.py
# Мини-клиент Prometheus HTTP API: /api/v1/query и /api/v1/query_range
#
# Переменные читаются при каждом вызове через os.getenv(),
# чтобы учитывать значения, загруженные из seed.env через core.config.
import os
import requests


def _cfg():
    """Возвращает актуальные настройки из окружения (читается при каждом вызове)."""
    return {
        "url":    os.getenv("PROM_URL", "").rstrip("/"),
        "verify": os.getenv("PROM_VERIFY_SSL", "1") not in ("0", "false", "False"),
        "timeout": float(os.getenv("PROM_TIMEOUT", "") or "3"),
        "bearer": os.getenv("PROM_BEARER", ""),
    }


def _headers(cfg: dict) -> dict:
    h = {"Accept": "application/json"}
    if cfg["bearer"]:
        h["Authorization"] = f"Bearer {cfg['bearer']}"
    return h


def _call(path: str, params: dict):
    cfg = _cfg()
    if not cfg["url"]:
        return []
    url = cfg["url"] + path
    try:
        r = requests.get(
            url, params=params,
            headers=_headers(cfg),
            timeout=cfg["timeout"],
            verify=cfg["verify"],
        )
        r.raise_for_status()
        data = r.json()
        if data.get("status") != "success":
            raise RuntimeError(f"Prometheus API error: {data}")
        return data["data"]["result"]
    except Exception as e:
        print(f"[PROM] query error: {e}")
        return []


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


def last_value(result: list):
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


def query_value(expr: str, ts: float = None):
    """Удобная функция: instant-запрос + извлечение скалярного значения."""
    return last_value(query(expr, ts))
