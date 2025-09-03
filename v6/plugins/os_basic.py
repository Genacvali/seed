# v6/plugins/os_basic.py
"""
Базовый плагин для OS метрик (CPU, Memory, Disk, Load Average)
"""

def run(alert: dict, prom, params: dict) -> dict:
    """
    OS-related metrics: CPU, memory, disk, network, processes
    """
    labels = alert.get("labels", {})
    inst = labels.get("instance", "unknown")
    alertname = labels.get("alertname", "SystemAlert")
    
    # Используем только hostname без порта для OS метрик
    inst_with_port = inst.split(":")[0]
    
    lines = []
    lookback = params.get("lookback", "15m")
    show_paths = params.get("show_paths", ["/"])
    show_processes = params.get("show_processes", False)
    show_network = params.get("show_network", False)
    show_swap = params.get("show_swap", False)
    show_host_metrics = params.get("show_host_metrics", True)
    
    # Все метрики теперь показываются в enrichment summary line сверху
    # Плагин показывает только рекомендации
    
    # === Recommendations ===
    recommendations = []
    
    if "cpu" in alertname.lower() or "CPU" in alertname:
        recommendations.extend([
            "• Check top processes: `htop` or `ps aux --sort=-%cpu`",
            "• Analyze CPU usage: `iostat 1` or `sar -u 1`",
            "• Consider scaling or optimizing high-CPU processes"
        ])
    
    if "memory" in alertname.lower() or "Memory" in alertname:
        recommendations.extend([
            "• Check memory consumers: `ps aux --sort=-%mem`",
            "• Clear page cache if safe: `echo 1 > /proc/sys/vm/drop_caches`",
            "• Check for memory leaks in applications"
        ])
    
    if "disk" in alertname.lower() or "Disk" in alertname:
        recommendations.extend([
            "• Find large files: `du -sh /* | sort -rh | head -10`",
            "• Clean temp files: `find /tmp -type f -atime +7 -delete`",
            "• Check log rotation and cleanup old logs"
        ])
    
    if "load" in alertname.lower() or "Load" in alertname:
        recommendations.extend([
            "• Check I/O wait: `iotop` or `iostat -x 1`",
            "• Review running processes: `ps aux | head -20`",
            "• Check for hung processes or high I/O operations"
        ])
    
    if recommendations:
        lines.append("")
        lines.append("🛠️ **Рекомендации:**")
        lines.extend(recommendations)
    
    return {
        "title": f"System Metrics - {inst}",
        "lines": lines
    }