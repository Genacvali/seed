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