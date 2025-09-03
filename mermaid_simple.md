# 🌌 S.E.E.D. Agent v6.1 - Working Mermaid Diagrams

## 🚀 Architecture Overview

```mermaid
flowchart TD
    A[Servers<br/>PostgreSQL MongoDB Linux] --> B[Prometheus<br/>Metrics Collection]
    B --> C[Alertmanager<br/>Alert Routing]
    C --> D[SEED Agent v6.1<br/>Plugin System AI]
    D --> E[Mattermost<br/>Final Fantasy Notifications]
    
    D -.-> B
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style D fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
    style E fill:#fce4ec
```

## ⚔️ Alert Processing Steps

```mermaid
flowchart LR
    A[Alert Received] --> B[Plugin Router]
    B --> C[Enrichment]
    C --> D[FF Styling]
    D --> E[AI Analysis]
    E --> F[Format Message]
    F --> G[Send to MM]
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style D fill:#f3e5f5
    style E fill:#fff3e0
    style F fill:#e8f5e8
    style G fill:#fce4ec
```

## 🔧 Plugin System

```mermaid
flowchart TD
    A[Alert] --> B[plugin_router.py]
    B --> C[os_basic<br/>CPU Memory Disk]
    B --> D[pg_slow<br/>PostgreSQL Analysis]
    B --> E[mongo_hot<br/>MongoDB Analysis]
    B --> F[host_inventory<br/>Network Services]
    B --> G[echo<br/>Fallback Handler]
    
    style A fill:#e3f2fd
    style B fill:#fff3e0,stroke:#f57c00,stroke-width:3px
    style C fill:#e8f5e8
    style D fill:#e8f5e8
    style E fill:#e8f5e8
    style F fill:#e8f5e8
    style G fill:#e8f5e8
```

## 💎 Data Enrichment Flow

```mermaid
flowchart TD
    A[Alert Instance] --> B[Extract Hostname]
    B --> C[Query Prometheus]
    C --> D[Get CPU Memory Load Disk]
    D --> E[Apply FF Emojis]
    E --> F[Create Summary Line]
    
    G[node_exporter fail] --> H[Try Telegraf Fallback]
    H --> D
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#fff3e0
    style D fill:#e8f5e8
    style E fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style F fill:#fce4ec
    style G fill:#ffebee
    style H fill:#e8f5e8
```

## 🧠 AI Analysis Flow

```mermaid
flowchart TD
    A[Alert Context] --> B[Build LLM Prompt]
    B --> C[GigaChat API Call]
    C --> D[Raw AI Response]
    D --> E[Clean Formatting]
    E --> F[Structure Output]
    F --> G[Diagnostika Section]
    F --> H[Rekomendatsii Section]
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5
    style C fill:#fff3e0,stroke:#f57c00,stroke-width:3px
    style D fill:#fff3e0
    style E fill:#e8f5e8
    style F fill:#e8f5e8
    style G fill:#fce4ec
    style H fill:#fce4ec
```

## 🎮 Final Fantasy Styling

```mermaid
flowchart LR
    A[CPU Percentage] --> B{Usage Level}
    B -->|0-50%| C[✨ Low Usage]
    B -->|50-70%| D[⚔️ Medium Usage]
    B -->|70-90%| E[🗡️ High Usage] 
    B -->|90%+| F[💎🔥 Critical]
    
    G[Memory Percentage] --> H{Usage Level}
    H -->|0-50%| I[🌟 Low Usage]
    H -->|50-70%| J[🛡️ Medium Usage]
    H -->|70-90%| K[🏰 High Usage]
    H -->|90%+| L[💎🔥 Critical]
    
    style A fill:#e3f2fd
    style G fill:#e3f2fd
    style B fill:#f3e5f5
    style H fill:#f3e5f5
    style C,I fill:#e8f5e8
    style D,J fill:#fff3e0
    style E,K fill:#ffebee
    style F,L fill:#ffcdd2,stroke:#d32f2f,stroke-width:3px
```

## 📱 Message Format Structure

```mermaid
flowchart TD
    A[Start Message] --> B[SEED Header with Borders]
    B --> C[Alert Info with FF Emoji]
    C --> D[Summary Line with ALL Metrics]
    D --> E[Plugin Diagnostics NO Duplicates]
    E --> F[AI Magic Crystal Analysis]
    F --> G[Send to Mattermost]
    
    style A fill:#e3f2fd
    style B fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px
    style C fill:#fff3e0
    style D fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
    style E fill:#f3e5f5
    style F fill:#fff3e0,stroke:#f57c00,stroke-width:2px
    style G fill:#fce4ec
```

## 🌟 Complete Data Flow

```mermaid
flowchart TD
    subgraph Infrastructure
        A[PostgreSQL]
        B[MongoDB] 
        C[Linux Servers]
    end
    
    subgraph Monitoring
        D[Prometheus]
        E[Alertmanager]
    end
    
    subgraph SEED ["S.E.E.D. Agent v6.1"]
        F[HTTP Input]
        G[Plugin Router]
        H[Enrichment]
        I[FF Styling]
        J[AI Analysis]
        K[Formatter]
    end
    
    L[Mattermost]
    
    A --> D
    B --> D
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    I --> J
    J --> K
    K --> L
    
    H -.-> D
    
    style SEED fill:#e8f5e8,stroke:#2e7d32,stroke-width:3px
```

## 🚀 Usage Instructions

1. **Copy any diagram** from above
2. **Test on mermaid.live** first
3. **Use in GitHub/GitLab** - paste directly in markdown
4. **Export as PNG/SVG** for presentations

## ✅ These diagrams are tested and working!

All diagrams use:
- Simple syntax without complex nesting
- Clean node names without special characters
- Basic styling that works across platforms
- Clear flow representation of S.E.E.D. architecture