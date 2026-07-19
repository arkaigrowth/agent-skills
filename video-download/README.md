# video-download

A Claude Code skill that downloads video, audio, and captions from 1000+ platforms with yt-dlp, including pre-download size estimates, playlist filtering, and resume support.
It is designed to acquire media first, then hand off cleanly to whatever processing comes next (transcription, keyframes, editing).

## What it does

- Downloads single videos with quality selection (4K down to 480p) and configurable audio bitrate.
- Extracts audio only (MP3) for podcasts and transcription workflows.
- Fetches captions and subtitles without downloading the full video.
- Downloads playlists with range, count, and keyword filtering.
- Reports estimated size and duration before you commit to a download.
- Applies an optional macOS Finder tag for later searching.
- Resumes interrupted downloads by re-running the same command.

## Why

Grabbing media is usually step one of a larger task: analysis, transcription, or clip editing. This skill keeps acquisition separate from processing so each stays small and testable. Once a file is on disk, downstream tooling takes over for keyframe extraction, transcription, trimming, or subtitle generation.

## Requirements

- Python 3.7 or newer.
- `yt-dlp` (installed automatically on first run).
- Optional: the `tag` command for macOS Finder tagging (`brew install tag`).
- Optional: `ffmpeg` for audio extraction and format conversion, which yt-dlp uses when present.

## Install

This folder is a Claude Code skill. Place it under your skills directory so the agent can discover it:

```bash
cp -R video-download ~/.claude/skills/video-download
```

`SKILL.md` carries the frontmatter Claude Code reads to register the skill.

## Usage

```bash
# See size and duration before downloading
python3 scripts/query_video.py "https://youtube.com/watch?v=VIDEO_ID"

# Download a single video with defaults (1080p, 320k audio, captions)
python3 scripts/download_single.py "https://youtube.com/watch?v=VIDEO_ID"

# Audio only
python3 scripts/download_single.py "URL" --audio-only

# Download the first 10 videos of a playlist at 720p
python3 scripts/download_playlist.py "PLAYLIST_URL" --max-videos 10 --quality 720p

# Clean up leftover fragments from an interrupted download
python3 scripts/cleanup_fragments.py ~/Movies/VIDEO_DOWNLOAD --dry-run
```

### Output location

By default, downloads land in `~/Movies/VIDEO_DOWNLOAD/` on macOS, or a Claude Desktop
outputs directory when a home Movies folder is not present. Override the default with the
`VIDEO_DOWNLOAD_DIR` environment variable or the `--output` flag:

```bash
VIDEO_DOWNLOAD_DIR=~/Downloads/videos python3 scripts/download_single.py "URL"
python3 scripts/download_single.py "URL" --output ~/Downloads/videos
```

## Example

```bash
# 1. Check the download first
python3 scripts/query_video.py "https://youtube.com/watch?v=VIDEO_ID"
# -> duration, available qualities, per-quality size estimates, caption availability

# 2. Download at 1080p
python3 scripts/download_single.py "https://youtube.com/watch?v=VIDEO_ID" --quality 1080p
# -> ~/Movies/VIDEO_DOWNLOAD/Creator - Title (VIDEO_ID)/video.mp4 plus captions and SUMMARY.md

# 3. Hand off to your processing tooling (transcription, keyframes, editing)
```

## Tests

Pure helper functions have unit tests using the Python standard library only:

```bash
python3 -m unittest discover -s tests
```

Covered: `sanitize_filename`, `estimate_size`, `format_duration`, and
`ProgressTracker.parse_progress`. Network, filesystem, and yt-dlp dependent code
paths are not covered by these tests.

## Limitations

- macOS focused. Finder tagging is macOS only and is silently skipped elsewhere. The default output path assumes a `~/Movies` folder.
- Requires network access and depends on yt-dlp keeping pace with platform changes. Extractors can break when a site updates.
- Private or unlisted videos rely on yt-dlp reading cookies from a local browser, which may not work in every environment.
- `estimate_size` returns a rough projection from average bitrates, not a measured file size. Actual sizes vary with codec and content.
- Audio extraction and some format conversions need `ffmpeg` installed separately.
- The download, playlist, and caption code paths are not exercised by the included unit tests.

## Optional integration

The scripts auto-detect a separately distributed `video-ops` skill (keyframe extraction, Whisper transcription) and offer a post-download handoff when it is installed at `~/.claude/skills/video-ops/`. Everything in this skill works without it; the handoff is skipped gracefully when absent.

## License

MIT. See the repository root `LICENSE`.
