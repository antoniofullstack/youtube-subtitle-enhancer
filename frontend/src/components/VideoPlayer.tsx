import { useRef, useEffect, useCallback } from "react";
import ReactPlayer from "react-player";
import styles from "./VideoPlayer.module.css";

interface VideoPlayerProps {
  videoId: string;
  playing: boolean;
  onTogglePlay: () => void;
  onProgress: (seconds: number) => void;
  onDuration: (duration: number) => void;
  seekTo: number | null;
  onSeekComplete: () => void;
}

export default function VideoPlayer({
  videoId,
  playing,
  onTogglePlay,
  onProgress,
  onDuration,
  seekTo,
  onSeekComplete,
}: VideoPlayerProps) {
  const playerRef = useRef<HTMLVideoElement>(null);

  useEffect(() => {
    if (seekTo !== null && playerRef.current) {
      playerRef.current.currentTime = seekTo;
      onSeekComplete();
    }
  }, [seekTo, onSeekComplete]);

  const handleTimeUpdate = useCallback(() => {
    if (playerRef.current) {
      onProgress(playerRef.current.currentTime);
    }
  }, [onProgress]);

  const handleLoadedMetadata = useCallback(() => {
    if (playerRef.current) {
      onDuration(playerRef.current.duration);
    }
  }, [onDuration]);

  return (
    <div className={styles.playerWrapper} onClick={onTogglePlay}>
      <ReactPlayer
        ref={playerRef}
        src={`https://www.youtube.com/watch?v=${videoId}`}
        playing={playing}
        controls={false}
        width="100%"
        height="100%"
        onTimeUpdate={handleTimeUpdate}
        onLoadedMetadata={handleLoadedMetadata}
        config={{
          youtube: {
            rel: 0,
          },
        }}
      />
      {!playing && (
        <div className={styles.playOverlay}>
          <svg width="64" height="64" viewBox="0 0 64 64" fill="none">
            <circle cx="32" cy="32" r="30" fill="rgba(255,255,255,0.2)" />
            <polygon points="26,20 26,44 46,32" fill="white" />
          </svg>
        </div>
      )}
    </div>
  );
}
