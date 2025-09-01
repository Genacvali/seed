# -*- coding: utf-8 -*-
import os
from pathlib import Path
from dataclasses import dataclass

BASE = Path(__file__).resolve().parent.parent
CFG_DIR = BASE / "configs"

def _getenv(name: str, default: str = "") -> str:
    return os.environ.get(name, default)

@dataclass
class Config:
    # http
    listen_host: str = _getenv("LISTEN_HOST", "0.0.0.0")
    listen_port: int = int(_getenv("LISTEN_PORT", "8080"))

    # mattermost
    mm_webhook: str = _getenv("MM_WEBHOOK", "")
    mm_verify_ssl: bool = _getenv("MM_VERIFY_SSL", "1") == "1"

    # llm
    use_llm: bool = _getenv("USE_LLM", "0") == "1"
    gc_client_id: str = _getenv("GIGACHAT_CLIENT_ID", "")
    gc_client_secret: str = _getenv("GIGACHAT_CLIENT_SECRET", "")
    gc_scope: str = _getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
    gc_oauth_url: str = _getenv("GIGACHAT_OAUTH_URL", "")
    gc_api_url: str = _getenv("GIGACHAT_API_URL", "")
    gc_model: str = _getenv("GIGACHAT_MODEL", "GigaChat-2")
    gc_verify_ssl: bool = _getenv("GIGACHAT_VERIFY_SSL", "1") == "1"
    gc_token_cache: str = _getenv("GIGACHAT_TOKEN_CACHE", "/tmp/gigachat_token.json")

    # rabbitmq
    rabbit_enabled: bool = _getenv("RABBIT_ENABLE", "0") == "1"
    rabbit_host: str = _getenv("RABBIT_HOST", "localhost")
    rabbit_port: int = int(_getenv("RABBIT_PORT", "5672"))
    rabbit_ssl: bool = _getenv("RABBIT_SSL", "0") == "1"
    rabbit_user: str = _getenv("RABBIT_USER", "guest")
    rabbit_pass: str = _getenv("RABBIT_PASS", "guest")
    rabbit_vhost: str = _getenv("RABBIT_VHOST", "/")
    rabbit_queue: str = _getenv("RABBIT_QUEUE", "seed-inbox")

    # telegraf exporter
    telegraf_url: str = _getenv("TELEGRAF_URL", "http://localhost:9216/metrics")

CFG = Config()