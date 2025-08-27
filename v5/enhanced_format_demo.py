#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Демонстрация нового адаптированного формата под стиль другого media type
Сравнение с оригинальной структурой
"""

def demo_enhanced_format():
    """Демонстрация адаптированного формата"""
    
    print("=== СРАВНЕНИЕ ФОРМАТОВ ===\n")
    
    # Ваш другой media type (оригинал)
    original_format = """{emjFail} <b>{HOST.HOST}</b>: {E}{EVENT.NAME}{/E}
{emjPoint} {$STAND} // {SEV{EVENT.NSEVERITY}} // #T{TRIGGER.ID} {ID4}
#HOSTGROUP '{emjQ} ' '{HOST.HOST}'#
{emjDate} {EVENT.TIME}
#ACK#
#SPLIT#
Z{EVENT.ID} // {HOST.NAME} // {HOST.IP}
{E}{TRIGGER.DESCRIPTION}{/E}
{TRIGGER.URL}
#SPLIT#
#GRAPH 3h '{ITEM.ID}:{ITEM.NAME}' '{ITEM.ID1}:{ITEM.NAME1}' '{ITEM.ID2}:{ITEM.NAME2}' '{ITEM.ID3}:{ITEM.NAME3}' '{ITEM.ID4}:{ITEM.NAME4}'#"""

    print("ОРИГИНАЛЬНАЯ СТРУКТУРА ДРУГОГО MEDIA TYPE:")
    print(original_format)
    print("\n" + "="*80 + "\n")
    
    # Адаптированный SEED формат
    seed_enhanced = """🚨 **p-homesecurity-mng-adv-msk01**: MongoDB Процессов нет ЭТО ТЕСТ
📍 Production // ⚔️HIGH // #T745832 5944
🔌 RedHat, DB/MongoDB, production, mongodb-exporter, homesecurity, adv
📆 2025.08.27 18:02:34

Z745832 // p-homesecurity-mng-adv-msk01 // 10.20.30.40

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

    print("SEED V5 АДАПТИРОВАННЫЙ ПОД ВАШ СТИЛЬ:")
    print(seed_enhanced)
    print("\n" + "="*80 + "\n")
    
    # Сравнительная таблица
    print("СООТВЕТСТВИЕ ПОЛЕЙ:")
    print("┌─────────────────────────┬─────────────────────────────────────┐")
    print("│ Оригинал                │ SEED Адаптированный                 │")
    print("├─────────────────────────┼─────────────────────────────────────┤")
    print("│ {emjFail} {HOST.HOST}   │ 🚨 **hostname**                     │")
    print("│ {EVENT.NAME}            │ alertname + описание                │")
    print("│ {$STAND}                │ Production (из конфига)             │")
    print("│ {SEV{EVENT.NSEVERITY}}  │ ⚔️HIGH (FF иконки + severity)       │")
    print("│ #T{TRIGGER.ID}          │ #T745832 (реальный/сгенер. ID)      │")
    print("│ {ID4}                   │ 5944 (случайный 4-знач)             │")
    print("│ {EVENT.TIME}            │ 📆 2025.08.27 18:02:34              │")
    print("│ Z{EVENT.ID}             │ Z745832 (идентификатор)             │")
    print("│ {HOST.NAME}             │ hostname без порта                  │")
    print("│ {HOST.IP}               │ IP адрес хоста (если есть)          │")
    print("│ {TRIGGER.DESCRIPTION}   │ Секция 'Возможные проблемы' + LLM  │")
    print("│ {TRIGGER.URL}           │ Секция 'Рекомендации' + команды    │")
    print("└─────────────────────────┴─────────────────────────────────────┘")
    
    print("\nДОПОЛНИТЕЛЬНЫЕ ВОЗМОЖНОСТИ SEED:")
    print("✅ LLM анализ проблем и автогенерация рекомендаций")
    print("✅ Цветные уведомления Mattermost (красный/оранжевый/желтый)")
    print("✅ Тротлинг защита от дублей (120 секунд)")
    print("✅ Автоматические технические теги из меток")
    print("✅ FF-стилизация эмодзи (💎⚔️🛡️✨)")
    print("✅ Сжатие LLM рекомендаций до 500 символов")
    print("✅ Поддержка resolved статусов")
    print("✅ Интеграция с множественными источниками (Alertmanager, Zabbix)")

if __name__ == "__main__":
    demo_enhanced_format()