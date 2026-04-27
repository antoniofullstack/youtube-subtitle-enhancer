# YouTube Subtitle Enhancer

A web application that improves YouTube subtitles by properly segmenting them into sentences and phrases, with synchronized playback.

## Features

- **Subtitle Segmentation**: YouTube subtitles are reorganized into proper sentences/phrases with accurate timestamps
- **Video Player**: Embedded YouTube player with custom controls
- **Subtitles Tab**: View all subtitles as scrollable cards with timestamps. The active subtitle highlights and auto-scrolls as the video plays
- **Words Tab**: Individual word-level view with highlighting synchronized to video playback
- **Click to Seek**: Click any subtitle or word to jump to that point in the video
- **Dark Theme**: Beautiful dark UI optimized for mobile devices
- **Multi-language**: Supports English, Portuguese, Spanish, French, and German subtitles

## Tech Stack

- **Frontend**: React + TypeScript (Vite), react-player, CSS Modules
- **Backend**: Python FastAPI, yt-dlp, youtube-transcript-api

## Getting Started

### Prerequisites

- Node.js 18+
- Python 3.10+

### Backend Setup

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -e .
uvicorn app.main:app --reload --port 8000
```

### Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

The app will be available at `http://localhost:5173`.

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `VITE_API_URL` | `http://localhost:8000` | Backend API URL |

## Usage

1. Paste a YouTube video URL in the search bar
2. Wait for subtitles to be fetched and processed
3. Use the **Subtitles** tab to read organized subtitles
4. Use the **Words** tab for word-by-word view
5. Click any subtitle or word to seek the video to that timestamp
6. Use the playback controls to play/pause and skip forward/backward

## API Endpoints

- `GET /api/video?url=<youtube_url>` - Fetch video info and subtitles
- `GET /api/health` - Health check

## License

MIT
