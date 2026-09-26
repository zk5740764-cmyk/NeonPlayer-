#!/usr/bin/env python3
"""
fetch_videos.py
Scrapes YouTube via yt-dlp and writes TWO separate JSON files at repo root:
  - videos.json  -> Home + all song/language categories
  - movies.json  -> movie categories only
Both are flat arrays, each item carrying its own "category" field (matches
RemoteFeedRepository.kt / RemoteMoviesRepository.kt on the Kotlin side).
"""

import json
import subprocess
import sys

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
    seen = set()
    out = []
    for v in videos:
        key = (v["id"], v["category"])
        if key in seen:
            continue
        seen.add(key)
        out.append(v)
    return out


def fetch_all(categories: dict) -> list:
    all_videos = []
    for category, queries in categories.items():
        print(f"[INFO] fetching category: {category}")
        collected = []
        for q in queries:
            collected.extend(fetch_query(q, category))
        print(f"[INFO]   -> {len(collected)} videos")
        all_videos.extend(collected)
    return dedupe(all_videos)


def main():
    songs = fetch_all(SONG_CATEGORIES)
    with open("videos.json", "w", encoding="utf-8") as f:
        json.dump(songs, f, ensure_ascii=False, indent=2)
    print(f"[DONE] wrote videos.json — {len(songs)} total videos")

    movies = fetch_all(MOVIE_CATEGORIES)
    with open("movies.json", "w", encoding="utf-8") as f:
        json.dump(movies, f, ensure_ascii=False, indent=2)
    print(f"[DONE] wrote movies.json — {len(movies)} total videos")


if __name__ == "__main__":
    main()
    
