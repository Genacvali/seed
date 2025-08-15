# -*- coding: utf-8 -*-
import os, json, time, uuid, base64, pathlib, datetime, requests
from dotenv import load_dotenv
load_dotenv()

def _b(v, d=False): 
    return (str(os.getenv(v, "0")).lower() not in ("0","false","no")) if d is False else bool(os.getenv(v, d))

class GigaChat:
    def __init__(self):
        self.client_id  = os.getenv("GIGACHAT_CLIENT_ID","")
        self.client_sec = os.getenv("GIGACHAT_CLIENT_SECRET","")
        self.oauth_url  = os.getenv("GIGACHAT_OAUTH_URL","")
        self.api_url    = os.getenv("GIGACHAT_API_URL","")
        self.scope      = os.getenv("GIGACHAT_SCOPE","GIGACHAT_API_PERS")
        self.model      = os.getenv("GIGACHAT_MODEL","GigaChat-2")
        self.verify     = os.getenv("GIGACHAT_VERIFY_SSL","1") != "0"
        cache = os.getenv("GIGACHAT_TOKEN_CACHE","")
        self.cache = pathlib.Path(cache) if cache else None
        self._tok, self._exp = None, 0
        self._load_cache()

    def _load_cache(self):
        if self.cache and self.cache.exists():
            try:
                js = json.loads(self.cache.read_text())
                self._tok = js.get("access_token"); self._exp = int(js.get("exp",0))
            except: pass

    def _save_cache(self):
        if self.cache:
            try:
                self.cache.parent.mkdir(parents=True, exist_ok=True)
                self.cache.write_text(json.dumps({"access_token": self._tok, "exp": self._exp}))
            except: pass

    def _fetch_token(self):
        raw = f"{self.client_id}:{self.client_sec}"
        b64 = base64.b64encode(raw.encode()).decode()
        hdr = {
            "Accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
            "RqUID": str(uuid.uuid4()),
            "Authorization": f"Basic {b64}",
        }
        r = requests.post(self.oauth_url, headers=hdr, data={"scope": self.scope}, timeout=20, verify=self.verify)
        r.raise_for_status()
        js = r.json()
        self._tok = js.get("access_token")
        exp = js.get("expires_at")
        now = int(time.time())
        if exp is None: self._exp = now + 20*60
        else:
            try:
                v = float(exp); self._exp = int(v/1000 if v > 1e12 else v)
            except: self._exp = now + 20*60
        self._save_cache()

    def _ensure(self):
        now = int(time.time())
        if self._tok and (self._exp == 0 or self._exp - now > 60):
            return
        self._fetch_token()

    def ask(self, prompt: str, system="Ты краткий SRE/DBA помощник.", max_tokens=256, temperature=0.2) -> str:
        self._ensure()
        hdr = {
            "Authorization": f"Bearer {self._tok}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.model,
            "messages": [{"role":"system","content":system},{"role":"user","content":prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": False
        }
        r = requests.post(self.api_url, headers=hdr, json=body, timeout=30, verify=self.verify)
        if r.status_code == 401:
            self._fetch_token()
            hdr["Authorization"] = f"Bearer {self._tok}"
            r = requests.post(self.api_url, headers=hdr, json=body, timeout=30, verify=self.verify)
        r.raise_for_status()
        js = r.json()
        return (js.get("choices") or [{}])[0].get("message",{}).get("content","").strip()