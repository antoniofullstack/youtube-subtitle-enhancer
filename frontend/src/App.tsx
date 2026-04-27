import { useState, useCallback } from "react";
import SearchBar from "./components/SearchBar";
import VideoPlayer from "./components/VideoPlayer";
import SubtitleList from "./components/SubtitleList";
import WordList from "./components/WordList";
import PlaybackControls from "./components/PlaybackControls";
import { fetchVideo } from "./services/api";
import { fetchSubtitlesClientSide } from "./services/clientSubtitles";
import type { VideoData } from "./types";
import styles from "./App.module.css";

type Tab = "subtitles" | "words";

export default function App() {
  const [videoData, setVideoData] = useState<VideoData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [currentTime, setCurrentTime] = useState(0);
  const [duration, setDuration] = useState(0);
  const [seekTo, setSeekTo] = useState<number | null>(null);
  const [activeTab, setActiveTab] = useState<Tab>("subtitles");

  const handleSearch = async (url: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchVideo(url);

      // If server couldn't fetch subtitles, try client-side
      if (data.subtitles.length === 0) {
        try {
          const clientSubs = await fetchSubtitlesClientSide(data.video_id);
          if (clientSubs.length > 0) {
            data.subtitles = clientSubs;
          }
        } catch {
          // Client-side fetch failed too, continue without subtitles
        }
      }

      setVideoData(data);
      setCurrentTime(0);
      setPlaying(false);

      if (data.subtitles.length === 0) {
        setError("Legendas não encontradas para este vídeo. O vídeo pode não ter legendas disponíveis.");
      }
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : "Falha ao buscar legendas";
      setError(message);
    } finally {
      setLoading(false);
    }
  };

  const handleTogglePlay = useCallback(() => {
    setPlaying((prev) => !prev);
  }, []);

  const handleProgress = useCallback((seconds: number) => {
    setCurrentTime(seconds);
  }, []);

  const handleDuration = useCallback((dur: number) => {
    setDuration(dur);
  }, []);

  const handleSeek = useCallback((time: number) => {
    setSeekTo(time);
    setCurrentTime(time);
  }, []);

  const handleSeekComplete = useCallback(() => {
    setSeekTo(null);
  }, []);

  const handleSkipBack = useCallback(() => {
    const newTime = Math.max(0, currentTime - 10);
    handleSeek(newTime);
  }, [currentTime, handleSeek]);

  const handleSkipForward = useCallback(() => {
    const newTime = Math.min(duration, currentTime + 10);
    handleSeek(newTime);
  }, [currentTime, duration, handleSeek]);

  return (
    <div className={styles.app}>
      <header className={styles.header}>
        <SearchBar onSearch={handleSearch} loading={loading} />
      </header>

      {error && (
        <div className={styles.error}>
          <p>{error}</p>
        </div>
      )}

      {!videoData && !loading && !error && (
        <div className={styles.welcome}>
          <div className={styles.welcomeIcon}>
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5">
              <rect x="2" y="2" width="20" height="20" rx="4" />
              <polygon points="10,8 16,12 10,16" fill="currentColor" stroke="none" />
            </svg>
          </div>
          <h2>YouTube Subtitle Enhancer</h2>
          <p>Cole uma URL do YouTube para ver as legendas organizadas por frases</p>
        </div>
      )}

      {videoData && (
        <>
          <div className={styles.tabs}>
            <button
              className={`${styles.tab} ${activeTab === "subtitles" ? styles.tabActive : ""}`}
              onClick={() => setActiveTab("subtitles")}
            >
              Subtitles
            </button>
            <button
              className={`${styles.tab} ${activeTab === "words" ? styles.tabActive : ""}`}
              onClick={() => setActiveTab("words")}
            >
              Words
            </button>
          </div>

          <div className={styles.videoSection}>
            <VideoPlayer
              videoId={videoData.video_id}
              playing={playing}
              onTogglePlay={handleTogglePlay}
              onProgress={handleProgress}
              onDuration={handleDuration}
              seekTo={seekTo}
              onSeekComplete={handleSeekComplete}
            />
          </div>

          <div className={styles.contentArea}>
            {activeTab === "subtitles" ? (
              <SubtitleList
                subtitles={videoData.subtitles}
                currentTime={currentTime}
                onSeek={(time) => {
                  handleSeek(time);
                  setPlaying(true);
                }}
              />
            ) : (
              <WordList
                subtitles={videoData.subtitles}
                currentTime={currentTime}
                onSeek={(time) => {
                  handleSeek(time);
                  setPlaying(true);
                }}
              />
            )}
          </div>

          <PlaybackControls
            playing={playing}
            currentTime={currentTime}
            duration={duration}
            onTogglePlay={handleTogglePlay}
            onSeek={handleSeek}
            onSkipBack={handleSkipBack}
            onSkipForward={handleSkipForward}
          />
        </>
      )}
    </div>
  );
}
