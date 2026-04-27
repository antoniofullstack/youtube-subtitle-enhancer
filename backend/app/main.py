from fastapi import FastAPI, HTTPException, Query, Body
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from app.subtitles import (
    fetch_subtitles,
    fetch_video_info,
    extract_video_id,
    process_raw_subtitles,
)
from app.models import VideoResponse, SubtitleSegment

app = FastAPI(title="YouTube Subtitles API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/video", response_model=VideoResponse)
async def get_video(url: str = Query(..., description="YouTube video URL or ID")):
    try:
        video_info = await fetch_video_info(url)
        subtitles = await fetch_subtitles(url)
        return VideoResponse(
            video_id=video_info["video_id"],
            title=video_info["title"],
            thumbnail=video_info["thumbnail"],
            duration=video_info["duration"],
            subtitles=subtitles,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch video: {str(e)}")


class ProcessSubtitlesRequest(BaseModel):
    subtitles: list[dict]


@app.post("/api/process-subtitles", response_model=list[SubtitleSegment])
async def process_subtitles(body: ProcessSubtitlesRequest):
    return process_raw_subtitles(body.subtitles)


@app.get("/api/health")
async def health():
    return {"status": "ok"}
