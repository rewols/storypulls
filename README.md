# StoryPulls

Paste an Instagram Reel, TikTok or Xiaohongshu (小红书) link and get a list of the places it features. Each place comes with a Google Maps link, a map, and CSV/KML export.

## How it works

```
web/     Next.js 16: UI, password gate, thin proxy to the worker
worker/  FastAPI (Python): download → transcribe → sample frames → Claude → Google Places
```

1. **Fetch** the post. TikTok and Instagram go through `yt-dlp`. Xiaohongshu pages are parsed directly (`window.__INITIAL_STATE__`), which works for image carousels as well as video notes.
2. **Listen and watch.** `faster-whisper` transcribes the audio locally (any language), and `ffmpeg` samples up to 12 frames. Carousel photos are used as they are.
3. **Extract.** One Claude call reads the caption, the timestamped transcript and the frames, and returns structured places with evidence ("said at 0:42", "on screen").
4. **Verify.** Google Places Text Search geocodes each place, retrying with the original-script name (e.g. 興波咖啡) if the English name misses. Places with no match stay in the list, flagged as unverified.

Results are cached in SQLite by post ID, so pasting the same link again costs nothing.

**Ingestion is the fragile part.** Instagram often needs a logged-in cookie file and blocks datacenter IPs. Xiaohongshu needs the full share link (with `xsec_token`) and sometimes a cookie file. When a fetch fails, the UI offers **Upload instead**: drop in a screen recording or screenshots and paste the caption.

## Run it

```bash
cp .env.example .env    # fill in ANTHROPIC_API_KEY, Google keys, APP_PASSWORD
docker compose up --build
open http://localhost:3000
```

The first video job downloads the Whisper model (~500 MB for `small`) into the worker's `/data` volume.

### Without Docker

```bash
# worker (needs ffmpeg on PATH)
cd worker && python -m venv .venv && .venv/bin/pip install -r requirements.txt
set -a; source ../.env; set +a
.venv/bin/uvicorn app.main:app --port 8000

# web
cd web && npm install && npm run dev
```

### Keys

| Variable | What for |
|---|---|
| `ANTHROPIC_API_KEY` | Place extraction (required) |
| `GOOGLE_MAPS_API_KEY` | Server-side Places API (New) lookups. Without it, places are unverified search links. |
| `GOOGLE_MAPS_BROWSER_KEY` | Maps JavaScript API for the map. Restrict it by HTTP referrer. |
| `GOOGLE_MAP_ID` | Needed for numbered markers; `DEMO_MAP_ID` works for testing |
| `APP_PASSWORD` | Shared password, so friends can use it but strangers can't spend your API credits |

### Cookies (Instagram / Xiaohongshu)

Export a Netscape-format `cookies.txt` from a browser where you're logged in (for example with the "Get cookies.txt LOCALLY" extension). Put it in `./cookies/`, then set `COOKIES_INSTAGRAM=/cookies/instagram.txt` (and the same for XHS). Use a throwaway account: scraping with your main account risks a ban.

Running the worker from a home connection makes Instagram much more reliable than running it on a cloud VM.

## Develop

```bash
cd worker && .venv/bin/python -m pytest          # unit + pipeline tests (Claude and Whisper stubbed)
.venv/bin/python -m scripts.smoke --fetch-only "<url>"   # check a platform download works
.venv/bin/python -m scripts.smoke "<url>"                # full pipeline, prints JSON

cd web && npm run typecheck && npm run lint && npm run build
```

When a platform breaks, the first thing to try is upgrading `yt-dlp` in `worker/requirements.txt`.

## Cost per post (rough)

- Claude (`claude-opus-5-5`, effort `medium`) with about 12 images plus the transcript: a few cents. Set `CLAUDE_MODEL=claude-sonnet-5-5` to halve it.
- Google Places Text Search: about $0.03 per place looked up.
- Whisper runs locally for free; a 60 s clip takes 10–20 s on CPU.
