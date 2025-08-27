#!/usr/bin/python3
# Adapted for SEED Agent v5 /zabbix endpoint
# Based on original by Mamashev Aleskey, mamashev@me.com, 2022(C)

import sys, os
__file__ = os.path.abspath(__file__)
__dir__ = os.path.dirname(os.path.realpath(__file__))
os.chdir(__dir__)
sys.path.append(__dir__+'/../python')
sys.path.append(__dir__+'/../python/modules')

# ----------------------------------------
import asyncio
import json
import cmpt.utils
import services
import base64
import re

def parse_severity_from_text(text: str) -> str:
    """Parse severity from Zabbix subject/message"""
    text_upper = text.upper()
    
    # Check for severity keywords
    if any(word in text_upper for word in ["CRITICAL", "DISASTER", "КАТАСТРОФА"]):
        return "disaster"
    elif any(word in text_upper for word in ["HIGH", "MAJOR", "ВЫСОКАЯ", "ПРОЦЕССОВ НЕТ"]):
        return "high"  
    elif any(word in text_upper for word in ["WARNING", "WARN", "AVERAGE", "СРЕДНЯЯ"]):
        return "average"
    elif any(word in text_upper for word in ["INFO", "INFORMATION", "ИНФОРМАЦИОННАЯ"]):
        return "information"
    else:
        # Default based on alert keywords
        if any(word in text_upper for word in ["ERROR", "FAIL", "DOWN", "UNAVAILABLE", "НЕТ", "НЕДОСТУПЕН"]):
            return "high"  # Treat errors as high severity
        # For test messages, use high to make them visible  
        if "TEST" in text_upper:
            return "high"
        return "average"  # Safe default

def extract_hostname_from_text(text: str) -> str:
    """Extract hostname from message"""
    # Look for hostname patterns - more specific first
    hostname_patterns = [
        r'([a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+-[a-zA-Z0-9]+\d+)',  # p-service-env-adv-msk01 pattern
        r'([a-zA-Z0-9\-]+(?:\-[a-zA-Z0-9\-]+){3,}\d+)',  # multi-dash pattern with numbers
        r'([a-zA-Z0-9\-]{10,})',  # long hostname pattern
        r'(test-server|test-host|localhost)',  # test hostnames
    ]
    
    for pattern in hostname_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    
    # Fallback: use 'test-server' for test messages
    if 'test' in text.lower():
        return 'test-server'
    
    return "unknown-host"

async def run():
    # Original payload structure
    original_payload = {
        'to': sys.argv[1],
        'subject': sys.argv[2],
        'message': sys.argv[3].replace('\\n','\n'),
        'mattermost': 'mattermost' in sys.argv,
        'telegram': 'telegram' in sys.argv,
    }
    
    # Convert to Zabbix format for SEED Agent /zabbix endpoint
    subject = sys.argv[2]
    message = sys.argv[3].replace('\\n','\n')
    
    # Parse components
    severity_text = parse_severity_from_text(subject + " " + message)
    hostname = extract_hostname_from_text(message)
    
    # Generate fake IDs (you can make these more sophisticated)
    import hashlib
    import time
    base_str = f"{subject}{hostname}{int(time.time())}"
    fake_trigger_id = str(abs(hash(base_str)) % 999999)
    fake_event_id = str(abs(hash(base_str + "event")) % 999999)
    
    # Create Zabbix-compatible payload for SEED Agent
    zabbix_payload = {
        "event": {
            "value": "1",  # 1 = problem, 0 = resolved
            "id": fake_event_id
        },
        "trigger": {
            "name": subject.replace("SEED Alert: ", "").strip(),
            "description": message,
            "severity_text": severity_text,
            "id": fake_trigger_id
        },
        "host": {
            "name": hostname,
            "host": hostname,
            "ip": "10.20.30.40"  # You can parse this from message or set dynamically
        },
        "item": {
            "name": "Custom Alert Item",
            "lastvalue": "N/A",
            "port": "0"
        }
    }

    print(f"[CONVERSION] subject='{subject}' -> severity='{severity_text}', hostname='{hostname}'")
    print(f"[ZABBIX PAYLOAD] {json.dumps(zabbix_payload, indent=2)}")

    # аттачи (если есть)
    for arg in sys.argv[3:]:
        if os.path.exists(arg):
            # For now, skip file attachments in Zabbix format
            # You can extend this if needed
            pass

    # определяем где запущен агент
    config = cmpt.utils.dictMerge((services.get('mmAgent',type='mmAgent',retval='config',first=True) or {}),{'instances': {'listner': {'host': '127.0.0.1', 'port': 3080}}}, overwrite=False)

    # ИЗМЕНЕНО: отправляем на /zabbix вместо /alert
    url = 'http://{}:{}/zabbix'.format(config['instances']['listner']['host'].replace('0.0.0.0','127.0.0.1'), config['instances']['listner']['port'])
    print('url', url)
    
    # стреляем
    try:
        resp = await cmpt.utils.fetch(url, method='POST', data=json.dumps(zabbix_payload), validCodes=[], retval=['text','status'], timeout=120)
        try:
            resp['text'] = json.loads(resp['text'])['status']
        except: pass

        if resp['status'] != 200:
            raise Exception(resp['text'])

        print(resp['text'])
        return 0
    except Exception as err:
        print('fail: {}'.format(str(err)))
        return 1

exit(asyncio.get_event_loop().run_until_complete(run()))