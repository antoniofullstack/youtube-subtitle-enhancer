import re
import json
import asyncio
import tempfile
import os
from typing import Any

import httpx

from app.models import SubtitleSegment, WordTimestamp

INVIDIOUS_INSTANCES = [
    "https://inv.thepixora.com",
    "https://inv.nadeko.net",
    "https://invidious.nerdvpn.de",
    "https://yt.chocolatemoo53.com",
]

SUBTITLE_LANGS = ['en', 'pt', 'pt-BR', 'es', 'fr', 'de']

BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)


def extract_video_id(url: str) -> str:
    patterns = [
        r'(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from: {url}")


async def fetch_video_info(url: str) -> dict[str, Any]:
    video_id = extract_video_id(url)

    # Try noembed first (fast, reliable, not blocked)
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(
                f"https://noembed.com/embed?url=https://www.youtube.com/watch?v={video_id}"
            )
            if r.status_code == 200:
                data = r.json()
                title = data.get("title", "")
                if title:
                    return {
                        "video_id": video_id,
                        "title": title,
                        "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
                        "duration": 0.0,
                    }
    except Exception:
        pass

    # Fallback to yt-dlp for info
    try:
        info = await asyncio.to_thread(_get_video_info_sync, video_id)
        return info
    except Exception:
        return {
            "video_id": video_id,
            "title": "YouTube Video",
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "duration": 0.0,
        }


def _get_video_info_sync(video_id: str) -> dict[str, Any]:
    import yt_dlp
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'skip_download': True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(
            f"https://www.youtube.com/watch?v={video_id}",
            download=False,
        )
        return {
            "video_id": video_id,
            "title": info.get("title", "Unknown"),
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "duration": float(info.get("duration", 0)),
        }


async def fetch_subtitles(url: str) -> list[SubtitleSegment]:
    video_id = extract_video_id(url)

    # Method 1: yt-dlp
    segments = await asyncio.to_thread(_fetch_subtitles_yt_dlp, video_id)
    if segments:
        return segments

    # Method 2: youtube-transcript-api
    raw_segments = await asyncio.to_thread(_fetch_subtitles_transcript_api, video_id)
    if raw_segments:
        return _build_segments_from_raw(raw_segments)

    # Method 3: Invidious API
    segments = await _fetch_subtitles_invidious(video_id)
    if segments:
        return segments

    # Method 4: YouTube embed page extraction
    segments = await _fetch_subtitles_embed(video_id)
    if segments:
        return segments

    return []


def _fetch_subtitles_yt_dlp(video_id: str) -> list[SubtitleSegment]:
    try:
        import yt_dlp
        with tempfile.TemporaryDirectory() as tmpdir:
            output_template = os.path.join(tmpdir, "subs")
            ydl_opts = {
                'quiet': True,
                'no_warnings': True,
                'skip_download': True,
                'writesubtitles': True,
                'writeautomaticsub': True,
                'subtitleslangs': SUBTITLE_LANGS,
                'subtitlesformat': 'json3',
                'outtmpl': output_template,
            }

            proxy = os.environ.get("YOUTUBE_PROXY")
            if proxy:
                ydl_opts['proxy'] = proxy

            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([f"https://www.youtube.com/watch?v={video_id}"])

            for f in sorted(os.listdir(tmpdir)):
                if f.endswith('.json3'):
                    filepath = os.path.join(tmpdir, f)
                    with open(filepath) as fh:
                        data = json.load(fh)
                    return _parse_json3_to_segments(data)

            for f in sorted(os.listdir(tmpdir)):
                if f.endswith('.vtt'):
                    filepath = os.path.join(tmpdir, f)
                    with open(filepath) as fh:
                        content = fh.read()
                    raw = _parse_vtt(content)
                    return _build_segments_from_raw(raw)

        return []
    except Exception as e:
        print(f"yt-dlp subtitle fetch failed: {e}")
        return []


async def _fetch_subtitles_invidious(video_id: str) -> list[SubtitleSegment]:
    for instance in INVIDIOUS_INSTANCES:
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                r = await client.get(
                    f"{instance}/api/v1/videos/{video_id}",
                    follow_redirects=True,
                )
                if r.status_code != 200:
                    continue

                data = r.json()
                captions = data.get("captions", [])
                if not captions:
                    continue

                # Find best caption track
                track = None
                for lang in SUBTITLE_LANGS:
                    for c in captions:
                        if c.get("language_code", "").startswith(lang):
                            track = c
                            break
                    if track:
                        break

                if not track and captions:
                    track = captions[0]

                if not track:
                    continue

                sub_url = track.get("url", "")
                if not sub_url:
                    continue

                full_url = f"{instance}{sub_url}" if sub_url.startswith("/") else sub_url
                # Request VTT format
                if "fmt=" not in full_url:
                    full_url += "&fmt=vtt"

                sr = await client.get(full_url, follow_redirects=True)
                if sr.status_code == 200 and sr.text.strip():
                    raw = _parse_vtt(sr.text)
                    if raw:
                        print(f"Invidious ({instance}) subtitle fetch succeeded")
                        return _build_segments_from_raw(raw)
        except Exception as e:
            print(f"Invidious ({instance}) failed: {e}")
            continue

    return []


async def _fetch_subtitles_embed(video_id: str) -> list[SubtitleSegment]:
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"https://www.youtube.com/embed/{video_id}",
                headers={"User-Agent": BROWSER_UA},
                follow_redirects=True,
            )
            if r.status_code != 200:
                return []

            match = re.search(r'ytcfg\.set\((\{.*?\})\);', r.text, re.DOTALL)
            if not match:
                return []

            cfg = json.loads(match.group(1))
            pv = cfg.get("PLAYER_VARS", {})
            epr_str = pv.get("embedded_player_response", "")
            if not epr_str:
                return []

            epr = json.loads(epr_str)
            captions = epr.get("captions", {})
            renderer = captions.get("playerCaptionsTracklistRenderer", {})
            tracks = renderer.get("captionTracks", [])

            for track in tracks:
                base_url = track.get("baseUrl", "")
                if not base_url:
                    continue
                fmt_url = base_url + "&fmt=json3"
                sr = await client.get(fmt_url, timeout=15)
                if sr.status_code == 200:
                    data = sr.json()
                    segments = _parse_json3_to_segments(data)
                    if segments:
                        print("Embed subtitle fetch succeeded")
                        return segments

    except Exception as e:
        print(f"Embed subtitle fetch failed: {e}")

    return []


def _parse_json3_to_segments(data: dict) -> list[SubtitleSegment]:
    segments: list[SubtitleSegment] = []
    events = data.get("events", [])

    for event in events:
        if "segs" not in event:
            continue

        start_ms = event.get("tStartMs", 0)
        duration_ms = event.get("dDurationMs", 0)
        start = start_ms / 1000.0
        end = (start_ms + duration_ms) / 1000.0

        text_parts = []
        for seg in event["segs"]:
            text = seg.get("utf8", "")
            if text.strip():
                text_parts.append(text.strip())

        full_text = " ".join(text_parts)
        full_text = re.sub(r'\n+', ' ', full_text).strip()

        if not full_text:
            continue

        words_list = full_text.split()
        word_duration = (duration_ms / 1000.0) / max(len(words_list), 1)
        words = []
        for i, w in enumerate(words_list):
            ws = start + i * word_duration
            we = ws + word_duration
            words.append(WordTimestamp(word=w, start=round(ws, 2), end=round(we, 2)))

        segments.append(SubtitleSegment(
            text=full_text,
            start=round(start, 2),
            end=round(end, 2),
            words=words,
        ))

    return segments


def _parse_vtt(content: str) -> list[dict]:
    segments = []
    lines = content.strip().split("\n")
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        time_match = re.match(
            r'(\d{2}:\d{2}:\d{2}\.\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}\.\d{3})', line
        )
        if time_match:
            start = _parse_vtt_time(time_match.group(1))
            end = _parse_vtt_time(time_match.group(2))
            i += 1
            text_lines = []
            while i < len(lines) and lines[i].strip():
                clean = re.sub(r'<[^>]+>', '', lines[i].strip())
                if clean:
                    text_lines.append(clean)
                i += 1
            if text_lines:
                text = " ".join(text_lines)
                segments.append({
                    "text": text,
                    "start": start,
                    "duration": end - start,
                })
        else:
            i += 1
    return segments


def _parse_vtt_time(time_str: str) -> float:
    parts = time_str.split(":")
    hours = int(parts[0])
    minutes = int(parts[1])
    seconds = float(parts[2])
    return hours * 3600 + minutes * 60 + seconds


def _fetch_subtitles_transcript_api(video_id: str) -> list[dict]:
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        from youtube_transcript_api.proxies import GenericProxyConfig

        proxy_url = os.environ.get("YOUTUBE_PROXY")
        if proxy_url:
            proxy_config = GenericProxyConfig(
                http_url=proxy_url,
                https_url=proxy_url,
            )
            ytt_api = YouTubeTranscriptApi(proxy_config=proxy_config)
        else:
            ytt_api = YouTubeTranscriptApi()

        transcript_list = ytt_api.list(video_id)

        try:
            transcript = transcript_list.find_transcript(['en'])
        except Exception:
            try:
                transcript = transcript_list.find_transcript(['pt', 'pt-BR', 'es', 'fr', 'de'])
            except Exception:
                transcripts = list(transcript_list)
                if transcripts:
                    transcript = transcripts[0]
                else:
                    return []

        snippets = transcript.fetch()
        segments = []
        for snippet in snippets:
            segments.append({
                "text": snippet.text,
                "start": snippet.start,
                "duration": snippet.duration,
            })
        return segments
    except Exception as e:
        print(f"Transcript API failed: {e}")
        return []


def _build_segments_from_raw(raw_segments: list[dict]) -> list[SubtitleSegment]:
    if not raw_segments:
        return []

    results: list[SubtitleSegment] = []

    for segment in raw_segments:
        text = segment["text"].strip()
        text = re.sub(r'\n+', ' ', text)
        start = segment["start"]
        duration = segment.get("duration", 0)
        end = start + duration

        if not text:
            continue

        words_list = text.split()
        word_dur = duration / max(len(words_list), 1)
        words = []
        for i, w in enumerate(words_list):
            ws = start + i * word_dur
            we = ws + word_dur
            words.append(WordTimestamp(word=w, start=round(ws, 2), end=round(we, 2)))

        results.append(SubtitleSegment(
            text=text,
            start=round(start, 2),
            end=round(end, 2),
            words=words,
        ))

    return results


def process_raw_subtitles(raw_data: list[dict]) -> list[SubtitleSegment]:
    return _build_segments_from_raw(raw_data)
