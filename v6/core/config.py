# -*- coding: utf-8 -*-
import os
from pathlib import Path
from dataclasses import dataclass

BASE = Path(__file__).resolve().parent.parent
CFG_DIR = BASE / "configs"
_ENV_PATH = CFG_DIR / "seed.env"

# Загружаем .env ДО создания CFG, чтобы os.environ был уже заполнен.
# Делаем это здесь, а не в seed-agent.py, потому что этот модуль
# импортируется первым и CFG создаётся сразу при импорте.
try:
    from dotenv import load_dotenv as _load_dotenv
    if _ENV_PATH.exists():
        # Читаем и нормализуем CRLF на лету
        _raw = _ENV_PATH.read_bytes().replace(b"\r\n", b"\n")
        _ENV_PATH.write_bytes(_raw)
        _load_dotenv(_ENV_PATH, override=True)
except Exception:
    pass


def _getenv(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


@dataclass
class Config:
    # http
    listen_host: str = _getenv("LISTEN_HOST", "0.0.0.0")
    listen_port: int = int(_getenv("LISTEN_PORT", "") or "8080")

    # mattermost
    mm_webhook:    str  = _getenv("MM_WEBHOOK", "")
    mm_verify_ssl: bool = _getenv("MM_VERIFY_SSL", "1") not in ("0", "false", "False")

    # llm
    use_llm:         bool = _getenv("USE_LLM", "0") == "1"
    gc_client_id:    str  = _getenv("GIGACHAT_CLIENT_ID", "")
    gc_client_secret:str  = _getenv("GIGACHAT_CLIENT_SECRET", "")
    gc_scope:        str  = _getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    gc_oauth_url:    str  = _getenv("GIGACHAT_OAUTH_URL", "")
    gc_api_url:      str  = _getenv("GIGACHAT_API_URL", "")
    gc_model:        str  = _getenv("GIGACHAT_MODEL", "GigaChat-2")
    gc_verify_ssl:   bool = _getenv("GIGACHAT_VERIFY_SSL", "1") not in ("0", "false", "False")
    gc_token_cache:  str  = _getenv("GIGACHAT_TOKEN_CACHE", "/tmp/gigachat_token.json")

    # rabbitmq
    rabbit_enabled: bool = _getenv("RABBIT_ENABLE", "0") == "1"
    rabbit_host:    str  = _getenv("RABBIT_HOST", "localhost")
    rabbit_port:    int  = int(_getenv("RABBIT_PORT", "") or "5672")
    rabbit_ssl:     bool = _getenv("RABBIT_SSL", "0") == "1"
    rabbit_user:    str  = _getenv("RABBIT_USER", "guest")
    rabbit_pass:    str  = _getenv("RABBIT_PASS", "guest")
    rabbit_vhost:   str  = _getenv("RABBIT_VHOST", "/")
    rabbit_queue:   str  = _getenv("RABBIT_QUEUE", "seed-inbox")

    # telegraf exporter
    telegraf_url: str = _getenv("TELEGRAF_URL", "http://localhost:9216/metrics")


CFG = Config()
