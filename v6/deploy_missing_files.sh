#!/bin/bash
# Скрипт для развертывания недостающих файлов системы плагинов на production

echo "🚀 Deploying missing files for SEED v6 Plugin System"
echo "========================================================"

# 1. Создаем plugin_router.py
echo "📄 Creating plugin_router.py..."
cat > plugin_router.py << 'EOF'
# v6/plugin_router.py
"""
Система маршрутизации алертов к плагинам
"""
import os
import yaml
import importlib.util
from typing import Dict, List, Optional, Any
import traceback

class PluginRouter:
    def __init__(self):
        self.routes = []
        self.default_plugin = "echo"
        self.default_params = {}
        self.plugins_cache = {}
        self.load_config()
    
    def load_config(self):
        """Загружает конфигурацию маршрутизации из alerts.yaml"""
        config_path = os.path.join(os.path.dirname(__file__), "configs", "alerts.yaml")
        
        if not os.path.exists(config_path):
            print(f"[PLUGIN] Warning: {config_path} not found, using default routing")
            return
            
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            self.routes = config.get('routes', [])
            self.default_plugin = config.get('default_plugin', 'echo')
            self.default_params = config.get('default_params', {})
            
            print(f"[PLUGIN] Loaded {len(self.routes)} routes, default: {self.default_plugin}")
            
        except Exception as e:
            print(f"[PLUGIN] Error loading config: {e}")
    
    def match_alert(self, alert: Dict[str, Any]) -> tuple:
        """
        Находит подходящий плагин для алерта
        Возвращает (plugin_name, params)
        """
        labels = alert.get("labels", {})
        
        # Проверяем каждый маршрут
        for route in self.routes:
            match_rules = route.get("match", {})
            
            # Проверяем все условия в match
            all_match = True
            for key, expected_value in match_rules.items():
                actual_value = labels.get(key)
                
                if actual_value != expected_value:
                    all_match = False
                    break
            
            if all_match:
                plugin_name = route.get("plugin", self.default_plugin)
                params = route.get("params", {})
                print(f"[PLUGIN] Alert '{labels.get('alertname', 'Unknown')}' → {plugin_name}")
                return plugin_name, params
        
        # Если ничего не подошло - используем default
        print(f"[PLUGIN] Alert '{labels.get('alertname', 'Unknown')}' → {self.default_plugin} (default)")
        return self.default_plugin, self.default_params
    
    def load_plugin(self, plugin_name: str):
        """Загружает плагин по имени"""
        if plugin_name in self.plugins_cache:
            return self.plugins_cache[plugin_name]
        
        plugin_path = os.path.join(os.path.dirname(__file__), "plugins", f"{plugin_name}.py")
        
        if not os.path.exists(plugin_path):
            print(f"[PLUGIN] Error: Plugin file not found: {plugin_path}")
            return None
        
        try:
            # Динамическая загрузка модуля
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Проверяем наличие функции run
            if not hasattr(module, 'run'):
                print(f"[PLUGIN] Error: Plugin {plugin_name} missing 'run' function")
                return None
            
            self.plugins_cache[plugin_name] = module
            print(f"[PLUGIN] Loaded plugin: {plugin_name}")
            return module
            
        except Exception as e:
            print(f"[PLUGIN] Error loading plugin {plugin_name}: {e}")
            print(f"[PLUGIN] Traceback: {traceback.format_exc()}")
            return None
    
    def run_plugin(self, alert: Dict[str, Any], prom_client) -> Optional[Dict[str, Any]]:
        """
        Выполняет соответствующий плагин для алерта
        Возвращает результат плагина или None при ошибке
        """
        plugin_name, params = self.match_alert(alert)
        
        # Загружаем плагин
        plugin_module = self.load_plugin(plugin_name)
        if not plugin_module:
            # Fallback к echo плагину
            if plugin_name != "echo":
                print(f"[PLUGIN] Fallback to echo plugin")
                plugin_module = self.load_plugin("echo")
                params = self.default_params
            
            if not plugin_module:
                return None
        
        try:
            # Выполняем плагин
            result = plugin_module.run(alert, prom_client, params)
            
            if result and isinstance(result, dict):
                print(f"[PLUGIN] Success: {plugin_name} returned {len(result.get('lines', []))} lines")
                return result
            else:
                print(f"[PLUGIN] Warning: {plugin_name} returned invalid result")
                return None
                
        except Exception as e:
            print(f"[PLUGIN] Error running {plugin_name}: {e}")
            print(f"[PLUGIN] Traceback: {traceback.format_exc()}")
            return None
    
    def get_plugin_info(self) -> Dict[str, Any]:
        """Возвращает информацию о загруженных плагинах"""
        return {
            "routes_count": len(self.routes),
            "default_plugin": self.default_plugin,
            "loaded_plugins": list(self.plugins_cache.keys()),
            "available_plugins": [
                f.replace('.py', '') 
                for f in os.listdir(os.path.join(os.path.dirname(__file__), "plugins"))
                if f.endswith('.py') and f != '__init__.py'
            ]
        }


# Создаем глобальный экземпляр роутера
plugin_router = PluginRouter()
EOF

# 2. Создаем configs/alerts.yaml
echo "📄 Creating configs/alerts.yaml..."
mkdir -p configs
cat > configs/alerts.yaml << 'EOF'
# SEED v6 - Alert to Plugin Mapping Configuration
# Маппинг алертов к плагинам для специализированной обработки

routes:
  # === OS/System Alerts ===
  - match: { alertname: "DiskSpaceLow" }
    plugin: "os_basic" 
    params: { show_paths: ["/", "/data", "/var/lib"], lookback: "15m" }

  - match: { alertname: "DiskSpaceHigh" }
    plugin: "os_basic"
    params: { show_paths: ["/", "/var/lib/postgresql", "/data"], lookback: "15m" }
    
  - match: { alertname: "HighCPUUsage" }
    plugin: "os_basic"
    params: { show_processes: true, lookback: "10m" }

  - match: { alertname: "HighMemoryUsage" }
    plugin: "os_basic" 
    params: { show_processes: true, show_swap: true, lookback: "10m" }

  - match: { alertname: "LoadAverage" }
    plugin: "os_basic"
    params: { show_processes: true, lookback: "5m" }

  # === MongoDB Alerts ===
  - match: { alertname: "MongoCollscan" }
    plugin: "mongo_hot"
    params: { show_host_metrics: true, lookback: "5m", top_collections: 5 }

  - match: { alertname: "MongoSlowQuery" }
    plugin: "mongo_hot"
    params: { show_host_metrics: true, lookback: "10m", slow_threshold: 1000 }

  - match: { alertname: "MongoReplicaLag" }
    plugin: "mongo_hot"
    params: { show_replica_status: true, show_host_metrics: true }

  - match: { alertname: "MongoConnections" }
    plugin: "mongo_hot"
    params: { show_connections: true, show_host_metrics: true }

  # === PostgreSQL Alerts ===
  - match: { alertname: "PostgresSlowQuery" }
    plugin: "pg_slow"
    params: { top: 5, show_host_metrics: true, min_duration: "1s" }

  - match: { alertname: "PG_IdleInTransaction_Storm" }
    plugin: "pg_slow"
    params: { show_idle_transactions: true, show_host_metrics: true, top: 10 }

  - match: { alertname: "PostgresConnections" }
    plugin: "pg_slow"
    params: { show_connections: true, show_host_metrics: true }

  - match: { alertname: "PostgresDeadlocks" }
    plugin: "pg_slow"
    params: { show_locks: true, show_host_metrics: true, top: 5 }

  # === Network & Services ===
  - match: { alertname: "InstanceDown" }
    plugin: "host_inventory"
    params: { show_services: true, ping_test: true }

  - match: { alertname: "ServiceDown" }
    plugin: "host_inventory"
    params: { show_services: true, check_ports: true }

  - match: { alertname: "HighNetworkTraffic" }
    plugin: "os_basic"
    params: { show_network: true, lookback: "10m" }

  # === Zabbix Integration ===
  - match: { alertname: "Zabbix agent on * is unreachable" }
    plugin: "host_inventory"
    params: { show_services: ["zabbix-agent", "zabbix-agent2"], ping_test: true }

  # === Generic/Fallback ===
  - match: { severity: "critical" }
    plugin: "os_basic"
    params: { show_host_metrics: true, lookback: "5m" }

# Default plugin when no routes match
default_plugin: "echo"
default_params: { show_basic_info: true }
EOF

# 3. Обновляем prom.py с исправлениями
echo "📄 Updating prom.py with query_value function..."
cat > prom.py << 'EOF'
# -*- coding: utf-8 -*-
import os, requests

PROM_URL = os.getenv("PROM_URL", "").rstrip("/")
PROM_BEARER = os.getenv("PROM_BEARER", "")
PROM_VERIFY_SSL = os.getenv("PROM_VERIFY_SSL", "1") not in ("0", "false")
PROM_TIMEOUT = int(os.getenv("PROM_TIMEOUT", "3"))

def _call(path: str, params: dict):
    """Базовый HTTP-вызов к Prometheus"""
    if not PROM_URL:
        return None
    url = PROM_URL + path
    headers = {}
    if PROM_BEARER:
        headers["Authorization"] = f"Bearer {PROM_BEARER}"
    
    r = requests.get(url, params=params, headers=headers, 
                     timeout=PROM_TIMEOUT, verify=PROM_VERIFY_SSL)
    r.raise_for_status()
    j = r.json()
    
    if j.get("status") == "success":
        return j.get("data", {}).get("result", [])
    return None

def query(expr: str, ts: float = None):
    """Моментальный запрос /api/v1/query"""
    p = {"query": expr}
    if ts is not None:
        p["time"] = str(ts)
    return _call("/api/v1/query", p)

def query_range(expr: str, start: float, end: float, step: str = "30s"):
    """Диапазон /api/v1/query_range"""
    p = {"query": expr, "start": start, "end": end, "step": step}
    return _call("/api/v1/query_range", p)

def last_value(result: list) -> float:
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

def query_value(expr: str, ts: float = None) -> float:
    """Удобная функция: запрос + извлечение значения"""
    result = query(expr, ts)
    return last_value(result)
EOF

echo "✅ Files created successfully!"
echo ""
echo "📋 Next steps:"
echo "1. Restart SEED Agent: ./stop.sh && ./start.sh"
echo "2. Test plugin system: python3 test_plugin_system.py"
echo "3. Check logs: tail -f logs/agent.log | grep PLUGIN"