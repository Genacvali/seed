#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрация нового компактного формата
Показывает как будет выглядеть сообщение
"""

def demo_new_format():
    """Демонстрация нового формата"""
    
    # Пример в стиле вашего сообщения - ИСПРАВЛЕННЫЙ
    example_message = """🚨 p-homesecurity-mng-adv-msk01:27017: MongoDB Процессов нет ЭТО ТЕСТ
📍 Production // ⚔️HIGH // #T4A7B2830
🔌 RedHat, DB/MongoDB, production, mongodb-exporter, homesecurity, adv
📆 17:12:58 - 2025.08.27 17:17:27 // ⏱️ 4m 33s

### 💎 Возможные проблемы:
• Служба MongoDB была остановлена или упала
• Процесс mongod завершился с ошибкой  
• Недостаточно места на диске для работы MongoDB

### ⚔️ Рекомендации:
```bash
systemctl status mongod
systemctl start mongod
journalctl -u mongod --since "10 minutes ago"
df -h /var/lib/mongo
```

— 🌌 SEED ✨"""

    print("=== НОВЫЙ КОМПАКТНЫЙ ФОРМАТ SEED AGENT V5 ===\n")
    print(example_message)
    print("\n" + "="*70)
    
    # Пример resolved сообщения
    resolved_example = """✅ p-homesecurity-mng-adv-msk01:27017: MongoDB Процессов нет РЕШЕН
📍 Production // ✅RESOLVED // #T4A7B2830
📆 17:20:15 - 2025.08.27 17:20:15

🎉 Проблема устранена

— 🌌 SEED ✨"""

    print("\nПРИМЕР RESOLVED СООБЩЕНИЯ:")
    print(resolved_example)
    print("\n" + "="*70)
    
    print("\nОСОБЕННОСТИ ОБНОВЛЕННОГО ФОРМАТА:")
    print("✅ Компактная структура точно как в вашем примере")
    print("✅ Фирменные FF-иконки: 💎🔥 ⚔️ 🛡️ ✨ ❔")  
    print("✅ Убрано дублирование текста в первой строке")
    print("✅ Автоматические технические теги из меток")
    print("✅ Уникальные ID алертов (#T + hash)")
    print("✅ Цветные уведомления Mattermost")
    print("✅ Раздельные секции: 'Возможные проблемы' и 'Рекомендации'")
    print("✅ Время в формате HH:MM:SS + полная дата")
    print("✅ Тротлинг защита 120 секунд")

if __name__ == "__main__":
    demo_new_format()