#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEED v6 – лёгкий HTTP агент:
 - /health           — проверка живости
 - /test (POST)      — быстрая проверка доставки
 - /alertmanager     — вебхук Alertmanager (принимает batch alerts)
 - Опционально: RabbitMQ consumer (JSON-сообщения с алертами)
 - Опционально: Mattermost нотификации и LLM (GigaChat)

Логи пишем в stdout — start.sh уже перенаправляет их в logs/agent.log.
"""

import os, json, time, threading, signal, sys
from typing import Any, Dict, List, Optional

import yaml
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from core.config import CFG
from core.mm import post_to_mm
from core.llm import GigaChat

# Prometheus enrichment (опционально)
try:
    from enrich import enrich_alert
    ENRICHMENT_AVAILABLE = True
except Exception:
    ENRICHMENT_AVAILABLE = False
    def enrich_alert(alert): return {}

# Plugin system
try:
    from plugin_router import plugin_router
    PLUGINS_AVAILABLE = True
except Exception as e:
    print(f"[PLUGIN] Failed to load plugin system: {e}")
    PLUGINS_AVAILABLE = False
    plugin_router = None

# Prometheus client for plugins
try:
    import prom
    PROM_CLIENT_AVAILABLE = True
except Exception:
    PROM_CLIENT_AVAILABLE = False
    prom = None

# ---------------------------
# Загрузка ENV из configs/seed.env
# ---------------------------
if getattr(sys, "frozen", False):
    # Запущено из собранного бинарника (PyInstaller onefile) —
    # считаем рабочей директорией папку рядом с бинарём.
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Обычный режим разработки — рядом с исходниками.
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ENV_PATH = os.path.join(BASE_DIR, "configs", "seed.env")
# .env уже загружен в core/config.py до всех импортов — повторно не нужно.

# ---------------------------
# Конфигурация (через core.config.CFG)
# ---------------------------
LISTEN_HOST = CFG.listen_host
LISTEN_PORT = CFG.listen_port

MM_WEBHOOK = CFG.mm_webhook
USE_LLM = CFG.use_llm

# Rabbit
RABBIT_ENABLE = CFG.rabbit_enabled
RABBIT_HOST = CFG.rabbit_host
RABBIT_PORT = CFG.rabbit_port
RABBIT_SSL = CFG.rabbit_ssl
RABBIT_USER = CFG.rabbit_user
RABBIT_PASS = CFG.rabbit_pass
RABBIT_VHOST = CFG.rabbit_vhost
RABBIT_QUEUE = CFG.rabbit_queue

# ─── Динамическое чтение конфига ─────────────────────────────────────────────
# Все функции читают значения через эти геттеры, а не через глобальные переменные,
# чтобы изменения в seed.env применялись сразу (без перезапуска агента).

def _use_llm() -> bool:
    return os.getenv("USE_LLM", "0") in ("1", "true", "True")

def _dry_run() -> bool:
    return os.getenv("DRY_RUN", "0") in ("1", "true", "True")

def _mm_webhook() -> str:
    return os.getenv("MM_WEBHOOK", "")

def _prom_url() -> str:
    return os.getenv("PROM_URL", "")

def _throttle_enable() -> bool:
    return os.getenv("ALERT_THROTTLE_ENABLE", "1") not in ("0", "false", "False")

def _throttle_window() -> int:
    return int(os.getenv("ALERT_THROTTLE_WINDOW_SEC", "") or "60")

def _throttle_max() -> int:
    return int(os.getenv("ALERT_THROTTLE_MAX_PER_WINDOW", "") or "3")

# Статические значения, которые реально нужны только при старте (порт, очередь и т.п.)
PROM_VERIFY_SSL = os.getenv("PROM_VERIFY_SSL", "1") not in ("0", "false", "False")
PROM_TIMEOUT    = os.getenv("PROM_TIMEOUT", "3")
PROM_BEARER     = os.getenv("PROM_BEARER", "")

# Обратная совместимость: оставляем переменные как свойства-ссылки на геттеры.
# Прямое обращение к USE_LLM/DRY_RUN осталось лишь в нескольких местах ниже —
# все они заменены на вызовы геттеров.
PROM_URL = _prom_url()   # используется только в проверке ENRICHMENT

def clean_llm_response(text: str) -> str:
    """Очищает LLM ответ от блоков кода и форматирует для Mattermost"""
    import re
    
    # Убираем блоки кода ```sql, ```bash и т.д.
    text = re.sub(r'```\w*\n.*?\n```', '', text, flags=re.DOTALL)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Убираем лишние ключевые слова
    text = re.sub(r'\b(sql|bash|plpgsql)\b', '', text, flags=re.IGNORECASE)
    
    # Нормализуем пробелы (но сохраняем структуру предложений)
    text = re.sub(r'\s+', ' ', text)
    text = text.strip()
    
    # Первично обрабатываем ключевые фразы и разделители
    # Находим секции "Диагностика:" и "Шаги решения:" или "Рекомендации:"
    text = re.sub(r'([.!?])\s*(Диагностика|Рекомендации|Шаги\s+(?:для\s+)?решения):\s*', r'\1\n\n**\2:**\n\n• ', text, flags=re.IGNORECASE)
    text = re.sub(r'^(Диагностика|Рекомендации|Шаги\s+(?:для\s+)?решения):\s*', r'**\1:**\n\n• ', text, flags=re.IGNORECASE)
    
    # Обрабатываем нумерацию внутри текста 
    # "1. Проверьте" -> "• Проверьте"
    text = re.sub(r'([.!?]\s+)(\d+\.)\s+', r'\1\n• ', text)
    text = re.sub(r'(\.\s+)(\d+\.)\s+', r'.\n• ', text)
    text = re.sub(r'(^|\n)\s*(\d+\.)\s+', r'\1• ', text, flags=re.MULTILINE)
    
    # Убираем лишние нумерации в начале пунктов после обработки
    text = re.sub(r'•\s*\d+\.\s*', '• ', text)
    
    # Разделяем предложения, которые слиплись
    # "память. Шаги решения:" -> "память.\n\n**Шаги решения:**"
    text = re.sub(r'([а-я])\.\s+(Шаги\s+(?:для\s+)?решения|Рекомендации):', r'\1.\n\n**\2:**\n\n• ', text, flags=re.IGNORECASE)
    
    # Обрабатываем подпункты с двоеточием
    text = re.sub(r'([.!?])\s*([А-Я][а-я\s]+[а-я]):\s*([А-Я])', r'\1\n\n• **\2:**\n  \3', text)
    
    # Разделяем длинные абзацы по логическим границам
    text = re.sub(r'([а-я])\.\s+([А-Я][а-я]+[а-я]\s+[а-я]+)', r'\1.\n• \2', text)
    
    # Разбиваем очень длинные строки (более 120 символов) по смыслу
    lines = []
    for line in text.split('\n'):
        line = line.strip()
        if len(line) > 120 and not line.startswith('•'):
            # Пытаемся разбить по запятым или точкам с запятой
            parts = re.split(r'([,;])\s*(?=[А-Я])', line)
            current_line = ''
            for i in range(0, len(parts), 2):
                part = parts[i]
                if i + 1 < len(parts):
                    part += parts[i + 1]  # добавляем запятую/точку с запятой
                
                if len(current_line + part) > 100 and current_line:
                    lines.append(current_line.strip())
                    current_line = '• ' + part.strip() if not part.strip().startswith('•') else part.strip()
                else:
                    current_line += part
            
            if current_line.strip():
                lines.append(current_line.strip())
        else:
            lines.append(line)
    
    # Убираем пустые строки и лишние маркеры
    result_lines = []
    for line in lines:
        line = line.strip()
        if line and line != '•' and line != '**:**':
            result_lines.append(line)
    
    return '\n'.join(result_lines).strip()

def send_alert_message(text: str, color: Optional[str]) -> bool:
    """Обертка над отправкой в Mattermost с поддержкой DRY_RUN."""
    if _dry_run():
        print("[DRY_RUN] Message NOT sent to Mattermost. Preview below:")
        print(text[:500])
        return True
    return post_to_mm(text, color)

def llm_tip(prompt: str, max_tokens: int = 400) -> Optional[str]:
    """Обертка над core.llm.GigaChat с форматированием ответа под Mattermost."""
    if not _use_llm():
        print("[LLM] disabled (USE_LLM=0)")
        return None

    print(f"[LLM] requesting tip for prompt: {prompt[:100]}...")

    try:
        client = GigaChat()
    except Exception as e:
        print(f"[LLM] init error: {e}")
        return None

    try:
        raw = client.ask(prompt.strip(), max_tokens=max_tokens)
        if not isinstance(raw, str) or not raw.strip():
            print("[LLM] empty response")
            return None

        result = clean_llm_response(raw.strip())
        print(f"[LLM] success: {result[:100]}...")
        return result
    except Exception as e:
        print(f"[LLM] chat EXC: {e}")
        return None

# ---------------------------
# Форматирование алертов (Final Fantasy style)
# ---------------------------
def get_severity_emoji(severity: str) -> str:
    """Возвращает эмодзи и цвет для уровня критичности"""
    sev_map = {
        "critical": "💎🔥",  # Critical - красный кристалл с огнем
        "high": "⚔️",       # High - меч  
        "warning": "🛡️",    # Warning - щит
        "info": "✨",       # Info - звездочка
        "low": "🌟"         # Low - обычная звезда
    }
    return sev_map.get(severity.lower(), "❔")

def get_mattermost_color(severity: str) -> str:
    """Возвращает цвет для Mattermost attachment"""
    color_map = {
        "critical": "#FF0000",  # Красный
        "high": "#FF8C00",      # Оранжевый  
        "warning": "#FFD700",   # Желтый
        "info": "#00BFFF",      # Синий
        "low": "#90EE90"        # Светло-зеленый
    }
    return color_map.get(severity.lower(), "#808080")

def fmt_alert_line(alert: Dict[str, Any], enriched: Dict[str, Any] = None, count: int = 1) -> str:
    labels = alert.get("labels", {})
    ann = alert.get("annotations", {})
    status = alert.get("status", "firing")
    name = labels.get("alertname", "Alert")
    inst = labels.get("instance") or labels.get("pod") or labels.get("job") or "-"
    sev = labels.get("severity", "info")
    summary = ann.get("summary") or ann.get("description") or ""
    
    # FF-style иконки  
    emoji = get_severity_emoji(sev)
    # Цвет статуса зависит от severity, а не только от firing/resolved
    if status == "resolved":
        status_icon = "🟢"  # resolved всегда зеленый
    else:
        # firing - цвет по severity
        severity_icons = {
            "critical": "🔴", # красный
            "high": "🟠",     # оранжевый  
            "warning": "🟡",  # желтый
            "info": "🔵",     # синий
            "low": "🟢"       # зеленый
        }
        status_icon = severity_icons.get(sev.lower(), "🔴")
    
    # Компактный FF-стиль с обогащенными данными
    suffix = f" ×{count}" if count and count > 1 else ""
    lines = [
        f"{emoji} **{name}**{suffix} {status_icon}",
        f"└── Host: `{inst}` | Severity: **{sev.upper()}**"
    ]
    
    # Добавляем enriched контекст если есть
    if enriched and enriched.get("summary_line"):
        lines.append(f"└── 📊 {enriched['summary_line']}")
    
    lines.append(f"└── {summary}")
    
    return "\n".join(lines)

_alert_throttle_state: Dict[str, Dict[str, Any]] = {}

def _make_alert_key(alert: Dict[str, Any]) -> str:
    labels = alert.get("labels", {}) or {}
    name = labels.get("alertname", "")
    inst = labels.get("instance") or labels.get("pod") or labels.get("job") or ""
    sev = labels.get("severity", "")
    status = alert.get("status", "firing")
    return f"{name}|{inst}|{sev}|{status}"

def fmt_batch_message(alerts: List[Dict[str, Any]]) -> tuple:
    """Возвращает (текст_сообщения, цвет_для_mattermost) с простым dedup/throttling."""
    if not alerts:
        return "🌌 **SEED Crystal** - No alerts detected", None

    # FF-style заголовок
    head = "🌌 **S.E.E.D.** - Smart Event Explainer & Diagnostics\n" + "═" * 55

    # Группируем одинаковые алерты (по alertname+instance+severity+status)
    grouped: Dict[str, Dict[str, Any]] = {}
    for a in alerts:
        key = _make_alert_key(a)
        g = grouped.setdefault(key, {"alert": a, "count": 0})
        g["count"] += 1

    lines: List[str] = []
    severities: List[str] = []
    llm_context: List[str] = []
    plugin_results: List[Dict[str, Any]] = []
    throttled_keys: List[str] = []

    now = time.time()

    for key, info in grouped.items():
        a = info["alert"]
        count = info["count"]

        # Простое throttling по ключу
        if _throttle_enable():
            st = _alert_throttle_state.get(key)
            if not st or now - st.get("first_ts", 0) > _throttle_window():
                st = {"first_ts": now, "count": 0}
            st["count"] += count
            _alert_throttle_state[key] = st
            if st["count"] > _throttle_max():
                throttled_keys.append(key)
                continue

        # Обогащаем алерт данными из Prometheus
        enriched: Dict[str, Any] = {}
        if ENRICHMENT_AVAILABLE and _prom_url():
            try:
                enriched = enrich_alert(a)
                print(f"[ENRICH] {a.get('labels', {}).get('alertname', 'Alert')}: {enriched.get('summary_line', 'no data')}")
            except Exception as e:
                print(f"[ENRICH] failed: {e}")

        # Запускаем плагин для алерта
        plugin_result: Optional[Dict[str, Any]] = None
        if PLUGINS_AVAILABLE and plugin_router and PROM_CLIENT_AVAILABLE and prom:
            try:
                plugin_result = plugin_router.run_plugin(a, prom)
                if plugin_result:
                    plugin_results.append(plugin_result)
            except Exception as e:
                print(f"[PLUGIN] Error processing alert: {e}")

        lines.append(fmt_alert_line(a, enriched, count=count))
        severities.append(a.get("labels", {}).get("severity", "info"))

        # Создаем более богатый контекст для LLM
        labels = a.get("labels", {})
        ann = a.get("annotations", {})
        alert_context = f"{labels.get('alertname', 'Alert')} (x{count}): {ann.get('summary', '')}" if count > 1 else f"{labels.get('alertname', 'Alert')}: {ann.get('summary', '')}"

        # Добавляем метрики в контекст для LLM
        if enriched.get("summary_line"):
            alert_context += f" | Метрики: {enriched['summary_line']}"

        # Добавляем результаты плагина в контекст LLM
        if plugin_result and plugin_result.get("lines"):
            plugin_summary = "; ".join(plugin_result["lines"][:3])  # Первые 3 строки
            alert_context += f" | Плагин: {plugin_summary}"

        llm_context.append(alert_context)

    text = head
    if lines:
        text += "\n\n" + "\n\n".join(lines)
    
    # Краткая статистика
    if len(alerts) > 1:
        sev_counts = {}
        for s in severities:
            sev_counts[s] = sev_counts.get(s, 0) + 1
        stats = " | ".join([f"{get_severity_emoji(s)} {s}:{c}" for s, c in sev_counts.items()])
        text += f"\n\n📊 **Summary:** {stats}"

    # Информация о throttling (если что-то было подавлено)
    if throttled_keys:
        text += f"\n\n⏱ **Throttling:** suppressed {len(throttled_keys)} alert group(s) in the last {_throttle_window()}s"
    
    # Результаты плагинов (детальная диагностика)
    if plugin_results:
        text += f"\n\n🔧 **Детальная диагностика:**"
        for result in plugin_results[:2]:  # Максимум 2 плагина, чтобы не перегружать
            if result.get("title") and result.get("lines"):
                text += f"\n\n**{result['title']}**\n"
                # Ограничиваем количество строк от плагина
                plugin_lines = result["lines"][:8]  # Максимум 8 строк
                text += "\n".join(plugin_lines)
    
    # LLM рекомендация с обогащенным контекстом
    if _use_llm() and len(alerts) > 0:
        # Используем обогащенный контекст для более точных рекомендаций
        context_str = "; ".join(llm_context[:3])  # Первые 3 алерта
        prompt = f"Алерты мониторинга с метриками: {context_str}. Дай подробную диагностику и 3-4 конкретных шага решения проблемы."
        tip = llm_tip(prompt, max_tokens=400)
        if tip:
            text += f"\n\n🧠 **Магия кристалла:** {tip}"
    
    # Определяем цвет по наивысшей критичности
    priority = ["critical", "high", "warning", "info", "low"]
    highest_sev = "info"
    for sev in priority:
        if sev in severities:
            highest_sev = sev
            break
    
    color = get_mattermost_color(highest_sev)
    return text, color

# ---------------------------
# FastAPI приложение
# ---------------------------
app = FastAPI(title="SEED v6 Agent")

@app.get("/health")
async def health():
    health_info = {
        "status": "ok",
        "mm_webhook": bool(_mm_webhook()),
        "use_llm": _use_llm(),
        "rabbit_enabled": RABBIT_ENABLE,
        "prometheus_enrichment": ENRICHMENT_AVAILABLE and bool(_prom_url()),
        "prometheus_url": _prom_url() or None,
        "dry_run": _dry_run(),
        "version": "v6.2",
    }
    
    # Добавляем информацию о плагинах
    if PLUGINS_AVAILABLE and plugin_router:
        try:
            plugin_info = plugin_router.get_plugin_info()
            health_info.update({
                "plugins_enabled": True,
                "plugin_routes": plugin_info.get("routes_count", 0),
                "default_plugin": plugin_info.get("default_plugin", "unknown"),
                "available_plugins": plugin_info.get("available_plugins", [])
            })
        except Exception as e:
            health_info["plugins_enabled"] = False
            health_info["plugin_error"] = str(e)
    else:
        health_info["plugins_enabled"] = False
    
    return health_info

@app.post("/test")
async def test_endpoint(req: Request):
    try:
        body = await req.json()
    except Exception:
        body = {}
    # Синтетический alertmanager-пакет
    pkg = {
        "alerts": [
            {
                "status": "firing",
                "labels": {
                    "alertname": body.get("alertname", "SeedTest"),
                    "instance":  body.get("instance",  os.uname().nodename),
                    "severity":  body.get("severity",  "warning")
                },
                "annotations": {
                    "summary": body.get("summary", "Test alert from SEED v6")
                }
            }
        ]
    }
    text, color = fmt_batch_message(pkg["alerts"])
    ok = send_alert_message(text, color)
    return {"ok": ok, "sent_text": text}

@app.post("/alertmanager")
async def alertmanager_webhook(req: Request):
    try:
        payload = await req.json()
    except Exception:
        return JSONResponse({"error": "invalid json"}, status_code=400)

    alerts = payload.get("alerts")
    if not isinstance(alerts, list):
        return JSONResponse({"error": "no alerts[]"}, status_code=400)

    text, color = fmt_batch_message(alerts)
    ok = send_alert_message(text, color)
    return {"ok": ok}

# ---------------------------
# Admin panel: статика + API
# ---------------------------
STATIC_DIR = os.path.join(BASE_DIR, "static")
ALERTS_YAML = os.path.join(BASE_DIR, "configs", "alerts.yaml")

# Отдаём /static/* (иконки, css и т.п.)
if os.path.isdir(STATIC_DIR):
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

@app.get("/admin")
async def admin_page():
    html_path = os.path.join(STATIC_DIR, "admin.html")
    if os.path.exists(html_path):
        return FileResponse(html_path, media_type="text/html")
    return HTMLResponse("<h1>admin.html not found</h1>", status_code=404)

@app.get("/")
async def index():
    """Главная страница — просто отдаём админ‑панель."""
    return await admin_page()

@app.get("/admin/env")
async def admin_get_env():
    """Вернуть текущие ключи из configs/seed.env (без секретов полностью)."""
    data: Dict[str, str] = {}
    if os.path.exists(ENV_PATH):
        with open(ENV_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    k, v = line.split("=", 1)
                    data[k.strip()] = v.strip()
    return data

@app.put("/admin/env")
async def admin_put_env(req: Request):
    """Записать seed.env и сразу применить переменные в os.environ (hot-reload)."""
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, 400)

    lines: List[str] = []
    for k, v in body.items():
        lines.append(f"{k}={v}")

    try:
        os.makedirs(os.path.dirname(ENV_PATH), exist_ok=True)
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")

        # Применяем новые значения сразу в текущий процесс
        for k, v in body.items():
            os.environ[k] = str(v)

        print("[ADMIN] Config reloaded from admin panel (hot-reload)")
        return {"ok": True, "note": "Applied immediately — no restart needed"}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 500)

@app.get("/admin/routes")
async def admin_get_routes():
    """Вернуть текущие маршруты из alerts.yaml + список доступных плагинов."""
    data: Dict[str, Any] = {"routes": [], "default_plugin": "echo", "available_plugins": []}
    if os.path.exists(ALERTS_YAML):
        with open(ALERTS_YAML, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
        data["routes"] = cfg.get("routes", [])
        data["default_plugin"] = cfg.get("default_plugin", "echo")

    plugins_dir = os.path.join(BASE_DIR, "plugins")
    if os.path.isdir(plugins_dir):
        data["available_plugins"] = sorted(
            f.replace(".py", "")
            for f in os.listdir(plugins_dir)
            if f.endswith(".py") and f != "__init__.py"
        )
    return data

@app.put("/admin/routes")
async def admin_put_routes(req: Request):
    """Сохранить маршруты в alerts.yaml и горячий релоад."""
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, 400)

    cfg = {
        "routes": body.get("routes", []),
        "default_plugin": body.get("default_plugin", "echo"),
        "default_params": body.get("default_params", {"show_basic_info": True}),
    }
    try:
        os.makedirs(os.path.dirname(ALERTS_YAML), exist_ok=True)
        with open(ALERTS_YAML, "w", encoding="utf-8") as f:
            yaml.dump(cfg, f, default_flow_style=False, allow_unicode=True, sort_keys=False)

        if PLUGINS_AVAILABLE and plugin_router:
            plugin_router.load_config()
            print("[ADMIN] Routes reloaded")

        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 500)

PLUGINS_DIR = os.path.join(BASE_DIR, "plugins")

PLUGIN_TEMPLATE = '''\
# -*- coding: utf-8 -*-
"""
Plugin: {name}

Как подключить — добавить в configs/alerts.yaml:
  - match: {{alertname: "YourAlert"}}
    plugin: "{name}"
    params: {{}}
"""

def run(alert: dict, prom, params: dict) -> dict:
    labels = alert.get("labels", {{}})
    annotations = alert.get("annotations", {{}})
    instance = labels.get("instance", "unknown")
    alertname = labels.get("alertname", "Alert")

    lines = []

    # ── Ваша логика ────────────────────────────────────
    # Запрос к Prometheus:
    #   val = prom.query_value(\'some_metric{{instance="%s"}}\' % instance)
    #   if isinstance(val, (int, float)):
    #       lines.append(f"Metric: {{val:.1f}}")
    # ───────────────────────────────────────────────────

    return {{
        "title": f"{{alertname}} @ {{instance}}",
        "lines": lines,
    }}
'''

@app.get("/admin/plugins")
async def admin_list_plugins():
    """Список плагинов в plugins/ с размером и датой изменения."""
    os.makedirs(PLUGINS_DIR, exist_ok=True)
    result = []
    for fname in sorted(os.listdir(PLUGINS_DIR)):
        if not fname.endswith(".py") or fname.startswith("_"):
            continue
        fpath = os.path.join(PLUGINS_DIR, fname)
        stat = os.stat(fpath)
        result.append({
            "name": fname.replace(".py", ""),
            "file": fname,
            "size": stat.st_size,
            "mtime": int(stat.st_mtime),
        })
    return {"plugins": result}

@app.get("/admin/plugins/{name}")
async def admin_get_plugin(name: str):
    """Вернуть исходный код плагина."""
    fpath = os.path.join(PLUGINS_DIR, f"{name}.py")
    if not os.path.exists(fpath):
        return JSONResponse({"ok": False, "error": "not found"}, 404)
    with open(fpath, "r", encoding="utf-8") as f:
        code = f.read()
    return {"ok": True, "name": name, "code": code}

@app.put("/admin/plugins/{name}")
async def admin_put_plugin(name: str, req: Request):
    """Создать или обновить плагин (сохранить Python-код)."""
    try:
        body = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, 400)

    code = body.get("code", "")
    if not code.strip():
        return JSONResponse({"ok": False, "error": "empty code"}, 400)

    os.makedirs(PLUGINS_DIR, exist_ok=True)
    fpath = os.path.join(PLUGINS_DIR, f"{name}.py")
    try:
        with open(fpath, "w", encoding="utf-8") as f:
            f.write(code)
        # Сбросить кэш плагина в роутере, чтобы следующий вызов перезагрузил его
        if PLUGINS_AVAILABLE and plugin_router and name in plugin_router.plugins_cache:
            del plugin_router.plugins_cache[name]
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 500)

@app.delete("/admin/plugins/{name}")
async def admin_delete_plugin(name: str):
    """Удалить плагин."""
    fpath = os.path.join(PLUGINS_DIR, f"{name}.py")
    if not os.path.exists(fpath):
        return JSONResponse({"ok": False, "error": "not found"}, 404)
    try:
        os.remove(fpath)
        if PLUGINS_AVAILABLE and plugin_router and name in plugin_router.plugins_cache:
            del plugin_router.plugins_cache[name]
        return {"ok": True}
    except Exception as e:
        return JSONResponse({"ok": False, "error": str(e)}, 500)

@app.get("/admin/plugin_template/{name}")
async def admin_plugin_template(name: str):
    """Вернуть шаблон нового плагина с подставленным именем."""
    code = PLUGIN_TEMPLATE.format(name=name)
    return {"ok": True, "code": code}

@app.post("/admin/dry_run")
async def admin_dry_run(req: Request):
    """Прогнать пакет алертов через пайплайн без отправки в MM."""
    try:
        payload = await req.json()
    except Exception:
        return JSONResponse({"ok": False, "error": "invalid json"}, 400)

    alerts = payload.get("alerts")
    if not isinstance(alerts, list):
        alerts = [payload] if isinstance(payload, dict) else []

    text, color = fmt_batch_message(alerts)
    return {"ok": True, "preview": text, "color": color}

# ---------------------------
# RabbitMQ consumer (опционально)
# Ожидаем body — это либо alertmanager-пакет, либо один alert со схожими полями.
# ---------------------------
def rabbit_consume_loop():
    try:
        import pika
    except ImportError:
        print("[RABBIT] pika not installed, skipping consumer")
        return
        
    creds = pika.PlainCredentials(RABBIT_USER, RABBIT_PASS)
    if RABBIT_SSL:
        # SSL connection
        import pika.adapters.utils.connection_workflow
        ssl_options = pika.SSLOptions(context=None)
        params = pika.ConnectionParameters(
            host=RABBIT_HOST,
            port=RABBIT_PORT,
            virtual_host=RABBIT_VHOST,
            credentials=creds,
            ssl_options=ssl_options
        )
    else:
        # Regular connection
        params = pika.ConnectionParameters(
            host=RABBIT_HOST,
            port=RABBIT_PORT,
            virtual_host=RABBIT_VHOST,
            credentials=creds
        )
    while True:
        try:
            print(f"[*] Rabbit connect to {RABBIT_HOST}:{RABBIT_PORT} vhost={RABBIT_VHOST} q={RABBIT_QUEUE}")
            conn = pika.BlockingConnection(params)
            ch = conn.channel()
            ch.queue_declare(queue=RABBIT_QUEUE, durable=True)

            def on_msg(ch, method, props, body):
                try:
                    j = json.loads(body.decode("utf-8"))
                    if "alerts" in j and isinstance(j["alerts"], list):
                        text, color = fmt_batch_message(j["alerts"])
                    else:
                        # обернём одиночный в пакет
                        text, color = fmt_batch_message([j])
                    send_alert_message(text, color)
                except Exception as e:
                    print(f"[RABBIT] msg err: {e}")
                finally:
                    ch.basic_ack(delivery_tag=method.delivery_tag)

            ch.basic_qos(prefetch_count=10)
            ch.basic_consume(queue=RABBIT_QUEUE, on_message_callback=on_msg)
            print("[*] Rabbit consuming…")
            ch.start_consuming()
        except Exception as e:
            print(f"[RABBIT] conn err: {e}; retry in 5s")
            time.sleep(5)

def start_rabbit_if_enabled():
    if not RABBIT_ENABLE:
        return
    t = threading.Thread(target=rabbit_consume_loop, daemon=True)
    t.start()

# ---------------------------
# Локальный запуск (как делает start.sh)
# ---------------------------
def _shutdown(signum, frame):
    print("Signal received, exiting…")
    sys.exit(0)

if __name__ == "__main__":
    # перехват SIGTERM для корректного stop.sh
    signal.signal(signal.SIGTERM, _shutdown)
    start_rabbit_if_enabled()

    # поднимаем uvicorn программно
    import uvicorn
    uvicorn.run(app, host=LISTEN_HOST, port=LISTEN_PORT, log_level="info")