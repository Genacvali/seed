# 🌌 S.E.E.D. Agent v6.1 - Актуальная архитектура
*От серверов до Mattermost с Final Fantasy стилем*

## 🎮 Полная схема потока данных

```
┌─────────────────────────────────────────────────────────────────┐
│                    🖥️ INFRASTRUCTURE LAYER                      │
├─────────────────────────────────────────────────────────────────┤
│  🐘 PostgreSQL       🍃 MongoDB        🖥️ Linux Servers        │
│  prod-db01           prod-mongo01      nt-smi-mng-sc-msk03     │
│                                                                 │
│  📊 Metrics Sources:                                            │
│  • node_exporter:9100  (OS metrics)                            │
│  • telegraf:9216       (fallback metrics)                      │
│  • postgres_exporter   (DB metrics)                            │
│  • mongodb_exporter    (Mongo metrics)                         │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   📊 MONITORING LAYER                           │
├─────────────────────────────────────────────────────────────────┤
│                    🔍 Prometheus                                │
│                  (Metrics Storage)                              │
│                                                                 │
│  • Scrapes metrics from all exporters                          │
│  • Evaluates alerting rules                                    │
│  • Stores time-series data                                     │
│                                                                 │
│            ┌─────────────────────────────┐                     │
│            │     ⚠️ Alert Rules          │                     │
│            │                             │                     │
│            │  PostgresSlowQuery          │                     │
│            │  HighMemoryUsage            │                     │
│            │  MongoSlowQuery             │                     │
│            │  HighCPUUsage               │                     │
│            │  DiskSpaceLow               │                     │
│            └─────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────┐
│                   🚨 ALERTING LAYER                             │
├─────────────────────────────────────────────────────────────────┤
│                  📢 Alertmanager                                │
│                                                                 │
│  • Receives alerts from Prometheus                             │
│  • Groups & routes alerts                                      │
│  • Sends to webhook endpoints                                  │
│                                                                 │
│            ┌─────────────────────────────┐                     │
│            │    📤 Webhook Config        │                     │
│            │                             │                     │
│            │  url: http://p-dba-seed-    │                     │
│            │       adv-msk01:8080/       │                     │
│            │       alertmanager          │                     │
│            └─────────────────────────────┘                     │
└─────────────────────────────────────────────────────────────────┘
                               │
                               ▼ HTTP POST
                               
┌═════════════════════════════════════════════════════════════════┐
║                🌌 S.E.E.D. AGENT v6.1                          ║
║                Smart Event Explainer & Diagnostics             ║
╠═════════════════════════════════════════════════════════════════╣
║                                                                 ║
║  📥 INPUT LAYER                                                 ║
║  ┌─────────────────────┐    ┌─────────────────────┐            ║
║  │  HTTP Webhook       │    │   RabbitMQ          │            ║
║  │  :8080/alertmanager │    │   Consumer          │            ║
║  │  (Primary)          │    │   (Optional)        │            ║
║  └─────────────────────┘    └─────────────────────┘            ║
║           │                           │                        ║
║           └─────────────┬─────────────┘                        ║
║                         │                                      ║
║  🧭 ROUTING LAYER       ▼                                      ║
║  ┌─────────────────────────────────────────────────┐          ║
║  │              plugin_router.py                   │          ║
║  │                                                 │          ║
║  │  • Reads configs/alerts.yaml                   │          ║
║  │  • Maps alertname → plugin                     │          ║
║  │  • PostgresSlowQuery → pg_slow                 │          ║
║  │  • HighMemoryUsage → os_basic                  │          ║
║  │  • MongoSlowQuery → mongo_hot                  │          ║
║  │  • InstanceDown → host_inventory               │          ║
║  └─────────────────────────────────────────────────┘          ║
║                         │                                      ║
║  🔧 PROCESSING LAYER    ▼                                      ║
║  ┌─────────────────────────────────────────────────┐          ║
║  │                Plugin System                    │          ║
║  │  ┌─────────────┬─────────────┬─────────────┐   │          ║
║  │  │  🖥️ os_basic │ 🐘 pg_slow  │🍃 mongo_hot │   │          ║
║  │  │             │             │             │   │          ║
║  │  │ CPU/Mem/    │ Slow Query  │ Collection  │   │          ║
║  │  │ Disk/Load   │ Analysis    │ Scans       │   │          ║
║  │  └─────────────┴─────────────┴─────────────┘   │          ║
║  │  ┌─────────────┬─────────────────────────────┐ │          ║
║  │  │🌐host_inv   │     📢 echo (fallback)      │ │          ║
║  │  │             │                             │ │          ║
║  │  │ Network     │ Default handler             │ │          ║
║  │  │ Services    │                             │ │          ║
║  │  └─────────────┴─────────────────────────────┘ │          ║
║  └─────────────────────────────────────────────────┘          ║
║                         │                                      ║
║  💎 ENRICHMENT LAYER    ▼                                      ║
║  ┌─────────────────────────────────────────────────┐          ║
║  │                 enrich.py                       │          ║
║  │                                                 │          ║
║  │  📊 Prometheus Queries:                        │          ║
║  │  • node_cpu_seconds_total (CPU %)             │          ║
║  │  • node_memory_MemAvailable (Memory %)        │          ║
║  │  • node_load1 (Load Average)                  │          ║
║  │  • node_filesystem_* (Disk usage)             │          ║
║  │                                                │          ║
║  │  🔄 Telegraf Fallback:                        │          ║
║  │  • cpu_usage_idle (port 9216)                 │          ║
║  │  • mem_used_percent                           │          ║
║  │  • system_load1                               │          ║
║  └─────────────────────────────────────────────────┘          ║
║                         │                                      ║
║  🎮 STYLING LAYER       ▼                                      ║
║  ┌─────────────────────────────────────────────────┐          ║
║  │            Final Fantasy Emojis                 │          ║
║  │                                                 │          ║
║  │  ⚔️ CPU:  ✨→⚔️→🗡️→💎🔥 (0→50→70→90%+)        │          ║
║  │  🧙‍♂️ MEM:  🌟→🛡️→🏰→💎🔥 (low→mid→high→critical) │          ║
║  │  ⚙️ DISK: ✨→🛡️→⚔️→💎🔥 (good→warn→danger→critical) │    ║
║  └─────────────────────────────────────────────────┘          ║
║                         │                                      ║
║  🧠 AI LAYER            ▼                                      ║
║  ┌─────────────────────────────────────────────────┐          ║
║  │              GigaChat LLM                       │          ║
║  │                                                 │          ║
║  │  🧙‍♂️ "Магия кристалла":                        │          ║
║  │  • Context analysis                            │          ║
║  │  • Root cause suggestions                      │          ║
║  │  • Structured recommendations                  │          ║
║  │  • Pattern recognition                         │          ║
║  └─────────────────────────────────────────────────┘          ║
║                         │                                      ║
║  📝 FORMATTING LAYER    ▼                                      ║
║  ┌─────────────────────────────────────────────────┐          ║
║  │               fmt_batch_message()               │          ║
║  │                                                 │          ║
║  │  🌌 S.E.E.D. Header with ═ borders            │          ║
║  │  ⚔️ Alert with FF severity emojis              │          ║
║  │  📊 Summary: 🗡️ CPU~75% · 🏰 MEM~82% · ⚖️ Load │        ║
║  │  🔧 Plugin diagnostics (NO metric duplication) │         ║
║  │  🧠 AI analysis with clean formatting          │          ║
║  └─────────────────────────────────────────────────┘          ║
╚═════════════════════════════════════════════════════════════════╝
                               │
                               ▼ HTTP POST
┌─────────────────────────────────────────────────────────────────┐
│                    💬 DELIVERY LAYER                            │
├─────────────────────────────────────────────────────────────────┤
│                   📱 Mattermost                                 │
│                                                                 │
│  Channel: #alerts-seed                                          │
│                                                                 │
│  📨 Final Message Format:                                       │
│  ┌─────────────────────────────────────────────────┐          │
│  │ 🌌 S.E.E.D. - Smart Event Explainer & Diagnostics│         │
│  │ ═══════════════════════════════════════════════│         │
│  │                                                │         │
│  │ 💎🔥 PostgresSlowQuery 🔴                      │         │
│  │ └── Host: prod-db01 | Severity: CRITICAL      │         │
│  │ └── 📊 🗡️ CPU~75% · 🏰 MEM~82% · ⚖️ Load:8.45 │         │
│  │                                                │         │
│  │ 🔧 Детальная диагностика:                     │         │
│  │ PostgreSQL Analysis - main_db @ prod-db01     │         │
│  │ • 45 connections, 120 queries/sec             │         │
│  │ • Slow query analysis commands                │         │
│  │                                                │         │
│  │ 🧠 Магия кристалла:                           │         │
│  │ **Диагностика:** Высокая нагрузка БД...       │         │
│  │ **Рекомендации:** Создать индексы, VACUUM...   │         │
│  └─────────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────────┘

## 🔄 Data Flow Summary

1. **📊 Metrics Collection**: 
   - node_exporter, telegraf, db_exporters → Prometheus

2. **🚨 Alert Generation**: 
   - Prometheus evaluates rules → fires alerts → Alertmanager

3. **📤 Alert Routing**: 
   - Alertmanager → HTTP webhook → SEED Agent :8080/alertmanager

4. **🧭 Alert Processing**:
   - plugin_router maps alert → specialized plugin (pg_slow, os_basic, etc.)

5. **💎 Data Enrichment**:
   - enrich.py queries Prometheus for current metrics
   - Final Fantasy emojis applied based on values
   - Telegraf fallback if node_exporter unavailable

6. **🧠 AI Analysis**:
   - GigaChat LLM provides contextual recommendations
   - Formatted as structured "Диагностика" + "Рекомендации"

7. **📱 Final Delivery**:
   - Beautiful formatted message → Mattermost channel
   - Single summary line with all metrics (no duplication)
   - Plugin-specific diagnostics + AI insights

## ⚡ Key Features v6.1

- **🎮 Final Fantasy Style**: Epic emojis progression for all metrics
- **📊 No Duplication**: All metrics in single summary line at top
- **🔄 Fallback Ready**: Works with node_exporter OR telegraf
- **🧠 Smart AI**: Structured LLM diagnostics with clean formatting
- **⚔️ Plugin System**: Specialized handlers for different alert types
- **🌟 One Process**: All functionality in single lightweight agent