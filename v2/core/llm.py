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
        headers = {
            "Content-Type":"application/x-www-form-urlencoded",
            "Accept":"application/json",
            "RqUID": str(uuid.uuid4()),
            "Authorization": "Basic " + f"{CID}:{CSEC}".encode("utf-8").decode("utf-8")
        }
        # В некоторых инсталляциях Basic не требует base64; если нужно — раскомментируй:
        # import base64; headers["Authorization"] = "Basic " + base64.b64encode(f"{CID}:{CSEC}".encode()).decode()
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
