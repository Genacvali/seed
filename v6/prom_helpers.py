# -*- coding: utf-8 -*-
"""
PromHelper — умная обёртка над prom.py.

Главная фишка: автоматически разрешает instance-метку.
Алерт может содержать "host.ru", а Prometheus хранить "host.ru:9100" —
PromHelper сам найдёт правильный вариант через запрос `up`.
"""
import prom as _prom
from typing import Any, Dict, List, Optional


class PromHelper:
    def __init__(self, instance: str):
        self.raw_instance = instance
        self._resolved: Optional[str] = None

    @property
    def instance(self) -> str:
        if self._resolved is None:
            self._resolved = self._resolve(self.raw_instance)
        return self._resolved

    # ─── Разрешение instance ──────────────────────────────────
    def _resolve(self, host: str) -> str:
        """Пробует найти правильный instance в Prometheus."""
        # 1. Точное совпадение
        if _prom.query(f'up{{instance="{host}"}}'):
            return host

        # 2. host без порта → ищем host:*
        bare = host.split(":")[0]
        results = _prom.query(f'up{{instance=~"{bare}(:[0-9]+)?$"}}')
        if results:
            candidates = [r["metric"].get("instance", host) for r in results]
            # Предпочитаем :9100 (node_exporter)
            for c in candidates:
                if c.endswith(":9100"):
                    return c
            return candidates[0]

        return host  # fallback — оставляем как есть

    # ─── Базовые query ────────────────────────────────────────
    def qv(self, tmpl: str, **kw) -> Optional[float]:
        """query_value с подстановкой {instance}."""
        return _prom.query_value(tmpl.format(instance=self.instance, **kw))

    def q(self, tmpl: str, **kw) -> List[Dict]:
        """instant query с подстановкой {instance}."""
        return _prom.query(tmpl.format(instance=self.instance, **kw)) or []

    # ─── CPU ──────────────────────────────────────────────────
    def cpu_usage_pct(self) -> Optional[float]:
        return self.qv(
            '100 - (avg by(instance)(rate('
            'node_cpu_seconds_total{{mode="idle",instance="{instance}"}}[5m])) * 100)'
        )

    def load_avg(self):
        return (
            self.qv('node_load1{{instance="{instance}"}}'),
            self.qv('node_load5{{instance="{instance}"}}'),
            self.qv('node_load15{{instance="{instance}"}}'),
        )

    def cpu_count(self) -> Optional[int]:
        v = self.qv('count(node_cpu_seconds_total{{mode="idle",instance="{instance}"}})')
        return int(v) if isinstance(v, float) else None

    def procs_running(self) -> Optional[int]:
        v = self.qv('node_procs_running{{instance="{instance}"}}')
        return int(v) if isinstance(v, float) else None

    # ─── Память ───────────────────────────────────────────────
    def memory_used_pct(self) -> Optional[float]:
        return self.qv(
            '(1 - node_memory_MemAvailable_bytes{{instance="{instance}"}}'
            ' / node_memory_MemTotal_bytes{{instance="{instance}"}}) * 100'
        )

    def memory_bytes(self) -> Dict[str, Optional[float]]:
        return {
            "total":   self.qv('node_memory_MemTotal_bytes{{instance="{instance}"}}'),
            "avail":   self.qv('node_memory_MemAvailable_bytes{{instance="{instance}"}}'),
            "cached":  self.qv('(node_memory_Cached_bytes{{instance="{instance}"}}'
                               ' + node_memory_Buffers_bytes{{instance="{instance}"}})'),
            "swap_total": self.qv('node_memory_SwapTotal_bytes{{instance="{instance}"}}'),
            "swap_free":  self.qv('node_memory_SwapFree_bytes{{instance="{instance}"}}'),
        }

    # ─── Диски ────────────────────────────────────────────────
    def disks(self) -> List[Dict]:
        """Все разделы > 1 ГБ с процентом использования."""
        _fs = 'fstype!~"tmpfs|devtmpfs|overlay|squashfs|nsfs|proc|sysfs"'
        size_r  = self.q(f'node_filesystem_size_bytes{{instance="{{instance}}",{_fs}}}')
        avail_r = self.q(f'node_filesystem_avail_bytes{{instance="{{instance}}",{_fs}}}')

        size_map  = _metric_map(size_r,  "mountpoint")
        avail_map = _metric_map(avail_r, "mountpoint")

        result = []
        for mp, size_b in sorted(size_map.items()):
            if size_b < 1e9:
                continue
            avail_b  = avail_map.get(mp, 0.0)
            used_pct = (1 - avail_b / size_b) * 100
            result.append({
                "mountpoint": mp,
                "size_gb":    size_b  / 1e9,
                "avail_gb":   avail_b / 1e9,
                "used_pct":   used_pct,
            })
        return result

    def disk_inode_pct(self, mountpoint: str = "/") -> Optional[float]:
        return self.qv(
            '(1 - node_filesystem_files_free{{instance="{instance}",mountpoint="{mp}"}}'
            ' / node_filesystem_files{{instance="{instance}",mountpoint="{mp}"}}) * 100',
            mp=mountpoint,
        )

    # ─── Топ процессов (process-exporter) ─────────────────────
    def top_processes_cpu(self, n: int = 10) -> List[Dict]:
        """
        Топ N процессов по CPU.
        Требует process-exporter: github.com/ncabatoff/process-exporter
        Метрика: namedprocess_namegroup_cpu_seconds_total
        """
        results = self.q(
            f'topk({n}, rate('
            'namedprocess_namegroup_cpu_seconds_total{instance="{instance}"}[5m]))'
        )
        return _top_procs(results, "cpu_pct", scale=100)

    def top_processes_mem(self, n: int = 10) -> List[Dict]:
        """Топ N процессов по RSS-памяти (process-exporter)."""
        results = self.q(
            f'topk({n},'
            ' namedprocess_namegroup_memory_bytes{instance="{instance}",memtype="resident"})'
        )
        return _top_procs(results, "mem_mb", scale=1 / 1e6)

    def process_exporter_available(self) -> bool:
        """Проверяет наличие process-exporter для данного instance."""
        return bool(self.q(
            'namedprocess_namegroup_num_procs{instance="{instance}"}'
        ))

    # ─── Диск I/O ─────────────────────────────────────────────
    def disk_io(self) -> Dict[str, Optional[float]]:
        """Утилизация дисков и скорость чтения/записи."""
        util = self.qv(
            'avg by(instance)(rate('
            'node_disk_io_time_seconds_total{{instance="{instance}",device!~"loop.*"}}[5m])) * 100'
        )
        read_bps = self.qv(
            'sum by(instance)(rate('
            'node_disk_read_bytes_total{{instance="{instance}",device!~"loop.*"}}[5m]))'
        )
        write_bps = self.qv(
            'sum by(instance)(rate('
            'node_disk_written_bytes_total{{instance="{instance}",device!~"loop.*"}}[5m]))'
        )
        return {
            "util":      util,
            "read_mbps":  read_bps  / 1e6 if isinstance(read_bps,  (int, float)) else None,
            "write_mbps": write_bps / 1e6 if isinstance(write_bps, (int, float)) else None,
        }

    # ─── Сеть ─────────────────────────────────────────────────
    def network_mbps(self) -> Dict[str, Optional[float]]:
        rx = self.qv(
            'sum by(instance)(rate('
            'node_network_receive_bytes_total{{instance="{instance}",device!="lo"}}[5m]))'
        )
        tx = self.qv(
            'sum by(instance)(rate('
            'node_network_transmit_bytes_total{{instance="{instance}",device!="lo"}}[5m]))'
        )
        return {
            "rx": rx / 1e6 if isinstance(rx, (int, float)) else None,
            "tx": tx / 1e6 if isinstance(tx, (int, float)) else None,
        }


# ─── Утилиты ──────────────────────────────────────────────────────────────────

def _metric_map(results: List[Dict], label: str) -> Dict[str, float]:
    m: Dict[str, float] = {}
    for r in results:
        key = r.get("metric", {}).get(label, "")
        val = r.get("value", [None, None])[1]
        if key and val is not None:
            try:
                m[key] = float(val)
            except (TypeError, ValueError):
                pass
    return m


def _top_procs(results: List[Dict], value_key: str, scale: float = 1.0) -> List[Dict]:
    procs = []
    for r in results:
        name = (
            r.get("metric", {}).get("groupname")
            or r.get("metric", {}).get("name")
            or "?"
        )
        val = r.get("value", [None, None])[1]
        if val is None:
            continue
        try:
            procs.append({"name": name, value_key: float(val) * scale})
        except (TypeError, ValueError):
            pass
    return sorted(procs, key=lambda x: -x.get(value_key, 0))
