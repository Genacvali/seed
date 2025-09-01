# -*- coding: utf-8 -*-
import os, json, time, base64, uuid, requests
from typing import Optional
from core.config import CFG
from core.log import get_logger

log = get_logger("llm")

class GigaChat:
    def __init__(self):
        self.client_id = CFG.gc_client_id
        self.client_secret = CFG.gc_client_secret
        self.scope = CFG.gc_scope
        self.oauth_url = CFG.gc_oauth_url
        self.api_url = CFG.gc_api_url
        self.model = CFG.gc_model
        self.verify_ssl = CFG.gc_verify_ssl
        self.cache_path = CFG.gc_token_cache

    def _load_token(self) -> Optional[str]:
        try:
            with open(self.cache_path, "r", encoding="utf-8") as f:
                obj = json.load(f)
            if obj.get("expires_at", 0) > int(time.time() * 1000) + 5000:
                return obj.get("access_token")
        except Exception:
            pass
        return None

    def _save_token(self, token: str, expires_at: int) -> None:
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump({"access_token": token, "expires_at": expires_at}, f)
        except Exception:
            pass

    def _get_token(self) -> str:
        t = self._load_token()
        if t:
            return t

        if not (self.client_id and self.client_secret and self.oauth_url):
            raise RuntimeError("GigaChat OAuth not configured")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json",
            "Authorization": "Basic " + base64.b64encode(
                (self.client_id + ":" + self.client_secret).encode("utf-8")
            ).decode("utf-8"),
            "RqUID": str(uuid.uuid4()),
        }
        data = {"scope": self.scope}
        r = requests.post(self.oauth_url, headers=headers, data=data, timeout=15, verify=self.verify_ssl)
        r.raise_for_status()
        obj = r.json()
        token = obj["access_token"]
        expires_at = int(obj.get("expires_at", int(time.time() * 1000) + 50 * 60 * 1000))
        self._save_token(token, expires_at)
        return token

    def ask(self, prompt: str, max_tokens: int = 120) -> str:
        token = self._get_token()
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "Ты кратко и по делу советуешь SRE/DBA по метрикам и алертам."},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": max_tokens,
            "temperature": 0.2,
        }
        r = requests.post(CFG.gc_api_url, json=payload, headers=headers, timeout=30, verify=self.verify_ssl)
        if r.status_code == 401:
            # refresh token and retry
            token = self._get_token()  # will refresh
            headers["Authorization"] = f"Bearer {token}"
            r = requests.post(CFG.gc_api_url, json=payload, headers=headers, timeout=30, verify=self.verify_ssl)

        r.raise_for_status()
        j = r.json()
        try:
            return j["choices"][0]["message"]["content"]
        except Exception:
            return ""