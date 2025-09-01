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

import requests
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse

try:
    from dotenv import load_dotenv
except Exception:
    load_dotenv = None

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
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, "configs", "seed.env")

def load_env():
    # удаляем CRLF на лету (на всякий)
    if os.path.exists(ENV_PATH):
        try:
            with open(ENV_PATH, "rb") as f:
                raw = f.read()
            raw = raw.replace(b"\r\n", b"\n")
            with open(ENV_PATH, "wb") as f:
                f.write(raw)
        except Exception:
            pass

    if load_dotenv is not None and os.path.exists(ENV_PATH):
        load_dotenv(ENV_PATH)

load_env()

# ---------------------------
# Конфигурация из ENV
# ---------------------------
LISTEN_HOST = os.getenv("LISTEN_HOST", "0.0.0.0")
LISTEN_PORT = int(os.getenv("LISTEN_PORT", "8080"))

MM_WEBHOOK      = os.getenv("MM_WEBHOOK", "")
MM_VERIFY_SSL   = os.getenv("MM_VERIFY_SSL", "1") not in ("0", "false", "False")
USE_LLM         = os.getenv("USE_LLM", "0") in ("1", "true", "True")

# GigaChat
GIGACHAT_CLIENT_ID     = os.getenv("GIGACHAT_CLIENT_ID")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET")
GIGACHAT_SCOPE         = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
GIGACHAT_OAUTH_URL     = os.getenv("GIGACHAT_OAUTH_URL", "https://ngw.devices.sberbank.ru:9443/api/v2/oauth")
GIGACHAT_API_URL       = os.getenv("GIGACHAT_API_URL", "https://gigachat.devices.sberbank.ru/api/v1/chat/completions")
GIGACHAT_MODEL         = os.getenv("GIGACHAT_MODEL", "GigaChat-2")
GIGACHAT_VERIFY_SSL    = os.getenv("GIGACHAT_VERIFY_SSL", "1") not in ("0", "false", "False")
GIGACHAT_TOKEN_CACHE   = os.getenv("GIGACHAT_TOKEN_CACHE", "/tmp/gigachat_token.json")

# Rabbit
RABBIT_ENABLE   = os.getenv("RABBIT_ENABLE", "0") in ("1", "true", "True")
RABBIT_HOST     = os.getenv("RABBIT_HOST", "localhost")
RABBIT_PORT     = int(os.getenv("RABBIT_PORT", "5672"))
RABBIT_SSL      = os.getenv("RABBIT_SSL", "0") in ("1", "true", "True")
RABBIT_USER     = os.getenv("RABBIT_USER", "seed")
RABBIT_PASS     = os.getenv("RABBIT_PASS", "seedpass")
RABBIT_VHOST    = os.getenv("RABBIT_VHOST", "/")
RABBIT_QUEUE    = os.getenv("RABBIT_QUEUE", "seed-inbox")

# Prometheus enrichment
PROM_URL        = os.getenv("PROM_URL", "")
PROM_VERIFY_SSL = os.getenv("PROM_VERIFY_SSL", "1") not in ("0", "false", "False")
PROM_TIMEOUT    = os.getenv("PROM_TIMEOUT", "3")
PROM_BEARER     = os.getenv("PROM_BEARER", "")

# ---------------------------
# Утилиты: Mattermost
# ---------------------------
def mm_post(text: str, color: Optional[str] = None) -> bool:
    if not MM_WEBHOOK:
        print("[MM] webhook not set")
        return False
    try:
        # Если указан цвет, используем attachment для цветного сообщения
        if color:
            payload = {
                "attachments": [{
                    "color": color,
                    "text": text,
                    "mrkdwn_in": ["text"]
                }]
            }
        else:
            payload = {"text": text}
            
        r = requests.post(MM_WEBHOOK, json=payload, timeout=10, verify=MM_VERIFY_SSL)
        if r.status_code // 100 == 2:
            print("[MM] OK")
            return True
        print(f"[MM] ERR {r.status_code}: {r.text[:200]}")
        return False
    except Exception as e:
        print(f"[MM] EXC: {e}")
        return False

# ---------------------------
# Утилиты: GigaChat (минимал)
# ---------------------------
def _load_cached_token() -> Optional[Dict[str, Any]]:
    try:
        if os.path.exists(GIGACHAT_TOKEN_CACHE):
            with open(GIGACHAT_TOKEN_CACHE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception:
        pass
    return None

def _save_cached_token(tok: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(GIGACHAT_TOKEN_CACHE), exist_ok=True)
        with open(GIGACHAT_TOKEN_CACHE, "w", encoding="utf-8") as f:
            json.dump(tok, f)
    except Exception:
        pass

def _now_ms() -> int:
    return int(time.time() * 1000)

def _get_gc_token() -> Optional[str]:
    # cache first  
    cached = _load_cached_token()
    if cached and isinstance(cached, dict):
        # Проверяем по времени жизни токена
        if cached.get("access_token") and cached.get("exp", 0) > int(time.time()) + 30:
            return cached["access_token"]

    if not (GIGACHAT_CLIENT_ID and GIGACHAT_CLIENT_SECRET):
        print("[LLM] OAuth credentials missing")
        return None

    # OAuth (как в v5)
    try:
        import base64, uuid
        
        # Подавляем SSL warnings
        import urllib3
        urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
        
        auth_key = base64.b64encode(f"{GIGACHAT_CLIENT_ID}:{GIGACHAT_CLIENT_SECRET}".encode()).decode()
        hdr = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),  # Важно! UUID, не timestamp
            "Authorization": f"Basic {auth_key}"
        }
        
        data = {"scope": GIGACHAT_SCOPE}
        print(f"[LLM] OAuth request to {GIGACHAT_OAUTH_URL}")
        
        r = requests.post(GIGACHAT_OAUTH_URL, headers=hdr, data=data, timeout=15, verify=GIGACHAT_VERIFY_SSL)
        print(f"[LLM] OAuth status: {r.status_code}")
        
        if r.status_code // 100 != 2:
            print(f"[LLM] OAuth ERR {r.status_code}: {r.text[:200]}")
            return None
            
        tok_data = r.json()
        print(f"[LLM] OAuth response keys: {list(tok_data.keys())}")
        
        # Сохраняем как в v5
        token = tok_data.get("access_token")
        if token:
            # Сохраняем с правильным форматом времени
            cache_data = {
                "access_token": token,
                "exp": int(time.time()) + 1800  # 30 минут
            }
            _save_cached_token(cache_data)
            print(f"[LLM] OAuth success, token cached")
            return token
        else:
            print(f"[LLM] No access_token in response: {tok_data}")
            return None
            
    except Exception as e:
        print(f"[LLM] OAuth EXC: {e}")
        return None

def clean_llm_response(text: str) -> str:
    """Очищает LLM ответ от блоков кода и форматирует для Mattermost"""
    import re
    
    # Убираем блоки кода ```sql, ```bash и т.д.
    text = re.sub(r'```\w*\n.*?\n```', '', text, flags=re.DOTALL)
    text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    
    # Убираем лишние ключевые слова
    text = re.sub(r'\b(sql|bash|plpgsql)\b', '', text, flags=re.IGNORECASE)
    
    # Заменяем нумерацию на переносы строк для лучшего форматирования
    text = re.sub(r'\b(\d+)\.\s*', r'\n• ', text)
    text = re.sub(r'\b(Диагностика:|Рекомендации:)', r'\n**\1**', text)
    
    # Чистим лишние пробелы и пустые строки
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line and line != '•']
    
    return '\n'.join(lines).strip()

def llm_tip(prompt: str, max_tokens: int = 400) -> Optional[str]:
    if not USE_LLM:
        print("[LLM] disabled (USE_LLM=0)")
        return None
    
    print(f"[LLM] requesting tip for prompt: {prompt[:100]}...")
    
    tok = _get_gc_token()
    if not tok:
        print("[LLM] no token available")
        return None
        
    try:
        payload = {
            "model": GIGACHAT_MODEL,
            "temperature": 0.2,
            "max_tokens": max_tokens,
            "messages": [
                {"role": "system", "content": "Ты SRE/DBA ассистент. Отвечай кратко и по делу."},
                {"role": "user", "content": prompt.strip()},
            ]
        }
        
        print(f"[LLM] sending request to {GIGACHAT_API_URL}")
        r = requests.post(GIGACHAT_API_URL, headers={"Authorization": f"Bearer {tok}"}, json=payload,
                          timeout=20, verify=GIGACHAT_VERIFY_SSL)
        
        print(f"[LLM] response status: {r.status_code}")
        
        if r.status_code // 100 != 2:
            print(f"[LLM] chat ERR {r.status_code}: {r.text[:200]}")
            return None
            
        j = r.json()
        msg = j.get("choices", [{}])[0].get("message", {}).get("content")
        
        if isinstance(msg, str) and msg.strip():
            # Очищаем ответ от блоков кода и форматируем
            result = clean_llm_response(msg.strip())
            print(f"[LLM] success: {result[:100]}...")
            return result
        else:
            print(f"[LLM] empty or invalid response: {j}")
            return None
            
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

def fmt_alert_line(alert: Dict[str, Any], enriched: Dict[str, Any] = None) -> str:
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
    lines = [
        f"{emoji} **{name}** {status_icon}",
        f"└── Host: `{inst}` | Severity: **{sev.upper()}**"
    ]
    
    # Добавляем enriched контекст если есть
    if enriched and enriched.get("summary_line"):
        lines.append(f"└── 📊 {enriched['summary_line']}")
    
    lines.append(f"└── {summary}")
    
    return "\n".join(lines)

def fmt_batch_message(alerts: List[Dict[str, Any]]) -> tuple:
    """Возвращает (текст_сообщения, цвет_для_mattermost)"""
    if not alerts:
        return "🌌 **SEED Crystal** - No alerts detected", None
    
    # FF-style заголовок
    head = "🌌 **S.E.E.D.** - Smart Event Explainer & Diagnostics\n" + "═" * 55
    
    lines = []
    severities = []
    llm_context = []
    
    plugin_results = []
    
    for a in alerts:
        # Обогащаем алерт данными из Prometheus
        enriched = {}
        if ENRICHMENT_AVAILABLE and PROM_URL:
            try:
                enriched = enrich_alert(a)
                print(f"[ENRICH] {a.get('labels', {}).get('alertname', 'Alert')}: {enriched.get('summary_line', 'no data')}")
            except Exception as e:
                print(f"[ENRICH] failed: {e}")
        
        # Запускаем плагин для алерта
        plugin_result = None
        if PLUGINS_AVAILABLE and plugin_router and PROM_CLIENT_AVAILABLE and prom:
            try:
                plugin_result = plugin_router.run_plugin(a, prom)
                if plugin_result:
                    plugin_results.append(plugin_result)
            except Exception as e:
                print(f"[PLUGIN] Error processing alert: {e}")
        
        lines.append(fmt_alert_line(a, enriched))
        severities.append(a.get("labels", {}).get("severity", "info"))
        
        # Создаем более богатый контекст для LLM
        labels = a.get("labels", {})
        ann = a.get("annotations", {})
        alert_context = f"{labels.get('alertname', 'Alert')}: {ann.get('summary', '')}"
        
        # Добавляем метрики в контекст для LLM
        if enriched.get("summary_line"):
            alert_context += f" | Метрики: {enriched['summary_line']}"
        
        # Добавляем результаты плагина в контекст LLM
        if plugin_result and plugin_result.get("lines"):
            plugin_summary = "; ".join(plugin_result["lines"][:3])  # Первые 3 строки
            alert_context += f" | Плагин: {plugin_summary}"
            
        llm_context.append(alert_context)
    
    text = head + "\n\n" + "\n\n".join(lines)
    
    # Краткая статистика
    if len(alerts) > 1:
        sev_counts = {}
        for s in severities:
            sev_counts[s] = sev_counts.get(s, 0) + 1
        stats = " | ".join([f"{get_severity_emoji(s)} {s}:{c}" for s, c in sev_counts.items()])
        text += f"\n\n📊 **Summary:** {stats}"
    
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
    if USE_LLM and len(alerts) > 0:
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
        "mm_webhook": bool(MM_WEBHOOK),
        "use_llm": USE_LLM,
        "rabbit_enabled": RABBIT_ENABLE,
        "prometheus_enrichment": ENRICHMENT_AVAILABLE and bool(PROM_URL),
        "prometheus_url": PROM_URL if PROM_URL else None,
        "version": "v6.1"
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
    ok = mm_post(text, color)
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
    ok = mm_post(text, color)
    return {"ok": ok}

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
                    mm_post(text, color)
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