#!/bin/bash
# Скрипт для симуляции COLLSCAN операций в MongoDB для тестирования

HOST="centos-s-1vcpu-512mb-10gb-fra1-01"
PORT="27017"
USER="zabbix"
PASS="zabbix"
DB="testdb"

echo "🧪 Создание тестовых данных для симуляции COLLSCAN..."

# Подключение к MongoDB и выполнение медленных запросов
mongo --host $HOST:$PORT --username $USER --password $PASS --authenticationDatabase admin << EOF

// Переключаемся на тестовую базу
use $DB;

// Создаем коллекцию с тестовыми данными (если не существует)
if (db.test_collection.countDocuments() < 1000) {
    print("Создаем тестовые данные...");
    var docs = [];
    for (let i = 0; i < 1000; i++) {
        docs.push({
            name: "user_" + i,
            age: Math.floor(Math.random() * 80) + 18,
            city: ["Moscow", "SPb", "Kazan", "Novosibirsk"][Math.floor(Math.random() * 4)],
            created_at: new Date(),
            metadata: {
                score: Math.random() * 100,
                tags: ["tag" + (i % 10), "category" + (i % 5)]
            }
        });
    }
    db.test_collection.insertMany(docs);
    print("Создано " + docs.length + " документов");
}

// Включаем профилирование для медленных операций
db.setProfilingLevel(1, { slowms: 50 });
print("Профилирование включено для запросов > 50ms");

print("🔍 Выполняем медленные запросы без индексов (COLLSCAN)...");

// 1. Запрос по полю без индекса
print("1. Поиск по age без индекса...");
db.test_collection.find({age: {$gt: 50}}).explain("executionStats");

// 2. Запрос с регулярным выражением
print("2. Поиск по регулярному выражению...");
db.test_collection.find({name: /user_5/}).explain("executionStats");

// 3. Запрос по вложенному полю
print("3. Поиск по вложенному полю...");
db.test_collection.find({"metadata.score": {$gt: 80}}).explain("executionStats");

// 4. Сортировка без индекса
print("4. Сортировка без индекса...");
db.test_collection.find().sort({age: -1}).limit(10).explain("executionStats");

// 5. Агрегация без индексов
print("5. Агрегация без индексов...");
db.test_collection.aggregate([
    {\$match: {city: "Moscow"}},
    {\$sort: {age: -1}},
    {\$limit: 5}
]).explain("executionStats");

print("✅ Медленные запросы выполнены. Проверьте логи MongoDB и метрики Telegraf");

// Показываем последние медленные операции из профайлера
print("📊 Последние медленные операции:");
db.system.profile.find().sort({ts: -1}).limit(5).forEach(function(doc) {
    print("Время: " + doc.ts + ", Длительность: " + doc.millis + "ms, Команда: " + doc.command.find);
});

EOF

echo "🎯 Для проверки алертов выполните:"
echo "   1. Проверьте лogi MongoDB: tail -f /var/log/mongodb/mongod.log"
echo "   2. Проверьте метрики Telegraf: curl http://$HOST:9216/metrics | grep mongodb"
echo "   3. Запустите тест: python test_integration.py"

# Симуляция записи в лог (если MongoDB логи недоступны)
LOGFILE="/tmp/mongod_test.log"
echo "📝 Создание тестового лога MongoDB в $LOGFILE"

cat > $LOGFILE << 'EOLOG'
2024-01-15T10:30:15.123+0000 I COMMAND  [conn1] command testdb.test_collection planSummary: COLLSCAN keysExamined:0 docsExamined:1000 nReturned:245 executionTimeMillis:856 works:1002 advanced:245 needTime:756 needYield:0 saveState:7 restoreState:7 isEOF:1 queryHash:B1C34567 planCacheKey:A2B34567 locks:{ Global: { acquireCount: { r: 8 } }, Database: { acquireCount: { r: 8 } }, Collection: { acquireCount: { r: 8 } } } protocol:op_msg 856ms
2024-01-15T10:30:16.890+0000 I COMMAND  [conn2] command testdb.test_collection planSummary: COLLSCAN keysExamined:0 docsExamined:1000 nReturned:89 executionTimeMillis:654 works:1002 advanced:89 needTime:912 needYield:0 saveState:5 restoreState:5 isEOF:1 queryHash:C2D34567 planCacheKey:B3C34567 locks:{ Global: { acquireCount: { r: 6 } }, Database: { acquireCount: { r: 6 } }, Collection: { acquireCount: { r: 6 } } } protocol:op_msg 654ms
2024-01-15T10:30:18.456+0000 I COMMAND  [conn3] command testdb.users planSummary: COLLSCAN keysExamined:0 docsExamined:5000 nReturned:1250 executionTimeMillis:1234 works:5002 advanced:1250 needTime:3751 needYield:0 saveState:39 restoreState:39 isEOF:1 queryHash:D3E34567 planCacheKey:C4D34567 locks:{ Global: { acquireCount: { r: 40 } }, Database: { acquireCount: { r: 40 } }, Collection: { acquireCount: { r: 40 } } } protocol:op_msg 1234ms
EOLOG

echo "✅ Тестовый лог создан: $LOGFILE"
echo "   Измените путь в telegraf.conf: files = [\"$LOGFILE\"]"