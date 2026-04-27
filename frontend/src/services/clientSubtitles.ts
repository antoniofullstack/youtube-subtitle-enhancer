import type { SubtitleSegment, WordTimestamp } from "../types";

interface CaptionTrack {
  baseUrl: string;
  languageCode: string;
  name?: { simpleText: string };
  kind?: string;
}

interface TimedTextEvent {
  tStartMs?: number;
  dDurationMs?: number;
  segs?: Array<{ utf8?: string; tOffsetMs?: number }>;
}

const PREFERRED_LANGS = ["en", "pt", "pt-BR", "es", "fr", "de"];

export async function fetchSubtitlesClientSide(
  videoId: string
): Promise<SubtitleSegment[]> {
  const tracks = await getCaptionTracks(videoId);
  if (!tracks.length) return [];

  let track = tracks.find((t) =>
    PREFERRED_LANGS.some((lang) => t.languageCode.startsWith(lang))
  );
  if (!track) track = tracks[0];

  const subtitleData = await fetchTimedText(track.baseUrl);
  if (!subtitleData) return [];

  return parseJson3ToSegments(subtitleData);
}

async function getCaptionTracks(videoId: string): Promise<CaptionTrack[]> {
  try {
    const resp = await fetch(
      `https://www.youtube.com/watch?v=${videoId}`,
      { credentials: "omit" }
    );
    if (!resp.ok) return [];

    const html = await resp.text();
    const match = html.match(/"captionTracks":(\[.*?\])/);
    if (!match) return [];

    return JSON.parse(match[1]);
  } catch {
    return [];
  }
}

async function fetchTimedText(
  baseUrl: string
): Promise<TimedTextEvent[] | null> {
  try {
    const url = baseUrl.includes("fmt=")
      ? baseUrl
      : baseUrl + "&fmt=json3";
    const resp = await fetch(url);
    if (!resp.ok) return null;
    const data = await resp.json();
    return data.events || null;
  } catch {
    return null;
  }
}

function parseJson3ToSegments(events: TimedTextEvent[]): SubtitleSegment[] {
  const segments: SubtitleSegment[] = [];

  for (const event of events) {
    if (!event.segs) continue;

    const startMs = event.tStartMs ?? 0;
    const durationMs = event.dDurationMs ?? 0;
    const start = startMs / 1000;
    const end = (startMs + durationMs) / 1000;

    const textParts: string[] = [];
    for (const seg of event.segs) {
      const text = seg.utf8?.trim();
      if (text) textParts.push(text);
    }

    const fullText = textParts.join(" ").replace(/\n+/g, " ").trim();
    if (!fullText) continue;

    const wordsList = fullText.split(/\s+/);
    const wordDuration = (durationMs / 1000) / Math.max(wordsList.length, 1);
    const words: WordTimestamp[] = wordsList.map((word, i) => ({
      word,
      start: Math.round((start + i * wordDuration) * 100) / 100,
      end: Math.round((start + (i + 1) * wordDuration) * 100) / 100,
    }));

    segments.push({
      text: fullText,
      start: Math.round(start * 100) / 100,
      end: Math.round(end * 100) / 100,
      words,
    });
  }

  return segments;
}
