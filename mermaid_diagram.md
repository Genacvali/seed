# 🌌 S.E.E.D. Agent v6.1 - Mermaid Architecture Diagram

## 🚀 Simple Overview (WORKING)

```mermaid
flowchart TD
    A["Servers<br/>Server, DB, Linux"] --> B["Prometheus<br/>Metrics Collection"]
    B --> C["Alertmanager<br/>Alert Routing"]
    
    %% Two input channels to SEED
    C -->|"HTTP Webhook<br/>:8080/alertmanager"| D["SEED Agent v6.1<br/>Plugin System + AI"]
    F["RabbitMQ<br/>Message Queue"] -->|"AMQP Consumer<br/>Optional"| D
    
    D --> E["Mattermost<br/>FF-styled notifications"]
    
    %% SEED queries Prometheus for current metrics to enrich alerts
    D -.->|"GET current CPU/MEM/Disk<br/>"| B
    
    classDef server fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef monitor fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px  
    classDef seed fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
    classDef output fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef rabbit fill:#ffebee,stroke:#d32f2f,stroke-width:2px
    
    class A server
    class B,C monitor
    class D seed
    class E output
    class F rabbit
```

## ⚔️ Alert Processing Flow (WORKING)

```mermaid
flowchart LR
    A["Alert Received<br/>PostgresSlowQuery"] --> B["Plugin Router<br/>Route to pg_slow"]
    B --> C["Enrichment<br/>Query Prometheus<br/>for current metrics"]
    C --> D["Final Fantasy Styling<br/>Apply CPU/MEM/DISK emojis"]
    D --> E["AI Analysis<br/>GigaChat recommendations"]
    E --> F["Format Message<br/>Beautiful output"]
    F --> G["Send to Mattermost<br/>Channel notification"]
    
    classDef process fill:#e3f2fd,stroke:#1976d2,stroke-width:2px
    classDef styling fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    classDef ai fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    classDef output fill:#e8f5e8,stroke:#2e7d32,stroke-width:2px
    
    class A,B,C process
    class D styling
    class E ai
    class F,G output
```

## 🎮 Plugin System Detail

```mermaid
flowchart TD
    A["Alert Received"] --> B["plugin_router.py"]
    
    B --> C["os_basic<br/>CPU/Memory/Disk analysis"]
    B --> D["pg_slow<br/>PostgreSQL diagnostics"]  
    B --> E["mongo_hot<br/>MongoDB analysis"]
    B --> F["host_inventory<br/>Network services"]
    B --> G["echo<br/>Default fallback"]
    
    H["configs/alerts.yaml<br/>Routing Rules"] --> B
    
    style A fill:#e3f2fd
    style B fill:#fff3e0,stroke:#f57c00,stroke-width:3px
    style C fill:#e8f5e8
    style D fill:#e8f5e8  
    style E fill:#e8f5e8
    style F fill:#e8f5e8
    style G fill:#e8f5e8
    style H fill:#f3e5f5
```

## 💎 Enrichment Process

```mermaid
flowchart TD
    A["Alert: instance=prod-db01"] --> B["Extract hostname"]
    B --> C["Query Prometheus API"]
    C --> D["Get CPU/Memory/Load/Disk"]
    D --> E["Apply Final Fantasy emojis"]
    E --> F["Create summary line"]
    
    G["node_exporter unavailable"] --> H["Try Telegraf fallback"]
    H --> D
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style D fill:#e8f5e8
    style E fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style F fill:#fce4ec
    style G fill:#ffebee
    style H fill:#e8f5e8
```

## 🚀 Usage Instructions

1. Copy any of the diagrams above
2. Paste into GitHub README.md, GitLab, or any Mermaid-supported platform
3. The diagrams will render automatically
4. For presentations, use mermaid.live or mermaid-js.github.io to export as PNG/SVG

## 🎮 Features Highlighted

- **🌌 S.E.E.D. Agent** as central processing hub
- **🎮 Final Fantasy styling** with emoji progressions  
- **🔧 Plugin system** with specialized handlers
- **💎 Smart enrichment** with Prometheus integration
- **🧠 AI analysis** via GigaChat LLM
- **📱 Beautiful output** to Mattermost