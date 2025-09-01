# v6/plugins/pg_slow.py
"""
PostgreSQL performance and slow query analysis plugin
"""

def run(alert: dict, prom, params: dict) -> dict:
    """
    PostgreSQL-specific metrics: connections, slow queries, locks, transactions
    """
    labels = alert.get("labels", {})
    inst = labels.get("instance", "unknown")
    alertname = labels.get("alertname", "PostgresAlert")
    
    lines = []
    top = params.get("top", 5)
    show_host_metrics = params.get("show_host_metrics", True)
    show_idle_transactions = params.get("show_idle_transactions", False)
    show_connections = params.get("show_connections", False)
    show_locks = params.get("show_locks", False)
    min_duration = params.get("min_duration", "1s")
    
    # === Basic Host Metrics (if requested) ===
    if show_host_metrics:
        # Нормализуем instance для node_exporter
        if inst and ":" not in inst:
            inst_with_port = f"{inst}:9100"
        else:
            inst_with_port = inst
            
        try:
            # CPU и Memory для хоста
            cpu_expr = f'100 * (1 - avg(rate(node_cpu_seconds_total{{instance="{inst_with_port}",mode="idle"}}[5m])))'
            cpu = prom.last_value(cpu_expr)
            lines.append(f"🔥 Host CPU: {cpu:.1f}%" if isinstance(cpu, (int, float)) else "🔥 Host CPU: n/a")
            
            mem_expr = f'100 * (1 - (node_memory_MemAvailable_bytes{{instance="{inst_with_port}"}} / node_memory_MemTotal_bytes{{instance="{inst_with_port}"}}))'
            mem = prom.last_value(mem_expr)
            lines.append(f"💾 Host Memory: {mem:.1f}%" if isinstance(mem, (int, float)) else "💾 Host Memory: n/a")
            
        except Exception as e:
            lines.append(f"❌ Host metrics error: {str(e)[:50]}")
    
    # === PostgreSQL Specific Metrics ===
    # Предполагаем, что PostgreSQL exporter работает на стандартном порту 9187
    pg_instance = inst
    if ":" not in pg_instance:
        pg_instance = f"{inst}:9187"
    
    try:
        # Active connections
        conn_expr = f'pg_stat_database_numbackends{{instance="{pg_instance}"}}'
        connections = prom.last_value(conn_expr)
        if isinstance(connections, (int, float)):
            lines.append(f"🔌 Active connections: {connections}")
        
        # Max connections
        max_conn_expr = f'pg_settings_max_connections{{instance="{pg_instance}"}}'
        max_connections = prom.last_value(max_conn_expr)
        if isinstance(max_connections, (int, float)) and isinstance(connections, (int, float)):
            conn_pct = (connections / max_connections) * 100
            lines.append(f"📊 Connection usage: {conn_pct:.1f}% ({connections}/{max_connections})")
        
    except Exception:
        lines.append("🔌 PostgreSQL connections: n/a")
    
    # === Idle in Transaction Analysis ===
    if show_idle_transactions or "idle" in alertname.lower():
        try:
            # Idle in transaction count
            idle_expr = f'pg_stat_activity_count{{instance="{pg_instance}",state="idle in transaction"}}'
            idle_count = prom.last_value(idle_expr)
            if isinstance(idle_count, (int, float)):
                lines.append(f"😴 Idle in transaction: {idle_count} sessions")
                
                if idle_count > 0:
                    lines.append("")
                    lines.append("🛠️ **Диагностика idle in transaction:**")
                    lines.extend([
                        "• `SELECT pid, usename, application_name, state_change FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < now() - interval '10 minutes';`",
                        "• `SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE state = 'idle in transaction' AND state_change < now() - interval '30 minutes';`",
                        "• Проверить настройки приложения на connection pooling",
                        "• Установить idle_in_transaction_session_timeout в postgresql.conf"
                    ])
        except Exception:
            lines.append("😴 Idle transactions: n/a")
    
    # === Connection Analysis ===
    if show_connections:
        try:
            # Connections by state
            active_expr = f'pg_stat_activity_count{{instance="{pg_instance}",state="active"}}'
            idle_expr = f'pg_stat_activity_count{{instance="{pg_instance}",state="idle"}}'
            
            active = prom.last_value(active_expr)
            idle = prom.last_value(idle_expr)
            
            if isinstance(active, (int, float)):
                lines.append(f"⚡ Active queries: {active}")
            if isinstance(idle, (int, float)):
                lines.append(f"💤 Idle connections: {idle}")
                
        except Exception:
            lines.append("📊 Connection breakdown: n/a")
    
    # === Lock Analysis ===
    if show_locks:
        try:
            # Waiting locks
            locks_expr = f'pg_locks_count{{instance="{pg_instance}",mode="AccessExclusiveLock"}}'
            locks = prom.last_value(locks_expr)
            if isinstance(locks, (int, float)) and locks > 0:
                lines.append(f"🔒 Exclusive locks waiting: {locks}")
                lines.append("")
                lines.append("🛠️ **Анализ блокировок:**")
                lines.extend([
                    "• `SELECT * FROM pg_locks WHERE NOT granted;`",
                    "• `SELECT pid, usename, query, state FROM pg_stat_activity WHERE wait_event_type = 'Lock';`",
                    "• `SELECT pg_cancel_backend(pid) FROM pg_stat_activity WHERE wait_event_type = 'Lock';`"
                ])
        except Exception:
            lines.append("🔒 Lock analysis: n/a")
    
    # === Slow Query Recommendations ===
    if "slow" in alertname.lower():
        lines.append("")
        lines.append("🐌 **Анализ медленных запросов:**")
        lines.extend([
            "• `SELECT query, mean_exec_time, calls FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 5;`",
            "• `SELECT pid, now() - pg_stat_activity.query_start AS duration, query FROM pg_stat_activity WHERE (now() - pg_stat_activity.query_start) > interval '1 minutes';`",
            "• Проверить наличие нужных индексов: `EXPLAIN ANALYZE <query>`",
            "• Настроить log_min_duration_statement для детального логирования"
        ])
    
    # === General PostgreSQL Recommendations ===
    recommendations = []
    
    if "connection" in alertname.lower():
        recommendations.extend([
            "• Настроить connection pooling (pgbouncer, pgpool)",
            "• Проверить max_connections в postgresql.conf", 
            "• Мониторить утечки соединений в приложениях"
        ])
    
    if "deadlock" in alertname.lower():
        recommendations.extend([
            "• Анализ deadlock_timeout в postgresql.conf",
            "• Логирование deadlocks: log_lock_waits = on",
            "• Оптимизация порядка обращения к таблицам в транзакциях"
        ])
    
    # === Database Size and Activity ===
    try:
        # Database size
        db_size_expr = f'pg_database_size_bytes{{instance="{pg_instance}"}}'
        db_size = prom.last_value(db_size_expr)
        if isinstance(db_size, (int, float)):
            size_gb = db_size / (1024**3)
            lines.append(f"💿 Database size: {size_gb:.2f} GB")
            
        # Commits and rollbacks
        commit_expr = f'rate(pg_stat_database_xact_commit{{instance="{pg_instance}"}}[5m])'
        rollback_expr = f'rate(pg_stat_database_xact_rollback{{instance="{pg_instance}"}}[5m])'
        
        commits = prom.last_value(commit_expr)
        rollbacks = prom.last_value(rollback_expr)
        
        if isinstance(commits, (int, float)):
            lines.append(f"✅ Commits/sec: {commits:.1f}")
        if isinstance(rollbacks, (int, float)):
            lines.append(f"❌ Rollbacks/sec: {rollbacks:.1f}")
            
    except Exception:
        lines.append("💿 Database activity: n/a")
    
    if recommendations:
        lines.append("")
        lines.append("🛠️ **Общие рекомендации:**")
        lines.extend(recommendations)
    
    return {
        "title": f"PostgreSQL Analysis - {inst}",
        "lines": lines
    }