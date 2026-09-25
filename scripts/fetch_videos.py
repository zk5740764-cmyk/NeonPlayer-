#!/usr/bin/env python3
"""
fetch_videos.py
Scrapes YouTube via yt-dlp for all song categories + movies, writes videos.json
at repo root as a FLAT array (matches RemoteVideosSync.kt's List<RemoteVideoDto>,
each item carrying its own "category" field).
"""

import json
import subprocess
import sys

CATEGORIES = {
    "bollywood": [
        "ytsearch20:new bollywood songs 2026",
        "ytsearch20:bollywood romantic songs",
        "ytsearch15:bollywood item songs",
    ],
    "punjabi": [
        "ytsearch20:new punjabi songs 2026",
        "ytsearch15:punjabi bhangra songs",
    ],
    "kashmiri_gojri": [
        "ytsearch15:new kashmiri songs",
        "ytsearch15:gojri songs",
    ],
    "urdu_hindi": [
        "ytsearch15:hindi sad songs",
        "ytsearch15:urdu ghazal songs",
    ],
    "english": [
        "ytsearch20:new english songs 2026",
        "ytsearch15:english pop hits",
    ],
    "lofi_chill": [
        "ytsearch15:lofi songs mix",
    ],
    "bollywood_movies": [
        "ytsearch15:bollywood full movie 2026",
        "ytsearch15:bollywood movie trailer 2026",
    ],
    "hollywood_movies": [
        "ytsearch15:hollywood movie trailer 2026",
        "ytsearch10:hollywood full movie english",
    ],
    "south_indian_movies": [
        "ytsearch15:south indian movie hindi dubbed",
    ],
    "punjabi_movies": [
        "ytsearch10:punjabi full movie",
    ],
}

YTDLP_BASE_ARGS = [
    "yt-dlp",
    "--flat-playlist",
    "--dump-json",
    "--no-warnings",
    "--ignore-errors",
]


def fetch_query(query: str, category: str):
    try:
        proc = subprocess.run(
            YTDLP_BASE_ARGS + [query],
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        print(f"[WARN] timeout: {query}", file=sys.stderr)
        return []

    videos = []
    for line in proc.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue

        vid = data.get("id")
        if not vid:
            continue

        videos.append({
            "id": vid,
            "title": data.get("title", ""),
            "channel": data.get("channel") or data.get("uploader") or "",
            "thumbnail": data.get("thumbnail") or f"https://i.ytimg.com/vi/{vid}/hqdefault.jpg",
            "duration": data.get("duration") or 0,
            "category": category,
        })
    return videos


def dedupe(videos):
    seen = set()
    out = []
    for v in videos:
        key = (v["id"], v["category"])
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def main():
    all_videos = []

    for category, queries in CATEGORIES.items():
        print(f"[INFO] fetching category: {category}")
        collected = []
        for q in queries:
            collected.extend(fetch_query(q, category))
        print(f"[INFO]   -> {len(collected)} videos")
        all_videos.extend(collected)

    all_videos = dedupe(all_videos)

    with open("videos.json", "w", encoding="utf-8") as f:
        json.dump(all_videos, f, ensure_ascii=False, indent=2)

    print(f"[DONE] wrote videos.json — {len(all_videos)} total videos")


if __name__ == "__main__":
    main()
