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

        # Load Average
        load_expr = f'node_load1{{instance="{inst_with_port}"}}'
        
        # Disk usage for root and data
        disk_root_expr = f'''100 * (node_filesystem_size_bytes{{instance="{inst_with_port}",mountpoint="/",fstype!~"tmpfs|overlay"}} 
                           - node_filesystem_avail_bytes{{instance="{inst_with_port}",mountpoint="/",fstype!~"tmpfs|overlay"}})
                           / node_filesystem_size_bytes{{instance="{inst_with_port}",mountpoint="/",fstype!~"tmpfs|overlay"}}'''
        
        disk_data_expr = f'''100 * (node_filesystem_size_bytes{{instance="{inst_with_port}",mountpoint="/data",fstype!~"tmpfs|overlay"}} 
                            - node_filesystem_avail_bytes{{instance="{inst_with_port}",mountpoint="/data",fstype!~"tmpfs|overlay"}})
                            / node_filesystem_size_bytes{{instance="{inst_with_port}",mountpoint="/data",fstype!~"tmpfs|overlay"}}'''

        try:
            enr["cpu_now"] = last_value(query(cpu_expr))
            enr["mem_now"] = last_value(query(mem_expr))
            enr["load_now"] = last_value(query(load_expr))
            enr["disk_root_now"] = last_value(query(disk_root_expr.replace('\n', '').strip()))
            enr["disk_data_now"] = last_value(query(disk_data_expr.replace('\n', '').strip()))
            
            # Telegraf fallback if node_exporter metrics not available
            if not isinstance(enr.get("cpu_now"), (int, float)):
                cpu_telegraf_expr = f'100 - cpu_usage_idle{{instance="{inst}",port="9216"}}'
                enr["cpu_now"] = last_value(query(cpu_telegraf_expr))
            
            if not isinstance(enr.get("mem_now"), (int, float)):
                mem_telegraf_expr = f'mem_used_percent{{instance="{inst}",port="9216"}}'
                enr["mem_now"] = last_value(query(mem_telegraf_expr))
                
            if not isinstance(enr.get("load_now"), (int, float)):
                load_telegraf_expr = f'system_load1{{instance="{inst}",port="9216"}}'
                enr["load_now"] = last_value(query(load_telegraf_expr))
                
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

    # Final Fantasy стиль эмодзи для дисков
    def _disk_emoji(usage):
        if not isinstance(usage, (int, float)):
            return "⚙️"  # Механизм - неизвестно
        if usage >= 90:
            return "💎🔥"  # Красный кристалл с огнем - критично
        elif usage >= 80:
            return "⚔️"  # Меч - опасно
        elif usage >= 60:
            return "🛡️"  # Щит - осторожно
        else:
            return "✨"  # Звездочка - все хорошо
    
    # Final Fantasy стиль эмодзи для разных метрик
    def _cpu_emoji(usage):
        if not isinstance(usage, (int, float)):
            return "🔮"  # Кристальная сфера - неизвестно
        if usage >= 90:
            return "💎🔥"  # Красный кристалл с огнем - критично
        elif usage >= 70:
            return "🗡️"  # Острый меч - высокая нагрузка
        elif usage >= 50:
            return "⚔️"  # Скрещенные мечи - средняя нагрузка
        else:
            return "✨"  # Звездочка - низкая нагрузка
            
    def _mem_emoji(usage):
        if not isinstance(usage, (int, float)):
            return "🧙‍♂️"  # Маг - неизвестно
        if usage >= 90:
            return "💎🔥"  # Красный кристалл с огнем - критично
        elif usage >= 70:
            return "🏰"  # Замок - высокое использование
        elif usage >= 50:
            return "🛡️"  # Щит - среднее использование  
        else:
            return "🌟"  # Звезда - низкое использование

    # Удобные строковые краткие подписи (на карточку)
    summary = []
    if "cpu_now" in enr:  
        cpu_emoji = _cpu_emoji(enr['cpu_now'])
        summary.append(f"{cpu_emoji} CPU ~ {_pct(enr['cpu_now'])}")
    if "mem_now" in enr:  
        mem_emoji = _mem_emoji(enr['mem_now'])
        summary.append(f"{mem_emoji} MEM ~ {_pct(enr['mem_now'])}")
    if "load_now" in enr: summary.append(f"⚖️ Load: {_num(enr['load_now'])}")
    if "disk_root_now" in enr: 
        emoji = _disk_emoji(enr['disk_root_now'])
        summary.append(f"{emoji} Disk /: {_pct(enr['disk_root_now'])}")
    if "disk_data_now" in enr: 
        emoji = _disk_emoji(enr['disk_data_now'])
        summary.append(f"{emoji} Disk /data: {_pct(enr['disk_data_now'])}")
    
    # Legacy disk support (from mountpoint)
    if "disk_used_now" in enr: 
        emoji = _disk_emoji(enr['disk_used_now'])
        s = f"{emoji} Disk {mount}: {_pct(enr['disk_used_now'])}"
        if "disk_used_max15m" in enr:
            s += f" (≤{_pct(enr['disk_used_max15m'])} за 15м)"
        summary.append(s)

    enr["summary_line"] = " · ".join(summary) if summary else ""
    return enr