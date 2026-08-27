#!/usr/bin/env python3
"""Pull all top-level comments from a YouTube video via Data API v3.

Usage:
    export YT_API_KEY="your-key"
    python3 yt_comments.py VIDEO_ID output.txt
"""

import os
import sys
import time

import requests

API_URL = "https://www.googleapis.com/youtube/v3/commentThreads"


def fetch_comments(video_id: str, api_key: str) -> list[str]:
    comments = []
    page_token = None

    while True:
        params = {
            "part": "snippet",
            "videoId": video_id,
            "key": api_key,
            "maxResults": 100,
            "textFormat": "plainText",
        }
        if page_token:
            params["pageToken"] = page_token

        resp = requests.get(API_URL, params=params, timeout=30)
        if resp.status_code != 200:
            print(f"API error {resp.status_code}: {resp.text[:300]}", file=sys.stderr)
            sys.exit(1)

        data = resp.json()
        for item in data.get("items", []):
            text = item["snippet"]["topLevelComment"]["snippet"]["textDisplay"]
            comments.append(text.replace("\n", " ").strip())

        page_token = data.get("nextPageToken")
        print(f"  {len(comments)} comments so far...", file=sys.stderr)
        if not page_token:
            break
        time.sleep(0.1)  # polite pacing

    return comments


def main():
    if len(sys.argv) != 3:
        print(__doc__, file=sys.stderr)
        sys.exit(1)

    video_id, out_path = sys.argv[1], sys.argv[2]
    api_key = os.environ.get("YT_API_KEY")
    if not api_key:
        print("Set YT_API_KEY environment variable first.", file=sys.stderr)
        sys.exit(1)

    comments = fetch_comments(video_id, api_key)

    with open(out_path, "w", encoding="utf-8") as f:
        for i, c in enumerate(comments, 1):
            f.write(f"{i}. {c}\n")

    print(f"Saved {len(comments)} comments to {out_path}")


if __name__ == "__main__":
    main()
