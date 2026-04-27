import re
import json
import asyncio
import tempfile
import os
from typing import Any

from app.models import SubtitleSegment, WordTimestamp


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
    info = await asyncio.to_thread(_get_video_info_sync, video_id)
    return info


def _get_video_info_sync(video_id: str) -> dict[str, Any]:
    try:
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
    except Exception:
        return {
            "video_id": video_id,
            "title": "YouTube Video",
            "thumbnail": f"https://img.youtube.com/vi/{video_id}/maxresdefault.jpg",
            "duration": 0.0,
        }


async def fetch_subtitles(url: str) -> list[SubtitleSegment]:
    video_id = extract_video_id(url)

    segments = await asyncio.to_thread(_fetch_subtitles_yt_dlp, video_id)
    if segments:
        return segments

    raw_segments = await asyncio.to_thread(_fetch_subtitles_transcript_api, video_id)
    return _build_segments_from_raw(raw_segments)


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
                'subtitleslangs': ['en', 'pt', 'pt-BR', 'es', 'fr', 'de'],
                'subtitlesformat': 'json3',
                'outtmpl': output_template,
            }
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
