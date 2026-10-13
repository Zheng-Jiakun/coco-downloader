"""Check a running Web build against real providers and audio prefixes."""
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import sys
from urllib.parse import urlparse

import requests

BASE = "http://127.0.0.1:3210"
PROVIDERS = ["netease", "qq", "kugou", "gequhai", "bodian", "qqmp3", "migu", "livepoo",
             "jianbin-netease", "jianbin-qq", "jianbin-kugou", "jianbin-kuwo"]


def probe(name):
    result = {"provider": name, "samples": []}
    with requests.Session() as session:
        session.trust_env = False
        try:
            response = session.get(BASE + "/api/search", params={"provider": name, "q": "晴天", "limit": 5}, timeout=70)
            result["search_status"] = response.status_code
            payload = response.json()
            items = payload.get("items", [])
            result["search_count"] = len(items)
            if payload.get("error"):
                result["error"] = payload["error"]
            for item in items[:2]:
                sample = {"title": item["title"], "artist": item["artist"]}
                result["samples"].append(sample)
                info = session.get(BASE + "/api/url", params={"provider": name, "id": item["id"],
                    "extra": json.dumps({**item.get("extra", {}), "usage": "playback"})}, timeout=70)
                sample["resolve_status"] = info.status_code
                data = info.json()
                if not data.get("url"):
                    sample["error"] = data.get("error", "Missing audio url")
                    continue
                with session.get(data["url"], headers={"Range": "bytes=0-4095", "User-Agent": "Mozilla/5.0"}, stream=True, timeout=15) as audio:
                    prefix = next(audio.iter_content(4096), b"")
                    sample.update(host=urlparse(audio.url).hostname, audio_status=audio.status_code,
                                  content_type=audio.headers.get("Content-Type"), prefix_hex=prefix[:16].hex(),
                                  audio_verified=audio.ok and (prefix.startswith((b"ID3", b"fLaC", b"RIFF", b"OggS")) or prefix[4:8] == b"ftyp" or (len(prefix)>1 and prefix[0] == 255 and prefix[1] & 0xE0 == 0xE0)))
                if name.startswith("jianbin") and item.get("cover"):
                    cover = session.get(BASE + item["cover"], timeout=30)
                    sample["cover_verified"] = cover.ok and cover.headers.get("Content-Type", "").startswith("image/")
        except Exception as error:
            result["error"] = str(error)
    return result


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    results = []
    with ThreadPoolExecutor(max_workers=4) as pool:
        for future in as_completed([pool.submit(probe, name) for name in PROVIDERS]):
            result = future.result()
            results.append(result)
            print(json.dumps(result, ensure_ascii=False), flush=True)
    output = Path(__file__).resolve().parents[1] / "diagnostics/web-provider-status-2026-10-11.json"
    output.write_text(json.dumps({"checked_at": datetime.now(timezone(timedelta(hours=8))).isoformat(),
                                 "results": results}, ensure_ascii=False, indent=2), encoding="utf-8")
