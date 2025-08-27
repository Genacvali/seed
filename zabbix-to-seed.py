#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys, json, urllib.request

def main():
    # Ожидаем параметры от Zabbix Script media type:
    #   argv[1] = {ALERT.SENDTO}  -> например: http://<seed-host>:8080/zabbix
    #   argv[2] = {ALERT.SUBJECT} -> не нужен для отправки, оставим для логики/фьючерсов
    #   argv[3] = {ALERT.MESSAGE} -> ТУТ JSON с макросами (event/trigger/host/item)
    if len(sys.argv) < 3:
        print("Usage: zabbix-to-seed.py <SEED_URL> <SUBJECT> <JSON>", file=sys.stderr)
        sys.exit(1)

    seed_url = sys.argv[1]
    raw_json = sys.argv[3] if len(sys.argv) > 3 else ""

    # На всякий: валидируем, что это JSON
    try:
        payload = json.loads(raw_json)
    except Exception as e:
        print("Invalid JSON in {ALERT.MESSAGE}:", e, file=sys.stderr)
        sys.exit(1)

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(seed_url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        # можно напечатать ответ (Zabbix его покажет в логах теста)
        sys.stdout.write(resp.read().decode("utf-8", "ignore"))
    sys.exit(0)

if __name__ == "__main__":
    main()