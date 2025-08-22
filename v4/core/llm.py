# -*- coding: utf-8 -*-
import os, time, json, uuid, requests
from pathlib import Path
from typing import Optional

CID   = os.getenv("GIGACHAT_CLIENT_ID")
CSEC  = os.getenv("GIGACHAT_CLIENT_SECRET")
SCOPE = os.getenv("GIGACHAT_SCOPE","GIGACHAT_API_PERS")
OAUTH = os.getenv("GIGACHAT_OAUTH_URL")
API   = os.getenv("GIGACHAT_API_URL")
MODEL = os.getenv("GIGACHAT_MODEL","GigaChat-2")
VERIFY= os.getenv("GIGACHAT_VERIFY_SSL","1") == "1"
CACHE = Path(os.getenv("GIGACHAT_TOKEN_CACHE","/tmp/gigachat_token.json"))

class GigaChat:
    def __init__(self):
        if not all([CID, CSEC, OAUTH, API]):
            self.enabled = False
        else:
            self.enabled = True

    def _load_token(self) -> Optional[str]:
        if not CACHE.exists(): return None
        try:
            data = json.loads(CACHE.read_text())
            if int(time.time()) < data.get("exp",0) - 30:
                return data.get("access_token")
        except: pass
        return None

    def _save_token(self, token: str, ttl: int):
        CACHE.parent.mkdir(parents=True, exist_ok=True)
        CACHE.write_text(json.dumps({"access_token": token, "exp": int(time.time())+ttl}, ensure_ascii=False))

    def _get_token(self) -> str:
        t = self._load_token()
        if t: return t
        # OAuth
        import base64
        auth_key = base64.b64encode(f"{CID}:{CSEC}".encode()).decode()
        headers = {
            "Content-Type":"application/x-www-form-urlencoded",
            "Accept":"application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {auth_key}"
        }
        data = {"scope": SCOPE}
        r = requests.post(OAUTH, headers=headers, data=data, timeout=15, verify=VERIFY)
        r.raise_for_status()
        token = r.json().get("access_token")
        self._save_token(token, ttl=60*30)
        return token

    def ask(self, prompt: str, max_tokens: int = 150) -> str:
        if not self.enabled:
            return ""
        token = self._get_token()
        payload = {
            "model": MODEL,
            "messages": [{"role":"user","content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        r = requests.post(API, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=30, verify=VERIFY)
        if r.status_code == 401:
            # попробуем обновить токен
            token = self._get_token()
            r = requests.post(API, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=30, verify=VERIFY)
        r.raise_for_status()
        js = r.json()
        try:
            return js["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(js, ensure_ascii=False)


class LLMClient:
    """Universal LLM client wrapper for SEED Agent v5"""
    
    def __init__(self, config):
        self.config = config
        
        # Initialize GigaChat client with config values
        if config.get("llm.enabled", True):
            # Set environment variables from config BEFORE creating GigaChat
            gigachat_config = config.get("llm.gigachat", {})
            import os
            
            if gigachat_config:
                os.environ["GIGACHAT_CLIENT_ID"] = gigachat_config.get("client_id", "")
                os.environ["GIGACHAT_CLIENT_SECRET"] = gigachat_config.get("client_secret", "")
                os.environ["GIGACHAT_SCOPE"] = gigachat_config.get("scope", "GIGACHAT_API_PERS")
                os.environ["GIGACHAT_OAUTH_URL"] = gigachat_config.get("oauth_url", "")
                os.environ["GIGACHAT_API_URL"] = gigachat_config.get("api_url", "")
                os.environ["GIGACHAT_MODEL"] = gigachat_config.get("model", "GigaChat-2")
                os.environ["GIGACHAT_VERIFY_SSL"] = "1" if gigachat_config.get("verify_ssl", False) else "0"
                os.environ["GIGACHAT_TOKEN_CACHE"] = gigachat_config.get("token_cache", "/tmp/gigachat_token.json")
                
                # Now create GigaChat with env vars set
                self.gigachat = GigaChat()
                self.enabled = self.gigachat.enabled
            else:
                self.gigachat = None
                self.enabled = False
        else:
            self.gigachat = None
            self.enabled = False
            
    async def get_completion(self, prompt: str, max_tokens: int = 500) -> str:
        """Get completion from LLM"""
        try:
            if not self.enabled or not self.gigachat:
                return "LLM недоступен - анализ не выполнен"
                
            # Call GigaChat synchronously (it's not async)
            import asyncio
            loop = asyncio.get_event_loop()
            
            # Run in thread pool to avoid blocking
            result = await loop.run_in_executor(
                None, self.gigachat.ask, prompt, max_tokens
            )
            
            return result or "LLM не вернул результат"
            
        except Exception as e:
            return f"Ошибка LLM: {str(e)}"
