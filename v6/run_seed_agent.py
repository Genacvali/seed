#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Единая точка входа для SEED:
- запускает HTTP‑агент (FastAPI + Uvicorn)
- читает LISTEN_HOST / LISTEN_PORT из env / configs/seed.env (через seed-agent.py)

Используется как:
    python3 run_seed_agent.py
и как целевой скрипт для сборки бинарника PyInstaller.
"""

import os
import uvicorn


def main() -> None:
    host = os.getenv("LISTEN_HOST", "0.0.0.0")
    port = int(os.getenv("LISTEN_PORT", "8080"))

    # Вся логика и конфиг загружаются из seed-agent.py
    # (модуль указываем строкой — uvicorn сам его импортирует).
    uvicorn.run(
        "seed-agent:app",
        host=host,
        port=port,
        log_level="info",
        reload=False,
    )


if __name__ == "__main__":
    main()

