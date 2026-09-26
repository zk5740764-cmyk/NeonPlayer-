#!/usr/bin/env python3
"""
fetch_videos.py
Scrapes YouTube via yt-dlp and writes ONE JSON file PER CATEGORY under
categories/, e.g. categories/home.json, categories/bollywood.json,
categories/bollywood_movies.json, etc. — instead of the old two combined
videos.json / movies.json files.

Also writes categories/manifest.json: a small index of every category name,
whether it's a "song" or "movie" category, and its file path — so the app
side can list/loop over categories without hardcoding each filename.

Each category file is a flat JSON array, same item shape as before (each
item still carries its own "category" field, kept for backward
compatibility with any code still checking it).
"""

import json
import os
import subprocess
import sys
from datetime import datetime, timezone

# ---- CONFIG -----------------------------------------------------------
# Bumped counts significantly for real volume per category — each ytsearchN
# query costs more CI time but the Action just runs on a schedule, not on
# any user-facing critical path.

SONG_CATEGORIES = {
    "home": [
        "ytsearch40:entertainment videos 2026",
        "ytsearch30:lifestyle vlog",
        "ytsearch30:travel vlog",
        "ytsearch30:tech review 2026",
        "ytsearch30:cooking recipe",
        "ytsearch20:motivational video",
        "ytsearch20:documentary",
        "ytsearch20:podcast interview",
    ],
    "bollywood": [
        "ytsearch50:new bollywood songs 2026",
        "ytsearch50:bollywood romantic songs",
        "ytsearch40:bollywood item songs",
        "ytsearch40:bollywood sad songs",
        "ytsearch30:bollywood old songs",
        "ytsearch30:bollywood party songs",
    ],
    "punjabi": [
        "ytsearch50:new punjabi songs 2026",
        "ytsearch40:punjabi bhangra songs",
        "ytsearch30:punjabi sad songs",
        "ytsearch30:punjabi romantic songs",
    ],
    "kashmiri_gojri": [
        "ytsearch30:new kashmiri songs",
        "ytsearch30:gojri songs",
        "ytsearch20:kashmiri old songs",
    ],
    "urdu_hindi": [
        "ytsearch30:hindi sad songs",
        "ytsearch30:urdu ghazal songs",
        "ytsearch20:hindi romantic songs",
        "ytsearch20:urdu sad poetry songs",
    ],
    "english": [
        "ytsearch40:new english songs 2026",
        "ytsearch30:english pop hits",
        "ytsearch20:english romantic songs",
    ],
    "lofi_chill": [
        "ytsearch30:lofi songs mix",
        "ytsearch20:chill relaxing music",
    ],
}

MOVIE_CATEGORIES = {
    "bollywood_movies": [
        "ytsearch30:bollywood full movie 2026",
        "ytsearch30:bollywood movie trailer 2026",
        "ytsearch20:bollywood full movie hindi",
    ],
    "hollywood_movies": [
        "ytsearch30:hollywood movie trailer 2026",
        "ytsearch20:hollywood full movie english",
        "ytsearch20:hollywood movie hindi dubbed",
    ],
    "south_indian_movies": [
        "ytsearch30:south indian movie hindi dubbed",
        "ytsearch20:south indian movie trailer",
    ],
    "punjabi_movies": [
        "ytsearch20:punjabi full movie",
        "ytsearch15:punjabi movie trailer",
    ],
}

OUTPUT_DIR = "categories"

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
            timeout=240,
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
    # One category per call now (see fetch_category below), so the id alone
    # is a unique-enough key — no need to also key on category anymore.
    seen = set()
    out = []
    for v in videos:
        if v["id"] in seen:
            continue
        seen.add(v["id"])
        out.append(v)
    return out


def fetch_category(category: str, queries: list) -> list:
    print(f"[INFO] fetching category: {category}")
    collected = []
    for q in queries:
        collected.extend(fetch_query(q, category))
    deduped = dedupe(collected)
    print(f"[INFO]   -> {len(deduped)} videos")
    return deduped


def write_category_file(category: str, videos: list):
    path = os.path.join(OUTPUT_DIR, f"{category}.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(videos, f, ensure_ascii=False, indent=2)
    print(f"[DONE] wrote {path} — {len(videos)} videos")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    manifest_categories = []

    for category, queries in SONG_CATEGORIES.items():
        videos = fetch_category(category, queries)
        write_category_file(category, videos)
        manifest_categories.append({
            "name": category,
            "type": "song",
            "file": f"{category}.json",
            "count": len(videos),
        })

    for category, queries in MOVIE_CATEGORIES.items():
        videos = fetch_category(category, queries)
        write_category_file(category, videos)
        manifest_categories.append({
            "name": category,
            "type": "movie",
            "file": f"{category}.json",
            "count": len(videos),
        })

    manifest = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "categories": manifest_categories,
    }
    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    print(f"[DONE] wrote {manifest_path} — {len(manifest_categories)} categories")


if __name__ == "__main__":
    main()
  
