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
    subject = sys.argv[2] if len(sys.argv) > 2 else ""
    raw_json = sys.argv[3] if len(sys.argv) > 3 else ""
    
    # Отладочный вывод
    print(f"DEBUG: seed_url='{seed_url}'", file=sys.stderr)
    print(f"DEBUG: subject='{subject}'", file=sys.stderr)
    print(f"DEBUG: raw_json='{raw_json}'", file=sys.stderr)
    print(f"DEBUG: raw_json length={len(raw_json)}", file=sys.stderr)

    # Проверяем, есть ли вообще данные
    if not raw_json or raw_json.strip() == "":
        print("ERROR: {ALERT.MESSAGE} is empty! Check Zabbix Media Type configuration.", file=sys.stderr)
        # Создаём fallback payload из subject
        payload = {
            "subject": subject,
            "message": f"Empty message from Zabbix. Subject: {subject}",
            "event": {"value": "1", "severity": "warning"},
            "trigger": {"name": subject or "Zabbix Alert"},
            "host": {"name": "unknown"}
        }
        print(f"DEBUG: Using fallback payload: {payload}", file=sys.stderr)
    else:
        # Проверяем: это чистый JSON или текст с #SEED-JSON# тегами
        try:
            # Сначала пытаемся как чистый JSON
            payload = json.loads(raw_json)
            print("DEBUG: Parsed as clean JSON", file=sys.stderr)
        except:
            # Если не JSON, ищем теги #SEED-JSON#
            import re
            json_match = re.search(r'#SEED-JSON#\s*(\{.*?\})\s*#/SEED-JSON#', raw_json, re.DOTALL)
            if json_match:
                try:
                    # Извлекаем JSON из тегов
                    payload = json.loads(json_match.group(1))
                    print("DEBUG: Parsed JSON from #SEED-JSON# tags", file=sys.stderr)
                except Exception as e:
                    print("Invalid JSON inside #SEED-JSON# tags:", e, file=sys.stderr)
                    sys.exit(1)
            else:
                # Если нет тегов, отправляем как text payload
                payload = {
                    "subject": subject,
                    "message": raw_json
                }
                print("DEBUG: Created text payload", file=sys.stderr)

    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(seed_url, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=10) as resp:
        # можно напечатать ответ (Zabbix его покажет в логах теста)
        sys.stdout.write(resp.read().decode("utf-8", "ignore"))
    sys.exit(0)

if __name__ == "__main__":
    main()