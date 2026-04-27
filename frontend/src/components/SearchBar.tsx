import { useState } from "react";
import styles from "./SearchBar.module.css";

interface SearchBarProps {
  onSearch: (url: string) => void;
  loading: boolean;
}

export default function SearchBar({ onSearch, loading }: SearchBarProps) {
  const [input, setInput] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (input.trim()) {
      onSearch(input.trim());
    }
  };

  return (
    <form className={styles.searchBar} onSubmit={handleSubmit}>
      <input
        type="text"
        placeholder="Cole a URL do YouTube aqui..."
        value={input}
        onChange={(e) => setInput(e.target.value)}
        className={styles.input}
        disabled={loading}
      />
      <button type="submit" className={styles.button} disabled={loading || !input.trim()}>
        {loading ? (
          <span className={styles.spinner} />
        ) : (
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="11" cy="11" r="8" />
            <line x1="21" y1="21" x2="16.65" y2="16.65" />
          </svg>
        )}
      </button>
    </form>
  );
}
