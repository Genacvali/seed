#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрация нового компактного формата
Показывает как будет выглядеть сообщение
"""

def demo_new_format():
    """Демонстрация нового формата"""
    
    # Пример в стиле вашего сообщения
    example_message = """🚨 p-homesecurity-mng-adv-msk01:27017: MongoDB Процессов нет Процессы MongoDB не найдены на сервере
📍 Production // ⚔️🤒HIGH // #T4A7B2830
🔌 RedHat, DB/MongoDB, production, mongodb-exporter, homesecurity, adv
📆 17:12:58 - 2025.08.27 17:17:27 // ⏱️ 4m 33s

• Служба MongoDB была остановлена или упала
• Процесс mongod завершился с ошибкой  
• Недостаточно места на диске для работы MongoDB

systemctl status mongod
systemctl start mongod
journalctl -u mongod --since "10 minutes ago"
df -h /var/lib/mongo

🔎 *Полный анализ в логах*

— 🌌 SEED ✨"""

    print("=== НОВЫЙ КОМПАКТНЫЙ ФОРМАТ SEED AGENT V5 ===\n")
    print(example_message)
    print("\n" + "="*70)
    
    # Пример resolved сообщения
    resolved_example = """✅ p-homesecurity-mng-adv-msk01:27017: MongoDB Процессов нет РЕШЕН
📍 Production // ✅RESOLVED
📆 17:20:15 - 2025.08.27 17:20:15

🎉 Проблема устранена

— 🌌 SEED ✨"""

    print("\nПРИМЕР RESOLVED СООБЩЕНИЯ:")
    print(resolved_example)
    print("\n" + "="*70)
    
    print("\nОСОБЕННОСТИ НОВОГО ФОРМАТА:")
    print("✅ Компактная структура как в вашем примере")
    print("✅ Сохранены FF-иконки: 💎🔥 ⚔️🤒 🛡️⚠️ ✨ℹ️")  
    print("✅ Автоматические технические теги из меток")
    print("✅ Уникальные ID алертов (#T + hash)")
    print("✅ Цветные уведомления Mattermost")
    print("✅ LLM-анализ сжат до 400 символов")
    print("✅ Время в формате HH:MM:SS + полная дата")
    print("✅ Тротлинг защита 120 секунд")

if __name__ == "__main__":
    demo_new_format()