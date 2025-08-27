# Патч для редактирования сообщений при resolved alerts

## Шаг 1: Обновить импорты в seed-agent.py

```python
# Добавить в секцию импортов
from core.message_tracker import MessageTracker
from core.notify_enhanced import EnhancedNotificationManager
```

## Шаг 2: Обновить класс SeedAgent

```python
class SeedAgent:
    def __init__(self, config_path: str = "seed.yaml"):
        # Existing initialization...
        
        # Добавить после инициализации throttler
        self.message_tracker = MessageTracker(self.throttler)
        
        # Заменить обычный NotificationManager на Enhanced
        self.notification_manager = EnhancedNotificationManager(self.config, self.message_tracker)
```

## Шаг 3: Обновить process_alert для поддержки resolved

В методе `process_alert()` добавить проверку статуса:

```python
async def process_alert(self, alert_data: dict) -> dict:
    # Existing code...
    
    # Определить тип алерта
    status = alert_data.get("status", "firing")
    labels = alert_data.get("labels", {})
    alertname = labels.get("alertname", "Unknown")
    
    # Проверить, является ли это resolved alert
    if status == "resolved":
        logger.info(f"🔄 Processing resolved alert: {alertname}")
        
        # Enhanced notification manager автоматически обработает resolved
        await self.notification_manager.send_alert_notification(alert_data, llm_result)
        
        return {
            "success": True,
            "message": f"Resolved alert processed: {alertname}",
            "alert_updated": True
        }
    
    # Обычная обработка firing alerts
    # ... existing code
```

## Шаг 4: Конфигурация Redis (seed.yaml)

Убедиться что Redis настроен для хранения message tracking:

```yaml
redis:
  host: localhost
  port: 6379
  db: 0
  # password: optional
```

## Шаг 5: Логика resolved сообщений

Система будет:

1. **При firing alert:** 
   - Отправить обычное сообщение
   - Сохранить message_id в Redis

2. **При resolved alert:**
   - Найти оригинальное сообщение в Redis
   - Создать resolved версию с:
     - ✅ Эмодзи resolved
     - Информацией о том, что проблема решена
     - Рекомендациями по проверке
     - Оригинальным текстом проблемы
   - Отправить обновлённое сообщение

## Пример resolved сообщения:

```
🌌 SEED
💎✅ MongoDB Процессов нет ЭТО ТЕСТ (RESOLVED)

📍 Сервер: p-homesecurity-mng-adv-msk01:27017
⏰ Resolved: 2025-08-27T14:15:30Z
📝 Описание: Alert resolved

✅ Статус: РАЗРЕШЕНО

🔍 Рекомендации:
• Проверь что проблема действительно устранена
• Убедись что система работает в штатном режиме  
• Мониторь метрики в течение следующих 15-30 минут

📊 Оригинальная проблема:
• Проверь доступность MongoDB через CLI
• Убедись что процессы запущены
• Проверь логи на ошибки соединения

— Powered by 🌌 SEED ✅
```

## Ограничения текущей реализации:

- **Mattermost Webhooks** не поддерживают редактирование сообщений
- Для полного редактирования нужен **Bot Token** и Posts API
- Пока что отправляется новое сообщение с пометкой "UPDATE"

## Для полного редактирования нужно:

1. Настроить Mattermost Bot с Personal Access Token
2. Использовать Posts API вместо Webhooks
3. Сохранять post_id в Redis для последующего редактирования