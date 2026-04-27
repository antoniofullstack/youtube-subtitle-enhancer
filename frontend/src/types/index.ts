export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
}

export interface SubtitleSegment {
  text: string;
  start: number;
  end: number;
  words: WordTimestamp[];
}

export interface VideoData {
  video_id: string;
  title: string;
  thumbnail: string;
  duration: number;
  subtitles: SubtitleSegment[];
}
