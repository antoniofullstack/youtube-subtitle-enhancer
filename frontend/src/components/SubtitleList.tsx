import { useRef, useEffect } from "react";
import type { SubtitleSegment } from "../types";
import styles from "./SubtitleList.module.css";

interface SubtitleListProps {
  subtitles: SubtitleSegment[];
  currentTime: number;
  onSeek: (time: number) => void;
}

function formatTime(seconds: number): string {
  const mins = Math.floor(seconds / 60);
  const secs = Math.floor(seconds % 60);
  return `${String(mins).padStart(2, "0")}:${String(secs).padStart(2, "0")}`;
}

export default function SubtitleList({ subtitles, currentTime, onSeek }: SubtitleListProps) {
  const listRef = useRef<HTMLDivElement>(null);
  const activeRef = useRef<HTMLDivElement>(null);

  const activeIndex = subtitles.findIndex(
    (s) => currentTime >= s.start && currentTime < s.end
  );

  useEffect(() => {
    if (activeRef.current && listRef.current) {
      const container = listRef.current;
      const element = activeRef.current;
      const containerRect = container.getBoundingClientRect();
      const elementRect = element.getBoundingClientRect();

      if (
        elementRect.top < containerRect.top ||
        elementRect.bottom > containerRect.bottom
      ) {
        element.scrollIntoView({ behavior: "smooth", block: "center" });
      }
    }
  }, [activeIndex]);

  return (
    <div className={styles.list} ref={listRef}>
      {subtitles.map((subtitle, index) => {
        const isActive = index === activeIndex;
        const isPast = currentTime > subtitle.end;

        return (
          <div key={index}>
            <div className={styles.timestamp}>{formatTime(subtitle.start)}</div>
            <div
              ref={isActive ? activeRef : undefined}
              className={`${styles.card} ${isActive ? styles.active : ""} ${isPast ? styles.past : ""}`}
              onClick={() => onSeek(subtitle.start)}
            >
              <p className={styles.text}>{subtitle.text}</p>
            </div>
          </div>
        );
      })}
    </div>
  );
}
