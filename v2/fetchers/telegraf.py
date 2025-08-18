# -*- coding: utf-8 -*-
import re, requests
from typing import Dict, Optional, List
from core import config

LABEL_RE = re.compile(r'\{([^}]*)\}')
PAIR_RE  = re.compile(r'(\w+)\s*=\s*"(.*?)"')

def _matches(line: str, labels: Dict[str,str]) -> bool:
    m = LABEL_RE.search(line)
    if not m:
        return not labels
    raw = m.group(1)
    d = dict(PAIR_RE.findall(raw))
    for k,v in labels.items():
        if d.get(k) != str(v):
            return False
    return True

def get_gauge(host: str, metric: str, labels: Optional[Dict[str,str]]=None, telegraf_url: Optional[str]=None) -> Optional[float]:
    url = telegraf_url or config.default_telegraf_url(host)
    try:
        r = requests.get(url, timeout=5, verify=False)
        if r.status_code != 200:
            return None
        val = None
        for line in r.text.splitlines():
            if not line.startswith(metric):
                continue
            if labels and not _matches(line, labels):
                continue
            # Возьмём число справа
            try:
                val = float(line.strip().split()[-1])
                break
            except: pass
        return val
    except:
        return None
