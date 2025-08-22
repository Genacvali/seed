# -*- coding: utf-8 -*-
import os, time, json, uuid, requests
from pathlib import Path
from typing import Optional

# Environment variables will be set dynamically by LLMClient

class GigaChat:
    def __init__(self):
        # Get environment variables dynamically
        self.client_id = os.getenv("GIGACHAT_CLIENT_ID")
        self.client_secret = os.getenv("GIGACHAT_CLIENT_SECRET")
        self.scope = os.getenv("GIGACHAT_SCOPE", "GIGACHAT_API_PERS")
        self.oauth_url = os.getenv("GIGACHAT_OAUTH_URL")
        self.api_url = os.getenv("GIGACHAT_API_URL")
        self.model = os.getenv("GIGACHAT_MODEL", "GigaChat-2")
        self.verify_ssl = os.getenv("GIGACHAT_VERIFY_SSL", "1") == "1"
        self.token_cache = Path(os.getenv("GIGACHAT_TOKEN_CACHE", "/tmp/gigachat_token.json"))
        
        # Check if all required parameters are present
        import logging
        logger = logging.getLogger(__name__)
        
        missing = []
        if not self.client_id:    missing.append("GIGACHAT_CLIENT_ID")
        if not self.client_secret:missing.append("GIGACHAT_CLIENT_SECRET")
        if not self.oauth_url:    missing.append("GIGACHAT_OAUTH_URL")
        if not self.api_url:      missing.append("GIGACHAT_API_URL")
        
        if missing:
            self.enabled = False
            logger.error(f"❌ GigaChat disabled: missing env vars: {', '.join(missing)}")
        else:
            self.enabled = True
            logger.info(f"✅ GigaChat env OK (model={self.model}, verify_ssl={self.verify_ssl})")

    def _load_token(self) -> Optional[str]:
        if not self.token_cache.exists(): 
            return None
        try:
            data = json.loads(self.token_cache.read_text())
            if int(time.time()) < data.get("exp", 0) - 30:
                return data.get("access_token")
        except: 
            pass
        return None

    def _save_token(self, token: str, ttl: int):
        self.token_cache.parent.mkdir(parents=True, exist_ok=True)
        self.token_cache.write_text(json.dumps({
            "access_token": token, 
            "exp": int(time.time()) + ttl
        }, ensure_ascii=False))

    def _get_token(self) -> str:
        t = self._load_token()
        if t: 
            return t
        
        # OAuth
        import base64
        auth_key = base64.b64encode(f"{self.client_id}:{self.client_secret}".encode()).decode()
        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {auth_key}"
        }
        data = {"scope": self.scope}
        
        r = requests.post(
            self.oauth_url, 
            headers=headers, 
            data=data, 
            timeout=15, 
            verify=self.verify_ssl
        )
        r.raise_for_status()
        token = r.json().get("access_token")
        self._save_token(token, ttl=60*30)
        return token

    def ask(self, prompt: str, max_tokens: int = 150) -> str:
        if not self.enabled:
            return ""
            
        token = self._get_token()
        payload = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        
        r = requests.post(
            self.api_url, 
            json=payload, 
            headers={"Authorization": f"Bearer {token}"}, 
            timeout=30, 
            verify=self.verify_ssl
        )
        
        if r.status_code == 401:
            # попробуем обновить токен
            token = self._get_token()
            r = requests.post(
                self.api_url, 
                json=payload, 
                headers={"Authorization": f"Bearer {token}"}, 
                timeout=30, 
                verify=self.verify_ssl
            )
            
        r.raise_for_status()
        js = r.json()
        try:
            return js["choices"][0]["message"]["content"]
        except Exception:
            return json.dumps(js, ensure_ascii=False)


class LLMClient:
    """Universal LLM client wrapper for SEED Agent v4"""
    
    def __init__(self, config):
        self.config = config
        self.gigachat = None
        self.enabled = False
        
        import logging
        logger = logging.getLogger(__name__)
        
        # Initialize GigaChat client with config values
        llm_cfg = config.get("llm", {}) or {}
        llm_enabled = llm_cfg.get("enabled", True)
        if llm_enabled:
            # Set environment variables from config BEFORE creating GigaChat
            gigachat_config = llm_cfg.get("gigachat", {}) or {}
            
            required = ["client_id", "client_secret", "oauth_url", "api_url"]
            if gigachat_config and all(gigachat_config.get(k) for k in required):
                import os
                
                # Store original env vars to restore later if needed
                original_env = {
                    "GIGACHAT_CLIENT_ID": os.environ.get("GIGACHAT_CLIENT_ID"),
                    "GIGACHAT_CLIENT_SECRET": os.environ.get("GIGACHAT_CLIENT_SECRET"),
                    "GIGACHAT_SCOPE": os.environ.get("GIGACHAT_SCOPE"),
                    "GIGACHAT_OAUTH_URL": os.environ.get("GIGACHAT_OAUTH_URL"),
                    "GIGACHAT_API_URL": os.environ.get("GIGACHAT_API_URL"),
                    "GIGACHAT_MODEL": os.environ.get("GIGACHAT_MODEL"),
                    "GIGACHAT_VERIFY_SSL": os.environ.get("GIGACHAT_VERIFY_SSL"),
                    "GIGACHAT_TOKEN_CACHE": os.environ.get("GIGACHAT_TOKEN_CACHE")
                }
                
                # Log config values before setting env vars
                mask = lambda s: (s[:4] + "…" + s[-4:]) if s and len(s) > 8 else "SET" if s else "EMPTY"
                logger.info(f"📊 LLM config values:")
                logger.info(f"   client_id: {mask(gigachat_config.get('client_id'))}")
                logger.info(f"   client_secret: {mask(gigachat_config.get('client_secret'))}")
                logger.info(f"   oauth_url: {'SET' if gigachat_config.get('oauth_url') else 'EMPTY'}")
                logger.info(f"   api_url: {'SET' if gigachat_config.get('api_url') else 'EMPTY'}")
                logger.info(f"   verify_ssl: {gigachat_config.get('verify_ssl', False)}")
                
                # Set config values to environment
                os.environ["GIGACHAT_CLIENT_ID"] = gigachat_config.get("client_id", "")
                os.environ["GIGACHAT_CLIENT_SECRET"] = gigachat_config.get("client_secret", "")
                os.environ["GIGACHAT_SCOPE"] = gigachat_config.get("scope", "GIGACHAT_API_PERS")
                os.environ["GIGACHAT_OAUTH_URL"] = gigachat_config.get("oauth_url", "")
                os.environ["GIGACHAT_API_URL"] = gigachat_config.get("api_url", "")
                os.environ["GIGACHAT_MODEL"] = gigachat_config.get("model", "GigaChat-2")
                os.environ["GIGACHAT_VERIFY_SSL"] = "1" if gigachat_config.get("verify_ssl", False) else "0"
                os.environ["GIGACHAT_TOKEN_CACHE"] = gigachat_config.get("token_cache", "/tmp/gigachat_token.json")
                
                # Now create GigaChat with env vars set
                try:
                    self.gigachat = GigaChat()
                    self.enabled = self.gigachat.enabled
                    if self.enabled:
                        logger.info("✅ GigaChat LLM client initialized successfully")
                    else:
                        logger.warning("⚠️ GigaChat created but not enabled - check credentials")
                except Exception as e:
                    logger.error(f"❌ Failed to initialize GigaChat: {e}")
                    self.gigachat = None
                    self.enabled = False
            else:
                missing = [k for k in required if not gigachat_config.get(k)]
                if missing:
                    logger.warning(f"⚠️ GigaChat config missing/empty keys: {', '.join(missing)} - LLM disabled")
                else:
                    logger.warning(f"⚠️ GigaChat config section not found or empty - LLM disabled")
        else:
            logger.info("ℹ️ LLM disabled in configuration")
            
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
