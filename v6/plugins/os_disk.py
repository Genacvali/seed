# -*- coding: utf-8 -*-
"""
Plugin: os_disk
Алерты на заканчивающееся место на диске.

Маршрут (configs/alerts.yaml):
  - match: {alertname: "DiskSpaceLow"}
    plugin: "os_disk"
    params: {}

  # Если хочешь следить за конкретным разделом:
  - match: {alertname: "DiskSpaceLow", mountpoint: "/data"}
    plugin: "os_disk"
    params: {mountpoints: ["/data"]}

Параметры (params):
  mountpoints: ["/", "/data", "/var"] — ограничить список точек монтирования.
               По умолчанию показываются все разделы > 1 ГБ.
"""
from typing import Any, Dict, List, Optional


def run(alert: Dict[str, Any], prom, params: Dict[str, Any]) -> Dict[str, Any]:
    labels      = alert.get("labels", {}) or {}
    annotations = alert.get("annotations", {}) or {}

    instance   = labels.get("instance", "unknown")
    alertname  = labels.get("alertname", "DiskSpaceLow")
    severity   = labels.get("severity", "")
    # Точка монтирования из самого алерта (если есть)
    mountpoint = labels.get("mountpoint") or labels.get("mount_point") or ""

    out = []

    out.append(f"🖥  Instance: {instance}")
    if severity:
        out.append(f"⚠  Severity: {severity}")
    if mountpoint:
        out.append(f"💿 Mountpoint: {mountpoint}")

    summary = annotations.get("summary") or annotations.get("message") or ""
    if summary:
        out.append(f"📋 {summary}")

    if prom:
        # Список разделов для проверки
        target_mounts: Optional[List[str]] = params.get("mountpoints")
        if mountpoint and not target_mounts:
            target_mounts = [mountpoint]

        # Запрашиваем все разделы для данного хоста (instant query)
        fstype_filter = 'fstype!~"tmpfs|devtmpfs|overlay|squashfs|nsfs|proc"'

        size_map  = _query_map(prom, f'node_filesystem_size_bytes{{instance="{instance}",{fstype_filter}}}')
        avail_map = _query_map(prom, f'node_filesystem_avail_bytes{{instance="{instance}",{fstype_filter}}}')

        if size_map:
            out.append("")
            out.append("💽 Диски:")
            for mp, size_b in sorted(size_map.items()):
                if size_b < 1 * 1024 ** 3:      # пропускаем разделы < 1 ГБ
                    continue
                if target_mounts and mp not in target_mounts:
                    continue

                avail_b  = avail_map.get(mp, 0)
                used_b   = size_b - avail_b
                used_pct = used_b / size_b * 100 if size_b else 0
                bar      = _bar(used_pct, 100)

                size_gb  = size_b  / 1024 ** 3
                avail_gb = avail_b / 1024 ** 3

                warn = " ⚠" if used_pct >= 85 else ("  🔴" if used_pct >= 95 else "")
                out.append(
                    f"  {mp:<16} {used_pct:5.1f}%  {bar}  "
                    f"free {avail_gb:.1f}/{size_gb:.1f} GB{warn}"
                )
        else:
            # Prometheus недоступен — выведем то, что есть из алерта
            value = annotations.get("value") or labels.get("value") or ""
            if value:
                out.append(f"📊 Значение: {value}")

    return {
        "title": f"💿 {alertname} @ {instance}",
        "lines": out,
    }


def _query_map(prom, query: str) -> Dict[str, float]:
    """Выполняет instant-запрос и возвращает {mountpoint: value}."""
    try:
        results = prom.query(query)
        if not results:
            return {}
        mapping: Dict[str, float] = {}
        for item in results:
            mp  = item.get("metric", {}).get("mountpoint", "")
            val = item.get("value", [None, None])[1]
            if mp and val is not None:
                try:
                    mapping[mp] = float(val)
                except (TypeError, ValueError):
                    pass
        return mapping
    except Exception:
        return {}


def _bar(val: float, total: float, width: int = 10) -> str:
    filled = int(round(val / total * width))
    return "[" + "█" * filled + "░" * (width - filled) + "]"
