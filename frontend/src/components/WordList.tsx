import type { SubtitleSegment } from "../types";
import styles from "./WordList.module.css";

interface WordListProps {
  subtitles: SubtitleSegment[];
  currentTime: number;
  onSeek: (time: number) => void;
}

export default function WordList({ subtitles, currentTime, onSeek }: WordListProps) {
  const allWords = subtitles.flatMap((s) => s.words);

  return (
    <div className={styles.wordContainer}>
      {allWords.map((word, index) => {
        const isActive = currentTime >= word.start && currentTime < word.end;
        const isPast = currentTime > word.end;

        return (
          <span
            key={index}
            className={`${styles.word} ${isActive ? styles.active : ""} ${isPast ? styles.past : ""}`}
            onClick={() => onSeek(word.start)}
          >
            {word.word}{" "}
          </span>
        );
      })}
    </div>
  );
}
