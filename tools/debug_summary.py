"""Summarize a debug capture log: count each distinct D3D12/DXGI message and show
every ERROR / CORRUPTION message (with its first and last time).

Usage: python debug_summary.py <debug_*.log>
"""
import re
import sys
from collections import OrderedDict

KIND = re.compile(r"(D3D12|DXGI) (ERROR|WARNING|CORRUPTION|INFO|MESSAGE)")
ID = re.compile(r"\[ *[A-Z ]+(ERROR|WARNING|CORRUPTION|INFO|MESSAGE) #(\d+):")


def main():
    stats = OrderedDict()
    other = 0
    for line in open(sys.argv[1], encoding="utf-8", errors="replace"):
        if "<<" not in line:
            continue
        time = line[:12]
        msg = line.split("<<", 1)[1].strip()
        k = KIND.search(msg)
        if not k:
            other += 1
            key = ("OTHER", msg[:90])
        else:
            i = ID.search(msg)
            key = (f"{k.group(1)} {k.group(2)}", i.group(2) if i else msg[:90])
        s = stats.setdefault(key, {"n": 0, "first": time, "last": time, "text": msg})
        s["n"] += 1
        s["last"] = time
    print(f"{sum(s['n'] for s in stats.values())} game messages, {len(stats)} distinct")
    for (kind, ident), s in sorted(stats.items(), key=lambda kv: (-("ERROR" in kv[0][0] or "CORRUPTION" in kv[0][0]), -kv[1]["n"])):
        flag = "!!" if ("ERROR" in kind or "CORRUPTION" in kind) else "  "
        print(f"{flag} {s['n']:7d}x  {s['first']}..{s['last']}  {kind} #{ident}: {s['text'][:230]}")


if __name__ == "__main__":
    main()
