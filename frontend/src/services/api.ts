import axios from "axios";
import type { VideoData } from "../types";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

export async function fetchVideo(url: string): Promise<VideoData> {
  const response = await axios.get<VideoData>(`${API_BASE}/api/video`, {
    params: { url },
  });
  return response.data;
}
