from pydantic import BaseModel


class WordTimestamp(BaseModel):
    word: str
    start: float
    end: float


class SubtitleSegment(BaseModel):
    text: str
    start: float
    end: float
    words: list[WordTimestamp] = []


class VideoResponse(BaseModel):
    video_id: str
    title: str
    thumbnail: str
    duration: float
    subtitles: list[SubtitleSegment]
