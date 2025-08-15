# plugins/host_inventory.py
# -*- coding: utf-8 -*-
"""
SEED plugin: host_inventory
Короткий «паспорт» сервера без внешних библиотек.
"""

import os, socket, platform, time, shutil

def _read_os_release():
    p = "/etc/os-release"
    if not os.path.exists(p):
        return "-"
    data = {}
    with open(p, "r", encoding="utf-8") as f:
        for line in f:
            if "=" in line:
                k, v = line.strip().split("=", 1)
                data[k] = v.strip('"')
    name = data.get("PRETTY_NAME") or (data.get("NAME","") + " " + data.get("VERSION",""))
    return name or "-"

def _uptime_human():
    try:
        with open("/proc/uptime","r") as f:
            secs = float(f.read().split()[0])
        days  = int(secs // 86400); secs %= 86400
        hours = int(secs // 3600);  secs %= 3600
        mins  = int(secs // 60)
        return f"{days}d {hours}h {mins}m"
    except Exception:
        return "-"

def _mem_info():
    mi = {}
    try:
        with open("/proc/meminfo","r") as f:
            for line in f:
                k, v, *_ = line.split()
                mi[k] = int(v)  # в кБ
        total = mi.get("MemTotal", 0) * 1024
        avail = mi.get("MemAvailable", 0) * 1024
        used  = total - avail
        return total, used, avail
    except Exception:
        return 0, 0, 0

def _fmt_bytes(n):
    if n is None: return "-"
    for unit in ("B","KB","MB","GB","TB"):
        if n < 1024: return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} PB"

def run(host: str, payload: dict) -> str:
    fqdn   = socket.getfqdn() or host
    osver  = _read_os_release()
    kern   = platform.release()
    arch   = platform.machine()
    up     = _uptime_human()

    # диски: корень и /data, если есть
    parts = [("/", "root")]
    if os.path.ismount("/data"):
        parts.append(("/data", "data"))

    disk_lines = []
    for mp, name in parts:
        try:
            du = shutil.disk_usage(mp)
            used_pct = 0 if du.total == 0 else int(du.used * 100 / du.total)
            disk_lines.append(f"- `{mp}`: {used_pct}% ({_fmt_bytes(du.used)} / {_fmt_bytes(du.total)})")
        except Exception:
            disk_lines.append(f"- `{mp}`: n/a")

    mtot, muse, mavail = _mem_info()
    mem_line = f"RAM: {_fmt_bytes(muse)} / {_fmt_bytes(mtot)} (free {_fmt_bytes(mavail)})" if mtot else "RAM: n/a"

    lines = []
    lines.append(f"### SEED · Профиль хоста `{fqdn}`")
    lines.append(f"• OS: **{osver}**  • Kernel: `{kern}`  • Arch: `{arch}`")
    lines.append(f"• Uptime: {up}")
    lines.append(mem_line)
    lines.append("**Диски:**")
    lines += disk_lines

    # необязательная мини-подсказка
    try:
        use_llm = os.getenv("USE_LLM","0") == "1"
        if use_llm:
            from core.llm import GigaChat
            tip = GigaChat().ask(
                "Дай одну короткую рекомендацию по базовой гигиене Linux-хоста (ресурсы, логи, автозапуски). Не более 2 предложений.",
                max_tokens=120
            )
            if tip:
                lines.append("\n**LLM совет:** " + tip.strip())
    except Exception as e:
        lines.append(f"\n_(LLM недоступен: {e})_")

    return "\n".join(lines)