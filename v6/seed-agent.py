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

# ---------------------------
# Утилиты: Mattermost
# ---------------------------
def mm_post(text: str) -> bool:
    if not MM_WEBHOOK:
        print("[MM] webhook not set")
        return False
    try:
        r = requests.post(MM_WEBHOOK, json={"text": text}, timeout=10, verify=MM_VERIFY_SSL)
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
        if cached.get("access_token") and cached.get("expires_at", 0) - _now_ms() > 10_000:
            return cached["access_token"]

    if not (GIGACHAT_CLIENT_ID and GIGACHAT_CLIENT_SECRET):
        return None

    # OAuth
    try:
        import base64
        credentials = f"{GIGACHAT_CLIENT_ID}:{GIGACHAT_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        hdr = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(int(time.time()*1000)),
            "Authorization": f"Basic {encoded_credentials}"
        }
        data = {"scope": GIGACHAT_SCOPE}
        r = requests.post(GIGACHAT_OAUTH_URL, headers=hdr, data=data, timeout=15, verify=GIGACHAT_VERIFY_SSL)
        if r.status_code // 100 != 2:
            print(f"[LLM] OAuth ERR {r.status_code}: {r.text[:200]}")
            return None
        tok = r.json()
        _save_cached_token(tok)
        return tok.get("access_token")
    except Exception as e:
        print(f"[LLM] OAuth EXC: {e}")
        return None

def llm_tip(prompt: str, max_tokens: int = 120) -> Optional[str]:
    if not USE_LLM:
        return None
    tok = _get_gc_token()
    if not tok:
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
        r = requests.post(GIGACHAT_API_URL, headers={"Authorization": f"Bearer {tok}"}, json=payload,
                          timeout=20, verify=GIGACHAT_VERIFY_SSL)
        if r.status_code // 100 != 2:
            print(f"[LLM] chat ERR {r.status_code}: {r.text[:200]}")
            return None
        j = r.json()
        msg = j.get("choices", [{}])[0].get("message", {}).get("content")
        if isinstance(msg, str):
            return " ".join(msg.strip().split())
    except Exception as e:
        print(f"[LLM] chat EXC: {e}")
    return None

# ---------------------------
# Форматирование алертов
# ---------------------------
def fmt_alert_line(alert: Dict[str, Any]) -> str:
    labels = alert.get("labels", {})
    ann    = alert.get("annotations", {})
    status = alert.get("status", "firing")
    name   = labels.get("alertname", "Alert")
    inst   = labels.get("instance") or labels.get("pod") or labels.get("job") or "-"
    sev    = labels.get("severity", "info")
    summary = ann.get("summary") or ann.get("description") or ""
    return (f"**{name}** · `{status}` · sev={sev}\n"
            f"• instance: `{inst}`\n"
            f"• {summary}".strip())

def fmt_batch_message(alerts: List[Dict[str, Any]]) -> str:
    if not alerts:
        return "SEED: пустой список алёртов"
    head = "SEED · Alertmanager webhook\n"
    lines = []
    for a in alerts:
        lines.append(fmt_alert_line(a))
    text = head + "\n\n" + "\n\n".join(lines)
    # LLM одна короткая рекомендация на пачку
    tip = llm_tip("Даны одну или несколько аварий мониторинга (Prometheus Alertmanager). "
                  "Предложи 1–2 очень кратких практичных шага диагностики (≤180 символов). "
                  "Без общих фраз, только конкретика.")
    if tip:
        text += f"\n\n**LLM совет:** {tip}"
    return text

# ---------------------------
# FastAPI приложение
# ---------------------------
app = FastAPI(title="SEED v6 Agent")

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "mm_webhook": bool(MM_WEBHOOK),
        "use_llm": USE_LLM,
        "rabbit_enabled": RABBIT_ENABLE,
        "version": "v6"
    }

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
    text = fmt_batch_message(pkg["alerts"])
    ok = mm_post(text)
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

    text = fmt_batch_message(alerts)
    ok = mm_post(text)
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
    params = pika.ConnectionParameters(
        host=RABBIT_HOST,
        port=RABBIT_PORT,
        virtual_host=RABBIT_VHOST,
        credentials=creds,
        ssl=RABBIT_SSL
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
                        text = fmt_batch_message(j["alerts"])
                    else:
                        # обернём одиночный в пакет
                        text = fmt_batch_message([j])
                    mm_post(text)
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