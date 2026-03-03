# -*- coding: utf-8 -*-
"""
Plugin: os_disk
"""
from typing import Any, Dict, List, Optional

# ── Схема параметров (читается admin-панелью) ────────────────────────────────
PARAMS_SCHEMA = {
    "title": "Disk плагин",
    "fields": [
        {
            "key": "mountpoints",
            "type": "str_list",
            "label": "Mountpoints для мониторинга",
            "description": "Оставь пустым — покажет все разделы. Пример: /data, /var",
            "default": [],
        },
        {
            "key": "extra_metrics",
            "type": "metrics_list",
            "label": "Дополнительные Prometheus-метрики",
            "description": "Любые PromQL-запросы. Используй {instance} — подставится автоматически.",
            "default": [],
            "presets": [
                {"label": "Disk read latency",  "query": "rate(node_disk_read_time_seconds_total{{instance=\"{instance}\"}}[5m]) / rate(node_disk_reads_completed_total{{instance=\"{instance}\"}}[5m])", "unit": "s"},
                {"label": "Disk write latency", "query": "rate(node_disk_write_time_seconds_total{{instance=\"{instance}\"}}[5m]) / rate(node_disk_writes_completed_total{{instance=\"{instance}\"}}[5m])", "unit": "s"},
                {"label": "Disk queue depth",   "query": "node_disk_io_now{{instance=\"{instance}\"}}", "unit": "ops"},
            ],
        },
    ],
}


def run(alert: Dict[str, Any], prom, params: Dict[str, Any]) -> Dict[str, Any]:
    labels      = alert.get("labels", {}) or {}
    annotations = alert.get("annotations", {}) or {}

    instance   = labels.get("instance", "unknown")
    alertname  = labels.get("alertname", "DiskSpaceLow")
    severity   = labels.get("severity", "")
    mountpoint = (labels.get("mountpoint")
                  or labels.get("mount_point")
                  or params.get("mountpoint", ""))

    target_mounts: Optional[List[str]] = params.get("mountpoints")
    if mountpoint and not target_mounts:
        target_mounts = [mountpoint]

    out = []
    out.append(f"🖥  Instance: {instance}")
    if severity:
        out.append(f"⚠  Severity: {severity}")
    if mountpoint:
        out.append(f"💿 Mountpoint: {mountpoint}")
    summary = annotations.get("summary") or annotations.get("message") or ""
    if summary:
        out.append(f"📋 {summary}")

    if not prom:
        return {"title": f"💿 {alertname} @ {instance}", "lines": out}

    try:
        from prom_helpers import PromHelper
        h = PromHelper(instance)
        if h.instance != instance:
            out.append(f"🔍 Resolved: {instance} → {h.instance}")
    except ImportError:
        h = _FallbackHelper(instance, prom)

    # ── Разделы ───────────────────────────────────────────────
    disks = h.disks()

    if disks:
        # Фильтр по нужным mountpoint если задан
        shown = [d for d in disks if (not target_mounts or d["mountpoint"] in target_mounts)]
        if not shown:
            shown = disks  # fallback — покажем все

        out.append("")
        out.append("💽 Диски:")
        for d in shown:
            mp       = d["mountpoint"]
            used_pct = d["used_pct"]
            avail_gb = d["avail_gb"]
            size_gb  = d["size_gb"]
            bar      = _bar(used_pct, 100)
            level    = "🔴" if used_pct >= 95 else ("🟡" if used_pct >= 85 else "🟢")
            out.append(
                f"  {level} {mp:<16} {used_pct:5.1f}%  {bar}"
                f"  free {avail_gb:.1f} / {size_gb:.1f} GB"
            )

        # ── Inode ─────────────────────────────────────────────
        mp_check = mountpoint or (disks[0]["mountpoint"] if disks else "/")
        inodes = h.disk_inode_pct(mp_check) if hasattr(h, 'disk_inode_pct') else None
        if isinstance(inodes, (int, float)):
            level = "🔴" if inodes >= 90 else ("🟡" if inodes >= 70 else "🟢")
            out.append(f"  {level} Inodes ({mp_check}): {inodes:.1f}%")

    else:
        # Prometheus недоступен или нет данных
        value = annotations.get("value") or labels.get("value") or ""
        if value:
            out.append(f"📊 Value: {value}")
        out.append("⚠  Метрики диска недоступны в Prometheus")

    # ── Дисковый I/O ──────────────────────────────────────────
    io = h.disk_io() if hasattr(h, 'disk_io') else {}
    if io:
        out.append("")
        util = io.get("util")
        read_mbps  = io.get("read_mbps")
        write_mbps = io.get("write_mbps")
        if isinstance(util, (int, float)):
            level = "🔴" if util >= 90 else ("🟡" if util >= 60 else "🟢")
            out.append(f"{level} Disk I/O util: {util:.1f}%")
        if isinstance(read_mbps, (int, float)) or isinstance(write_mbps, (int, float)):
            r = f"{read_mbps:.1f} MB/s"  if isinstance(read_mbps,  (int, float)) else "n/a"
            w = f"{write_mbps:.1f} MB/s" if isinstance(write_mbps, (int, float)) else "n/a"
            out.append(f"💾 Read: {r}  Write: {w}")

    # ── Дополнительные метрики из params ──────────────────────
    _append_extra_metrics(out, h, params)

    return {
        "title": f"💿 {alertname} @ {(h.instance if hasattr(h,'instance') else instance)}",
        "lines": out,
    }


def _append_extra_metrics(out: list, h, params: dict) -> None:
    extras = params.get("extra_metrics", [])
    if not extras:
        return
    out.append("")
    out.append("📡 Custom metrics:")
    for m in extras:
        query = m.get("query", "").strip()
        label = m.get("label", query[:40])
        unit  = m.get("unit", "")
        if not query:
            continue
        try:
            val = h.qv(query) if hasattr(h, "qv") else None
        except Exception:
            val = None
        if isinstance(val, (int, float)):
            out.append(f"   {label}: {val:.4g}{(' ' + unit) if unit else ''}")
        else:
            out.append(f"   {label}: n/a")


def _bar(val: float, total: float, width: int = 10) -> str:
    filled = min(int(round(val / total * width)), width)
    return "[" + "█" * filled + "░" * (width - filled) + "]"


class _FallbackHelper:
    def __init__(self, instance: str, prom_mod):
        self.instance = instance
        self._p = prom_mod

    def disks(self):
        _fs = 'fstype!~"tmpfs|devtmpfs|overlay|squashfs|nsfs|proc"'
        i = self.instance
        sr = self._p.query(f'node_filesystem_size_bytes{{instance="{i}",{_fs}}}') or []
        ar = self._p.query(f'node_filesystem_avail_bytes{{instance="{i}",{_fs}}}') or []
        sm = {r["metric"].get("mountpoint",""): float(r["value"][1]) for r in sr if r.get("value")}
        am = {r["metric"].get("mountpoint",""): float(r["value"][1]) for r in ar if r.get("value")}
        result = []
        for mp, sb in sorted(sm.items()):
            if sb < 1e9: continue
            ab = am.get(mp, 0)
            result.append({"mountpoint":mp,"size_gb":sb/1e9,"avail_gb":ab/1e9,"used_pct":(1-ab/sb)*100})
        return result

    def disk_inode_pct(self, mountpoint="/"):
        i = self.instance
        return self._p.query_value(
            f'(1 - node_filesystem_files_free{{instance="{i}",mountpoint="{mountpoint}"}}'
            f' / node_filesystem_files{{instance="{i}",mountpoint="{mountpoint}"}}) * 100'
        )
