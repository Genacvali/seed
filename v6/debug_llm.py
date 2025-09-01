#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Диагностика LLM проблем в SEED
"""
import os
import requests
import json

# Загружаем env
if os.path.exists("configs/seed.env"):
    from dotenv import load_dotenv
    load_dotenv("configs/seed.env")

# GigaChat параметры
GIGACHAT_CLIENT_ID = os.getenv("GIGACHAT_CLIENT_ID")
GIGACHAT_CLIENT_SECRET = os.getenv("GIGACHAT_CLIENT_SECRET") 
USE_LLM = os.getenv("USE_LLM", "0") == "1"

def test_gigachat_direct():
    """Прямой тест GigaChat API"""
    print("🧠 Testing GigaChat API directly...")
    print(f"   USE_LLM: {USE_LLM}")
    print(f"   CLIENT_ID: {'✅ set' if GIGACHAT_CLIENT_ID else '❌ missing'}")
    print(f"   CLIENT_SECRET: {'✅ set' if GIGACHAT_CLIENT_SECRET else '❌ missing'}")
    
    if not USE_LLM:
        print("❌ LLM disabled in config. Set USE_LLM=1")
        return False
        
    if not (GIGACHAT_CLIENT_ID and GIGACHAT_CLIENT_SECRET):
        print("❌ GigaChat credentials missing")
        return False
    
    # Тестируем OAuth
    try:
        import base64
        credentials = f"{GIGACHAT_CLIENT_ID}:{GIGACHAT_CLIENT_SECRET}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json", 
            "Authorization": f"Basic {encoded_credentials}",
            "RqUID": "test-12345"
        }
        
        data = {"scope": "GIGACHAT_API_PERS"}
        oauth_url = "https://ngw.devices.sberbank.ru:9443/api/v2/oauth"
        
        print(f"🔐 Testing OAuth: {oauth_url}")
        r = requests.post(oauth_url, headers=headers, data=data, timeout=15, verify=False)
        
        print(f"   Status: {r.status_code}")
        if r.status_code == 200:
            token_data = r.json()
            print("✅ OAuth successful!")
            access_token = token_data.get("access_token")
            
            # Тестируем chat API
            chat_url = "https://gigachat.devices.sberbank.ru/api/v1/chat/completions"
            chat_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            
            chat_payload = {
                "model": "GigaChat-2",
                "messages": [
                    {"role": "system", "content": "Ты SRE ассистент. Отвечай кратко."},
                    {"role": "user", "content": "Тест: дай краткий совет по диску 94% заполнения"}
                ],
                "max_tokens": 50,
                "temperature": 0.2
            }
            
            print(f"💬 Testing Chat API: {chat_url}")
            chat_r = requests.post(chat_url, json=chat_payload, headers=chat_headers, timeout=20, verify=False)
            print(f"   Status: {chat_r.status_code}")
            
            if chat_r.status_code == 200:
                response = chat_r.json()
                message = response.get("choices", [{}])[0].get("message", {}).get("content", "")
                print(f"✅ Chat API working! Response: {message}")
                return True
            else:
                print(f"❌ Chat API failed: {chat_r.text}")
                return False
        else:
            print(f"❌ OAuth failed: {r.text}")
            return False
            
    except Exception as e:
        print(f"❌ GigaChat test failed: {e}")
        return False

def test_seed_llm_endpoint():
    """Тест LLM через SEED API"""
    print(f"\n🌐 Testing SEED LLM endpoint...")
    
    try:
        # Простой тест алерт
        payload = {
            "alerts": [{
                "status": "firing",
                "labels": {
                    "alertname": "TestLLM",
                    "instance": "test-host",
                    "severity": "critical"
                },
                "annotations": {
                    "summary": "Test LLM functionality with disk 95% full"
                }
            }]
        }
        
        print("📤 Sending test alert to SEED...")
        r = requests.post("http://localhost:8080/alertmanager", json=payload, timeout=30)
        print(f"   Status: {r.status_code}")
        print(f"   Response: {r.text}")
        
        if r.status_code == 200:
            print("✅ Alert sent, check logs for LLM processing")
            return True
        else:
            print(f"❌ SEED API error: {r.text}")
            return False
            
    except Exception as e:
        print(f"❌ SEED API test failed: {e}")
        return False

def check_seed_logs():
    """Проверка логов SEED"""
    print(f"\n📋 Last 10 lines from SEED logs:")
    try:
        with open("logs/agent.log", "r") as f:
            lines = f.readlines()
            for line in lines[-10:]:
                print(f"   {line.strip()}")
    except Exception as e:
        print(f"❌ Cannot read logs: {e}")

def main():
    print("🔍 SEED LLM Diagnostics")
    print("=" * 50)
    
    # 1. Прямой тест GigaChat
    gigachat_ok = test_gigachat_direct()
    
    # 2. Тест через SEED
    if gigachat_ok:
        test_seed_llm_endpoint()
    
    # 3. Проверка логов
    check_seed_logs()
    
    print(f"\n💡 Recommendations:")
    if not gigachat_ok:
        print("   1. Check GigaChat credentials in configs/seed.env")
        print("   2. Verify network access to Sber GigaChat API")
        print("   3. Check SSL certificate issues (GIGACHAT_VERIFY_SSL=0)")
    else:
        print("   1. Check SEED logs: tail -f logs/agent.log")
        print("   2. Monitor LLM processing: tail -f logs/agent.log | grep LLM")
        print("   3. Verify prompt formatting in code")

if __name__ == "__main__":
    main()