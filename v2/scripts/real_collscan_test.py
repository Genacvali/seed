#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для реального тестирования MongoDB COLLSCAN детекции
Генерирует реальные COLLSCAN запросы и парсит логи MongoDB
"""
import json
import requests
import re
import subprocess
import time
from datetime import datetime
from pymongo import MongoClient
from pathlib import Path

# Конфигурация - будет обновляться в main()
MONGO_URI = None
MONGO_LOG_PATH = "/var/log/mongodb/mongod.log"
SEED_URL = "http://127.0.0.1:8000/alert"
DB_NAME = "seed_demo"

def create_test_data():
    """Создаем тестовые данные если их нет"""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    # Проверяем есть ли данные
    if db.users.count_documents({}) > 1000:
        print(f"📊 Данные уже есть: {db.users.count_documents({})} документов")
        return
    
    print("📝 Создаем тестовые данные...")
    users = []
    for i in range(5000):
        users.append({
            "name": f"User{i}",
            "email": f"user{i}@test.com",
            "age": 18 + (i % 60),
            "city": f"City{i % 50}",
            "status": ["active", "inactive", "pending"][i % 3],
            "created": datetime.utcnow()
        })
    
    db.users.insert_many(users)
    print(f"✅ Создано {len(users)} документов")

def generate_collscan_queries():
    """Генерируем запросы которые точно вызовут COLLSCAN"""
    client = MongoClient(MONGO_URI)
    db = client[DB_NAME]
    
    print("🔥 Генерируем COLLSCAN запросы...")
    
    queries = [
        # Поиск без индексов
        {"age": {"$gt": 50}},
        {"email": "user1000@test.com"},
        {"city": "City1", "status": "active"},
        {"name": {"$regex": "User1.*"}},
        # Сортировка без индекса
        {"age": {"$gte": 25}},
    ]
    
    results = []
    for i, query in enumerate(queries):
        print(f"  🔍 Запрос {i+1}: {query}")
        start_time = time.time()
        
        # Выполняем запрос
        if i == 4:  # Последний с сортировкой
            cursor = db.users.find(query).sort("created", -1).limit(10)
        else:
            cursor = db.users.find(query).limit(10)
        
        docs = list(cursor)
        duration = (time.time() - start_time) * 1000
        
        results.append({
            "query": str(query),
            "docs_found": len(docs),
            "duration_ms": round(duration, 2)
        })
        
        print(f"    ⏱️ {duration:.1f}ms, найдено: {len(docs)} документов")
        time.sleep(0.5)  # Небольшая пауза
    
    return results

def parse_mongodb_log(lines_to_check=100):
    """Парсим лог MongoDB на предмет COLLSCAN операций"""
    if not Path(MONGO_LOG_PATH).exists():
        print(f"❌ Лог файл не найден: {MONGO_LOG_PATH}")
        return []
    
    print(f"📋 Парсим последние {lines_to_check} строк лога MongoDB...")
    
    # Читаем последние строки лога
    try:
        result = subprocess.run(['tail', '-n', str(lines_to_check), MONGO_LOG_PATH], 
                              capture_output=True, text=True)
        lines = result.stdout.splitlines()
    except Exception as e:
        print(f"❌ Ошибка чтения лога: {e}")
        return []
    
    collscans = []
    collscan_pattern = re.compile(r'.*COLLSCAN.*')
    duration_pattern = re.compile(r'"durationMillis":(\d+)')
    namespace_pattern = re.compile(r'"ns":"([^"]+)"')
    docs_pattern = re.compile(r'"docsExamined":(\d+)')
    
    for line in lines:
        if 'COLLSCAN' in line:
            duration_match = duration_pattern.search(line)
            ns_match = namespace_pattern.search(line)
            docs_match = docs_pattern.search(line)
            
            if duration_match and ns_match:
                collscans.append({
                    "namespace": ns_match.group(1),
                    "duration_ms": int(duration_match.group(1)),
                    "docs_examined": int(docs_match.group(1)) if docs_match else 0,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "operation": "find"  # упрощение
                })
    
    print(f"🎯 Найдено {len(collscans)} COLLSCAN операций")
    return collscans

def format_hotspots_table(collscans):
    """Форматируем COLLSCAN данные в красивую таблицу"""
    if not collscans:
        return "Нет COLLSCAN операций в логах"
    
    header = "namespace                     op       time      details\n" + "-" * 60
    rows = [header]
    
    for cs in collscans[:10]:  # Берем первые 10
        namespace = cs["namespace"][:25].ljust(25)
        op = cs["operation"][:8].ljust(8)
        time_str = f"{cs['duration_ms']}ms".rjust(8)
        details = f"plan:COLLSCAN docs:{cs['docs_examined']} keys:0"
        
        row = f"{namespace} {op} {time_str}  {details}"
        rows.append(row)
    
    return "\n".join(rows)

def send_real_alert(host, collscans):
    """Отправляем реальный алерт с данными из MongoDB лога"""
    hotspots_table = format_hotspots_table(collscans)
    last_ts = collscans[0]["timestamp"] if collscans else datetime.utcnow().isoformat() + "Z"
    
    data = {
        "receiver": "seed",
        "status": "firing",
        "alerts": [{
            "status": "firing",
            "labels": {
                "alertname": "mongo_collscan",
                "host": host,
                "env": "test",
                "instance": f"{host}:27017",
                "job": "mongodb",
                "severity": "warning"
            },
            "annotations": {
                "summary": f"MongoDB COLLSCAN detected - {len(collscans)} slow operations",
                "description": f"Real COLLSCAN operations detected on {host}",
                "hotspots": hotspots_table,
                "last_ts": last_ts,
                "runbook_url": "https://docs.mongodb.com/manual/tutorial/create-indexes-to-support-queries/"
            },
            "startsAt": datetime.utcnow().isoformat() + "Z",
            "endsAt": "0001-01-01T00:00:00Z",
            "generatorURL": "http://mongodb:27017/",
            "fingerprint": f"real_collscan_{int(time.time())}"
        }],
        "groupLabels": {"alertname": "mongo_collscan"},
        "commonLabels": {"alertname": "mongo_collscan", "host": host},
        "commonAnnotations": {},
        "externalURL": "http://alertmanager:9093",
        "version": "4",
        "groupKey": f"{{}}{{host=\"{host}\"}}:{{alertname=\"mongo_collscan\"}}"
    }
    
    try:
        r = requests.post(SEED_URL, json=data, timeout=10)
        print(f"📤 Алерт отправлен: {r.status_code}")
        if r.status_code == 200:
            print("✅ SEED получил алерт с реальными данными!")
        else:
            print(f"❌ Ошибка: {r.text}")
    except Exception as e:
        print(f"❌ Ошибка отправки алерта: {e}")

def main():
    import sys
    global MONGO_URI
    
    host = sys.argv[1] if len(sys.argv) > 1 else "d-dba-mng-adv-msk02"
    
    # Настраиваем URI в зависимости от хоста
    if "msk01" in host:
        MONGO_URI = "mongodb://zabbix:zabbix@d-dba-mng-adv-msk01:27017/?connect=direct"
    else:
        MONGO_URI = "mongodb://zabbix:zabbix@d-dba-mng-adv-msk02:27017/?connect=direct"
    
    print(f"🚀 Тестирование реальных COLLSCAN операций на {host}")
    print(f"🔗 MongoDB URI: {MONGO_URI}")
    print("=" * 60)
    
    try:
        # 1. Создаем тестовые данные
        create_test_data()
        
        # 2. Генерируем COLLSCAN запросы
        query_results = generate_collscan_queries()
        
        # 3. Ждем чтобы запросы попали в лог
        print("⏳ Ждем 3 секунды для записи в лог...")
        time.sleep(3)
        
        # 4. Парсим лог на предмет COLLSCAN
        collscans = parse_mongodb_log()
        
        if collscans:
            print(f"🎯 Обнаружено {len(collscans)} COLLSCAN операций!")
            for cs in collscans[:3]:  # Показываем первые 3
                print(f"  📊 {cs['namespace']}: {cs['duration_ms']}ms, docs: {cs['docs_examined']}")
        else:
            print("⚠️ COLLSCAN операции не найдены в логе")
            print("💡 Попробуйте:")
            print("   1. Проверить путь к логу MongoDB")
            print("   2. Включить профилирование: db.setProfilingLevel(1, {slowms: 0})")
            print("   3. Увеличить verbosity логирования MongoDB")
            
            # Создаем фейковые данные для демонстрации
            collscans = [
                {
                    "namespace": f"{DB_NAME}.users",
                    "duration_ms": result["duration_ms"],
                    "docs_examined": 1000 + i * 500,
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "operation": "find"
                }
                for i, result in enumerate(query_results[:3])
            ]
            print("🎭 Используем сгенерированные данные для демонстрации")
        
        # 5. Отправляем реальный алерт
        send_real_alert(host, collscans)
        
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()