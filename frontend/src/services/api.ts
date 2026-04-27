import axios from "axios";
import type { VideoData, SubtitleSegment } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchVideo(url: string): Promise<VideoData> {
  const response = await axios.get<VideoData>(`${API_BASE}/api/video`, {
    params: { url },
  });
  return response.data;
}

export async function processSubtitles(
  subtitles: Array<{ text: string; start: number; duration: number }>
): Promise<SubtitleSegment[]> {
  const response = await axios.post<SubtitleSegment[]>(
    `${API_BASE}/api/process-subtitles`,
    { subtitles }
  );
  return response.data;
}
