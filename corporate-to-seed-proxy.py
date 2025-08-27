#!/usr/bin/python3
# Прокси-скрипт: принимает корпоративный формат, отправляет в SEED Agent

import sys
import json
import urllib.request

def main():
    if len(sys.argv) < 4:
        print("Usage: corporate-to-seed-proxy.py <to> <subject> <message>")
        return 1
    
    # Принимаем корпоративные параметры  
    to = sys.argv[1]
    subject = sys.argv[2]  
    message = sys.argv[3].replace('\\n', '\n')
    
    # Формируем payload для SEED Agent
    payload = {
        'to': to,
        'subject': subject,
        'message': message,
        'mattermost': 'mattermost' in sys.argv,
        'telegram': 'telegram' in sys.argv
    }
    
    # URL SEED Agent
    seed_url = 'http://p-dba-seed-adv-msk01:8080/zabbix'
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(seed_url, data=data, headers={'Content-Type': 'application/json'})
        
        with urllib.request.urlopen(req, timeout=120) as resp:
            print(resp.read().decode('utf-8'))
            return 0
            
    except Exception as err:
        print(f'fail: {err}')
        return 1

if __name__ == '__main__':
    exit(main())