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
    
    # === Additional Disk Usage (only /data since / is in enrichment) ===
    if "/data" not in show_paths:
        show_paths = ["/data"]  # Force /data check
        
    for path in show_paths:
        if path != "/":  # Skip root, it's already in enrichment summary
            try:
                disk_expr = f'''100 * (node_filesystem_size_bytes{{instance="{inst_with_port}",mountpoint="{path}",fstype!~"tmpfs|overlay"}} 
                               - node_filesystem_avail_bytes{{instance="{inst_with_port}",mountpoint="{path}",fstype!~"tmpfs|overlay"}})
                               / node_filesystem_size_bytes{{instance="{inst_with_port}",mountpoint="{path}",fstype!~"tmpfs|overlay"}}'''
                disk = prom.query_value(disk_expr.replace('\n', '').strip())
                if isinstance(disk, (int, float)):
                    icon = "🔴" if disk > 90 else "🟡" if disk > 80 else "🟢"
                    lines.append(f"{icon} Disk {path}: {disk:.1f}%")
            except Exception:
                lines.append(f"💽 Disk {path}: n/a")
    
    # === Network Traffic (only if requested) ===
    if show_network:
        try:
            # Network RX/TX bytes per second
            net_rx_expr = f'rate(node_network_receive_bytes_total{{instance="{inst_with_port}",device!~"lo|docker.*|veth.*"}}[5m]) * 8'
            net_tx_expr = f'rate(node_network_transmit_bytes_total{{instance="{inst_with_port}",device!~"lo|docker.*|veth.*"}}[5m]) * 8'
            
            net_rx = prom.query_value(net_rx_expr)
            net_tx = prom.query_value(net_tx_expr)
            
            if isinstance(net_rx, (int, float)) and isinstance(net_tx, (int, float)):
                rx_mbps = net_rx / 1_000_000  # Convert to Mbps
                tx_mbps = net_tx / 1_000_000
                lines.append(f"📡 Network: ↓{rx_mbps:.1f} Mbps / ↑{tx_mbps:.1f} Mbps")
            else:
                lines.append("📡 Network: n/a")
        except Exception:
            lines.append("📡 Network: n/a")
    
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