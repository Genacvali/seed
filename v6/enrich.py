# v6/enrich.py
import os, time
from prom import query, query_range, last_value

LOOKBACK = int(os.getenv("PROM_LOOKBACK_SEC", "900"))  # 15 мин

def _pct(x): 
    return f"{x:.0f}%" if isinstance(x, (int, float)) else "n/a"

def _num(x):
    return f"{x:.2f}" if isinstance(x, (int, float)) else "n/a"

def enrich_alert(alert: dict) -> dict:
    """
    Возвращает { 'cpu_now':.., 'mem_now':.., 'disk_used_now':.., ... }
    Ничего не ломает, если Prometheus не настроен.
    """
    labels = alert.get("labels", {})
    inst   = labels.get("instance") or labels.get("host")
    mount  = labels.get("mountpoint") or labels.get("path")
    
    # Используем только hostname без порта для метрик
    inst_with_port = inst.split(":")[0] if inst else None
    end    = time.time()
    start  = end - LOOKBACK

    enr = {}

    if inst:
        # CPU (node_exporter вариант)
        cpu_expr = f'100 * (1 - avg(rate(node_cpu_seconds_total{{instance="{inst_with_port}",mode="idle"}}[5m])))'
        # Если у тебя Telegraf-монолит в Prom, можно заменить на свой метрик-нейм:
        # cpu_expr = f'avg(cpu_usage{{instance="{inst_with_port}"}})'

        mem_expr = (
            f'100 * (1 - (node_memory_MemAvailable_bytes{{instance="{inst_with_port}"}}'
            f' / node_memory_MemTotal_bytes{{instance="{inst_with_port}"}}))'
        )
        # Для Telegraf (если имена другие):
        # mem_expr = f'100 * ((mem_total{{instance="{inst_with_port}"}} - mem_available{{instance="{inst_with_port}"}}) / mem_total{{instance="{inst_with_port}"}})'

        try:
            enr["cpu_now"] = last_value(query(cpu_expr))
            enr["mem_now"] = last_value(query(mem_expr))
            
            # Telegraf fallback if node_exporter metrics not available
            if not isinstance(enr.get("cpu_now"), (int, float)):
                cpu_telegraf_expr = f'100 - cpu_usage_idle{{instance="{inst}",port="9216"}}'
                enr["cpu_now"] = last_value(query(cpu_telegraf_expr))
            
            if not isinstance(enr.get("mem_now"), (int, float)):
                mem_telegraf_expr = f'mem_used_percent{{instance="{inst}",port="9216"}}'
                enr["mem_now"] = last_value(query(mem_telegraf_expr))
                
        except Exception:
            pass

    if inst and mount:
        # Использование диска (node_exporter)
        disk_expr = (
            f'100 * (node_filesystem_size_bytes{{instance="{inst_with_port}",mountpoint="{mount}",fstype!~"tmpfs|overlay"}}'
            f' - node_filesystem_avail_bytes{{instance="{inst_with_port}",mountpoint="{mount}",fstype!~"tmpfs|overlay"}})'
            f' / node_filesystem_size_bytes{{instance="{inst_with_port}",mountpoint="{mount}",fstype!~"tmpfs|overlay"}}'
        )
        # Telegraf-вариант:
        # disk_expr = f'disk_used_percent{{instance="{inst_with_port}",path="{mount}"}}'

        try:
            enr["disk_used_now"] = last_value(query(disk_expr))
            # тренд за 15 мин (avg/max)
            res = query_range(disk_expr, start, end, "60s")
            # грубая оценка
            if res and "values" in res[0] and len(res[0]["values"]) >= 2:
                vals = [float(v[1]) for v in res[0]["values"] if v and v[1] is not None]
                if vals:
                    enr["disk_used_avg15m"] = sum(vals)/len(vals)
                    enr["disk_used_max15m"] = max(vals)
        except Exception:
            pass

    # Пример для Mongo COLLSCAN (если метрика есть в Prom — от Telegraf/экспортеров)
    if labels.get("alertname","").lower().startswith("mongohot"):
        # адаптируй expr под свою метрику (пример ниже — иллюстрация)
        expr = f'sum(increase(mongodb_op_collsacn_total{{instance="{inst_with_port}"}}[15m]))'
        try:
            enr["mongo_colls_scans_15m"] = last_value(query(expr))
        except Exception:
            pass

    # Пример для Postgres slow queries (тоже под свою метрику/экспортер)
    if labels.get("alertname","").lower().startswith("pgslow"):
        expr = f'sum(increase(pg_stat_statements_calls_slow_total{{instance="{inst_with_port}"}}[15m]))'
        try:
            enr["pg_slow_15m"] = last_value(query(expr))
        except Exception:
            pass

    # Удобные строковые краткие подписи (на карточку)
    summary = []
    if "cpu_now" in enr:  summary.append(f"CPU ~ {_pct(enr['cpu_now'])}")
    if "mem_now" in enr:  summary.append(f"MEM ~ {_pct(enr['mem_now'])}")
    if "disk_used_now" in enr: 
        s = f"Disk {mount} ~ {_pct(enr['disk_used_now'])}"
        if "disk_used_max15m" in enr:
            s += f" (≤{_pct(enr['disk_used_max15m'])} за 15м)"
        summary.append(s)

    enr["summary_line"] = " · ".join(summary) if summary else ""
    return enr