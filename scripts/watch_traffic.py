#!/usr/bin/env python3
"""
AvaScry Live Terminal Traffic Watcher & 404 Radar
Monitors live web traffic, crawler classification (Google, Bing, AI), status codes, latency, and image cache size.
"""

import os
import sys
import re
import time
import glob
import threading
from datetime import datetime, timezone
from collections import deque, defaultdict

LOG_FILE = "logs/access.log"

# Regex parser for log line:
# 2026-08-31T14:02:09.123456+00:00 81.171.72.135    [User:NL]       405 (   0ms) -> POST /
LOG_REGEX = re.compile(
    r'^(?P<ts>\S+)\s+(?P<ip>\S+)\s+(?P<badge>\[[^\]]+\])\s+(?P<status>\d{3})\s+\(\s*(?P<lat>\d+)ms\)\s+->\s+(?P<method>\S+)\s+(?P<path>\S+)'
)

# Global Image Cache Stats (updated asynchronously)
IMAGE_STATS = {
    "normal_count": 0, "normal_mb": 0.0,
    "large_count": 0, "large_mb": 0.0,
    "total_count": 0, "total_mb": 0.0,
    "last_check": "Checking..."
}

def update_image_cache_stats_worker():
    """Background worker to check image cache size without blocking live log processing."""
    while True:
        try:
            normal_files = glob.glob("public/images/normal/**/*", recursive=True)
            large_files = glob.glob("public/images/large/**/*", recursive=True)
            
            normal_files = [f for f in normal_files if os.path.isfile(f)]
            large_files = [f for f in large_files if os.path.isfile(f)]
            
            n_size = sum(os.path.getsize(f) for f in normal_files) / (1024 * 1024)
            l_size = sum(os.path.getsize(f) for f in large_files) / (1024 * 1024)
            
            IMAGE_STATS["normal_count"] = len(normal_files)
            IMAGE_STATS["normal_mb"] = n_size
            IMAGE_STATS["large_count"] = len(large_files)
            IMAGE_STATS["large_mb"] = l_size
            IMAGE_STATS["total_count"] = len(normal_files) + len(large_files)
            IMAGE_STATS["total_mb"] = n_size + l_size
            IMAGE_STATS["last_check"] = datetime.now().strftime("%H:%M:%S")
        except Exception:
            pass
        time.sleep(30)

def classify_badge(badge: str) -> str:
    b = badge.lower()
    if "googlebot" in b:
        return "google"
    if "bingbot" in b:
        return "bing"
    if any(ai in b for ai in ("ai:claude", "ai:openai", "ai:perplexity", "ai:bytedance", "perplexity", "claude", "gpt", "bytespider")):
        return "ai"
    if "shield" in b:
        return "shield"
    if "user" in b:
        return "human"
    return "other"

def percentile(values, p):
    if not values:
        return 0
    k = (len(values) - 1) * p
    f = int(k)
    c = min(f + 1, len(values) - 1)
    d = k - f
    return values[f] + d * (values[c] - values[f])

class TrafficTracker:
    def __init__(self):
        self.total_reqs = 0
        self.cat_counts = defaultdict(int)
        self.status_counts = defaultdict(int)
        self.all_latencies = []
        self.all_404s = {} # path -> {"count": int, "last_seen": str, "last_ip": str, "last_badge": str}
        
        # 5-minute sliding window queue: (timestamp_float, cat, status, latency)
        self.window_5m = deque()

    def add_request(self, dt: datetime, cat: str, status: int, lat: int, path: str, ip: str, badge: str):
        now_epoch = dt.timestamp()
        
        # Total aggregates
        self.total_reqs += 1
        self.cat_counts[cat] += 1
        self.status_counts[status] += 1
        self.all_latencies.append(lat)
        
        # 404 Radar tracking
        if status == 404:
            clean_path = path.split("?")[0]
            if clean_path not in self.all_404s:
                self.all_404s[clean_path] = {
                    "count": 0,
                    "first_seen": dt.strftime("%H:%M:%S"),
                    "last_seen": dt.strftime("%H:%M:%S"),
                    "last_ip": ip,
                    "last_badge": badge
                }
            self.all_404s[clean_path]["count"] += 1
            self.all_404s[clean_path]["last_seen"] = dt.strftime("%H:%M:%S")

        # Sliding window
        self.window_5m.append((now_epoch, cat, status, lat))

    def prune_5m(self, current_epoch: float):
        cutoff = current_epoch - 300.0 # 5 minutes
        while self.window_5m and self.window_5m[0][0] < cutoff:
            self.window_5m.popleft()

    def get_5m_stats(self):
        cat_5m = defaultdict(int)
        status_5m = defaultdict(int)
        lats_5m = []
        
        for _, cat, status, lat in self.window_5m:
            cat_5m[cat] += 1
            status_5m[status] += 1
            lats_5m.append(lat)
            
        total_5m = len(self.window_5m)
        lats_5m.sort()
        p50 = percentile(lats_5m, 0.50) if lats_5m else 0
        p95 = percentile(lats_5m, 0.95) if lats_5m else 0
        
        return total_5m, cat_5m, status_5m, p50, p95

    def get_all_stats(self):
        sorted_lats = sorted(self.all_latencies)
        p50 = percentile(sorted_lats, 0.50) if sorted_lats else 0
        p95 = percentile(sorted_lats, 0.95) if sorted_lats else 0
        return self.total_reqs, self.cat_counts, self.status_counts, p50, p95

def render_dashboard(tracker: TrafficTracker):
    now_epoch = time.time()
    tracker.prune_5m(now_epoch)
    
    tot_5m, cat_5m, st_5m, p50_5m, p95_5m = tracker.get_5m_stats()
    tot_all, cat_all, st_all, p50_all, p95_all = tracker.get_all_stats()

    # ANSI Colors
    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"

    def pct(val, total):
        return f"{val/total*100:5.1f}%" if total > 0 else "  0.0%"

    def st_sum(st_dict, prefix):
        return sum(v for k, v in st_dict.items() if str(k).startswith(prefix))

    output = []
    output.append(f"{CYAN}{BOLD}================================================================================{RESET}")
    output.append(f"{CYAN}{BOLD}                    🔮 AVASCRY LIVE TRAFFIC WATCHER & 404 RADAR                {RESET}")
    output.append(f"{CYAN}{BOLD}================================================================================{RESET}")
    output.append(f"  {BOLD}{'METRIC':<24} {'LAST 5 MIN':<26} {'SINCE STARTUP':<26}{RESET}")
    output.append(f"  {'-'*24} {'-'*26} {'-'*26}")
    
    # Request Counts
    output.append(f"  {'Total Requests':<24} {tot_5m:<8}                    {tot_all:<8}")
    output.append(f"  {GREEN}{'🟢 Googlebot':<24}{RESET} {cat_5m['google']:<6} ({pct(cat_5m['google'], tot_5m)})           {cat_all['google']:<6} ({pct(cat_all['google'], tot_all)})")
    output.append(f"  {BLUE}{'🔵 Bingbot':<24}{RESET} {cat_5m['bing']:<6} ({pct(cat_5m['bing'], tot_5m)})           {cat_all['bing']:<6} ({pct(cat_all['bing'], tot_all)})")
    output.append(f"  {YELLOW}{'🤖 AI Crawlers':<24}{RESET} {cat_5m['ai']:<6} ({pct(cat_5m['ai'], tot_5m)})           {cat_all['ai']:<6} ({pct(cat_all['ai'], tot_all)})")
    output.append(f"  {'👤 Humans / Users':<24} {cat_5m['human']:<6} ({pct(cat_5m['human'], tot_5m)})           {cat_all['human']:<6} ({pct(cat_all['human'], tot_all)})")
    output.append(f"  {'🛡️ Blocked Probes':<24} {cat_5m['shield']:<6}                          {cat_all['shield']:<6}")
    output.append("")

    # Status Codes
    st200_5m = st_5m[200]
    st200_all = st_all[200]
    st3xx_5m = st_sum(st_5m, "3")
    st3xx_all = st_sum(st_all, "3")
    st404_5m = st_5m[404]
    st404_all = st_all[404]
    st5xx_5m = st_sum(st_5m, "5")
    st5xx_all = st_sum(st_all, "5")

    output.append(f"  {BOLD}HTTP Status Codes:{RESET}")
    output.append(f"  {GREEN}{'  200 OK':<24}{RESET} {st200_5m:<6} ({pct(st200_5m, tot_5m)})           {st200_all:<6} ({pct(st200_all, tot_all)})")
    output.append(f"  {'  3xx Redirect':<24} {st3xx_5m:<6} ({pct(st3xx_5m, tot_5m)})           {st3xx_all:<6} ({pct(st3xx_all, tot_all)})")
    
    col404 = RED if st404_all > 0 else RESET
    output.append(f"  {col404}{'  404 Not Found':<24} {st404_5m:<6} ({pct(st404_5m, tot_5m)})           {st404_all:<6} ({pct(st404_all, tot_all)}){RESET}")
    
    col5xx = RED if st5xx_all > 0 else RESET
    output.append(f"  {col5xx}{'  5xx Server Errors':<24} {st5xx_5m:<6} ({pct(st5xx_5m, tot_5m)})           {st5xx_all:<6} ({pct(st5xx_all, tot_all)}){RESET}")
    output.append("")

    # Latency
    output.append(f"  {BOLD}⚡ Latency (Speed):{RESET}")
    output.append(f"  {'  p50 (Typical)':<24} {p50_5m:>4.0f}ms                      {p50_all:>4.0f}ms")
    output.append(f"  {'  p95 (Slowest 5%)':<24} {p95_5m:>4.0f}ms                      {p95_all:>4.0f}ms")

    # Image Disk Cache Stats
    output.append(f"{CYAN}--------------------------------------------------------------------------------{RESET}")
    n_cnt = IMAGE_STATS["normal_count"]
    n_gb = IMAGE_STATS["normal_mb"] / 1024
    l_cnt = IMAGE_STATS["large_count"]
    l_gb = IMAGE_STATS["large_mb"] / 1024
    t_cnt = IMAGE_STATS["total_count"]
    t_gb = IMAGE_STATS["total_mb"] / 1024
    
    output.append(f"  {BOLD}🖼️ IMAGE DISK CACHE:{RESET}  Normal: {n_cnt:,} ({n_gb:.2f} GB) | Large: {l_cnt:,} ({l_gb:.2f} GB)")
    output.append(f"  Total on Disk: {BOLD}{t_cnt:,} files ({t_gb:.2f} GB){RESET}  [Last Checked: {IMAGE_STATS['last_check']}]")

    # 404 Radar (Uncapped List All)
    output.append(f"{CYAN}--------------------------------------------------------------------------------{RESET}")
    output.append(f"  {BOLD}🚨 404 RADAR (ALL UNRESOLVED PATHS SINCE STARTUP):{RESET}")
    
    if not tracker.all_404s:
        output.append(f"  {GREEN}✓ Clean sheet! Zero 404 errors recorded.{RESET}")
    else:
        for p, data in sorted(tracker.all_404s.items(), key=lambda x: x[1]["count"], reverse=True):
            output.append(f"  {RED}[x{data['count']}] {p:<50} (Last: {data['last_seen']} by {data['last_badge']}){RESET}")

    output.append(f"{CYAN}================================================================================{RESET}")
    output.append(f"  Watching {LOG_FILE}... (Press Ctrl+C to stop)")

    # Clear terminal screen and print
    sys.stdout.write("\033[H\033[J" + "\n".join(output) + "\n")
    sys.stdout.flush()

def tail_log_file(tracker: TrafficTracker):
    """Continuously tail and parse logs/access.log."""
    while not os.path.exists(LOG_FILE):
        time.sleep(1)

    with open(LOG_FILE, "r", encoding="utf-8", errors="ignore") as f:
        # First read any existing lines from previous runs
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = LOG_REGEX.match(line)
            if m:
                try:
                    ts = datetime.fromisoformat(m.group("ts"))
                except Exception:
                    ts = datetime.now(timezone.utc)
                ip = m.group("ip")
                badge = m.group("badge")
                status = int(m.group("status"))
                lat = int(m.group("lat"))
                method = m.group("method")
                path = m.group("path")
                cat = classify_badge(badge)
                tracker.add_request(ts, cat, status, lat, path, ip, badge)

        # Now follow new incoming lines in real time
        while True:
            line = f.readline()
            if line:
                line = line.strip()
                if line:
                    m = LOG_REGEX.match(line)
                    if m:
                        try:
                            ts = datetime.fromisoformat(m.group("ts"))
                        except Exception:
                            ts = datetime.now(timezone.utc)
                        ip = m.group("ip")
                        badge = m.group("badge")
                        status = int(m.group("status"))
                        lat = int(m.group("lat"))
                        method = m.group("method")
                        path = m.group("path")
                        cat = classify_badge(badge)
                        tracker.add_request(ts, cat, status, lat, path, ip, badge)
            else:
                time.sleep(0.1)

def main():
    tracker = TrafficTracker()
    
    # Start background cache size worker
    t_cache = threading.Thread(target=update_image_cache_stats_worker, daemon=True)
    t_cache.start()
    
    # Start background log tailer
    t_log = threading.Thread(target=tail_log_file, args=(tracker,), daemon=True)
    t_log.start()

    try:
        while True:
            render_dashboard(tracker)
            time.sleep(1.5)
    except KeyboardInterrupt:
        print("\nTraffic watcher stopped.")

if __name__ == "__main__":
    main()
