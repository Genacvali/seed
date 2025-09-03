# -*- coding: utf-8 -*-

def run(alert: dict, prom_client, params: dict) -> dict:
    """
    MongoDB slow query analysis plugin
    Provides MongoDB performance diagnostics and recommendations
    """
    labels = alert.get("labels", {})
    annotations = alert.get("annotations", {})
    instance = labels.get("instance", "unknown")
    database = labels.get("database", "unknown")
    alertname = labels.get("alertname", "MongoSlowQuery")
    
    # Extract host without port for MongoDB metrics
    host = instance.split(":")[0]
    
    lines = []
    
    # === MongoDB Connection Stats ===
    try:
        # MongoDB connections
        mongo_conn_expr = f'mongodb_connections{{instance="{instance}"}}'
        mongo_conns = prom_client.query_value(mongo_conn_expr)
        if isinstance(mongo_conns, (int, float)):
            lines.append(f"🔗 MongoDB Connections: {mongo_conns:.0f}")
    except Exception:
        lines.append("🔗 MongoDB Connections: n/a")
    
    # === MongoDB Operations Stats ===
    try:
        # Operations per second
        ops_expr = f'rate(mongodb_opcounters_total{{instance="{instance}"}}[5m])'
        ops_result = prom_client.query(ops_expr)
        if ops_result:
            total_ops = sum(float(item["value"][1]) for item in ops_result if item.get("value"))
            lines.append(f"⚡ Operations/sec: {total_ops:.1f}")
    except Exception:
        lines.append("⚡ Operations/sec: n/a")
    
    # === Host Metrics ===
    show_host_metrics = params.get("show_host_metrics", True)
    if show_host_metrics:
        try:
            # CPU usage
            cpu_expr = f'100 * (1 - avg(rate(node_cpu_seconds_total{{instance="{host}",mode="idle"}}[5m])))'
            cpu = prom_client.query_value(cpu_expr)
            
            # Telegraf fallback
            if not isinstance(cpu, (int, float)):
                cpu_expr = f'100 - cpu_usage_idle{{instance="{instance}",port="9216"}}'
                cpu = prom_client.query_value(cpu_expr)
            
            lines.append(f"🔥 Host CPU: {cpu:.1f}%" if isinstance(cpu, (int, float)) else "🔥 Host CPU: n/a")
            
            # Memory usage
            mem_expr = f'100 * (1 - (node_memory_MemAvailable_bytes{{instance="{host}"}} / node_memory_MemTotal_bytes{{instance="{host}"}}))'
            mem = prom_client.query_value(mem_expr)
            
            # Telegraf fallback
            if not isinstance(mem, (int, float)):
                mem_expr = f'mem_used_percent{{instance="{instance}",port="9216"}}'
                mem = prom_client.query_value(mem_expr)
            
            lines.append(f"💾 Host Memory: {mem:.1f}%" if isinstance(mem, (int, float)) else "💾 Host Memory: n/a")
            
        except Exception as e:
            lines.append(f"❌ Host metrics error: {str(e)[:50]}")
    
    # === Slow Query Analysis ===
    slow_threshold = params.get("slow_threshold", 1000)
    lines.append("")
    lines.append(f"🐌 **MongoDB Slow Query Analysis** (threshold: {slow_threshold}ms)")
    
    # === Recommendations ===
    lines.append("")
    lines.append("🛠️ **Рекомендации:**")
    lines.extend([
        f"• Проверить индексы для БД '{database}': db.collection.getIndexes()",
        "• Анализ медленных запросов: db.setProfilingLevel(2, {slowms: 100})",
        "• Проверить план выполнения: query.explain('executionStats')",
        "• Оптимизировать запросы с большим docsExamined/returned ratio",
        "• Рассмотреть создание составных индексов для частых запросов"
    ])
    
    # === Collection Stats (if available) ===
    top_collections = params.get("top_collections", 5)
    if top_collections > 0:
        lines.append("")
        lines.append(f"📊 **Top {top_collections} Collections Analysis:**")
        lines.append("• Используйте db.stats() и db.collection.stats() для детального анализа")
        lines.append("• Проверьте размер коллекций и индексов")
    
    return {
        "title": f"MongoDB Analysis - {database} @ {host}",
        "lines": lines
    }