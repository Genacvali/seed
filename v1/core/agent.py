# -*- coding: utf-8 -*-
import json
from core.bus import consume
from core.config import load_settings, resolve_handler
from core.notifier import send_mm

def _on_alert(msg: bytes):
    try:
        alert = json.loads(msg.decode("utf-8"))
    except Exception:
        send_mm("SEED: ⚠️ не-JSON сообщение получено, пропускаю.")
        return
    # 1) роутинг по конфигу → имя плагина + payload-defaults
    plugin_name, payload = resolve_handler(alert)
    if not plugin_name:
        return send_mm(f"SEED: 🤷 не найден обработчик для type='{alert.get('type')}'")
    # 2) загрузка и вызов плагина
    try:
        mod = __import__(f"plugins.{plugin_name}", fromlist=["run"])
        text = mod.run(alert["host"], payload)   # всегда (host: str, payload: dict) -> str
        if text:
            send_mm(text)
    except Exception as e:
        send_mm(f"SEED: ❌ Ошибка плагина `{plugin_name}`: {e}")

def main():
    load_settings()      # загрузим конфиг и плагины в память
    consume(_on_alert)   # слушаем RabbitMQ и передаём сообщения коллбэку

if __name__ == "__main__":
    main()