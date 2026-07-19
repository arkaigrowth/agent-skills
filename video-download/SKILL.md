---
name: video-download
description: "Download videos and audio from 1000+ platforms (YouTube, Vimeo, etc.) with quality selection, caption extraction, playlist support, and macOS Finder tagging. Use when the user needs to download videos from URLs (including unlisted/private links), extract audio-only from videos, download captions/transcripts without full video, batch download playlists with filtering, get pre-download size/duration estimates, or perform any video acquisition task ahead of downstream analysis."
---

# Video Download Skill

Acquire videos, audio, and captions from 1000+ platforms using yt-dlp. Built for pre-download planning, resume support, and clean handoff to downstream analysis tooling.

## Requirements

- **Python:** 3.7+ (scripts will check version on startup)
- **yt-dlp:** Auto-installed on first run
- **macOS tagging (optional):** `brew install tag`

## Quick Start

### Single Video Download (Default Settings)

```bash
# Query first to see size estimate
python3 scripts/query_video.py "https://youtube.com/watch?v=abc123"

# Download with defaults (1080p, 320kbps audio, English/Polish/Spanish captions)
python3 scripts/download_single.py "URL"
```

**Default behavior:**
- Quality: 1080p (change with `--quality 4K` or `720p`)
- Audio: 320kbps (change with `--audio-bitrate 192k`)
- Captions: English, Polish, Spanish in native formats (vtt/srt)
- Location: Auto-detects Mac (`~/Movies/VIDEO_DOWNLOAD/`) or Claude Desktop
- Folder naming: `{Creator} - {Title} ({video_id})` for easy browsing
- Tagging: Applies 'video' macOS Finder tag (disable with `--no-tag`)
- Resume: Automatically resumes interrupted downloads
- Progress: Milestone-based progress (10%, 25%, 50%, 75%, 90%, 100%)
- Logging: Full logs saved to `download.log`, auto-cleaned on success

### Audio-Only Download

```bash
python3 scripts/download_single.py URL --audio-only
```

Downloads MP3 at 320kbps (or specify `--audio-bitrate 192k`).

## Workflow Pattern

**Recommended sequence:**

1. **Query** → See size/duration before downloading
2. **Download** → Acquire video/audio/captions
3. **Convert Transcript** → Generate human-readable markdown from JSON
4. **Process** → Hand off to your transcription/keyframe tooling
5. **Clean up** → Remove fragments if needed

## Core Operations

### 1. Query Video Metadata (Pre-Download)

**Always query first** for playlists or large videos to see size estimates.

```bash
# Single video
python3 scripts/query_video.py "URL"

# Playlist (shows total size, video count, top 5 videos)
python3 scripts/query_video.py "PLAYLIST_URL"

# JSON output for programmatic use
python3 scripts/query_video.py "URL" --json > metadata.json
```

**Output includes:**
- Duration, view count, uploader
- Available qualities (4K, 1440p, 1080p, 720p)
- Size estimates for each quality
- Caption availability
- For playlists: Total count, total size, preview of videos

### 2. Download Single Video

```bash
# Default (1080p, 320k audio, captions, tagged)
# Interactive: Prompts for keyframe extraction after download
python3 scripts/download_single.py "URL"

# 4K quality
python3 scripts/download_single.py "URL" --quality 4K

# Audio only (MP3)
python3 scripts/download_single.py "URL" --audio-only

# Specific audio bitrate
python3 scripts/download_single.py "URL" --audio-bitrate 192k

# Skip captions
python3 scripts/download_single.py "URL" --no-captions

# Auto-extract keyframes (no prompt, requires video-ops skill)
python3 scripts/download_single.py "URL" --extract-keyframes

# Skip keyframe extraction (no prompt)
python3 scripts/download_single.py "URL" --no-keyframes

# Custom output location
python3 scripts/download_single.py "URL" --output ~/Downloads/videos

# Skip macOS tagging
python3 scripts/download_single.py "URL" --no-tag
```

**Output structure:**
```
~/Movies/VIDEO_DOWNLOAD/IndyDevDan - Claude 4 ADVANCED AI Coding (f8RnRuaxee8)/
├── Claude 4 ADVANCED AI Coding....mp4    # Downloaded video
├── Claude 4 ADVANCED AI Coding....en.vtt # English captions (WebVTT)
├── Claude 4 ADVANCED AI Coding....info.json # Full metadata
├── Claude 4 ADVANCED AI Coding....webp   # Thumbnail
├── download.log                           # Download log (auto-cleaned on success)
└── SUMMARY.md                             # Human-readable summary
```

**New:** Folders are now human-readable with format: `{Creator} - {Title} ({video_id})`

### 3. Download Playlist

```bash
# Query first to see total size
python3 scripts/query_video.py "PLAYLIST_URL"

# Download all (be careful with large playlists!)
python3 scripts/download_playlist.py "PLAYLIST_URL"

# Download first 10 videos
python3 scripts/download_playlist.py "PLAYLIST_URL" --max-videos 10

# Download specific range (videos 5-20)
python3 scripts/download_playlist.py "PLAYLIST_URL" --range 5-20

# Filter by keyword
python3 scripts/download_playlist.py "PLAYLIST_URL" --filter "tutorial"

# Lower quality to save space
python3 scripts/download_playlist.py "PLAYLIST_URL" --quality 720p --max-videos 20
```

**Playlist features:**
- Automatic resume on interruption
- Skip unavailable/private videos
- Progress tracking per video (milestone-based)
- Organized output: `playlist_title/001 - video1.mp4`
- Download logs saved to `playlist_download.log`

### 4. Generate Human-Readable Transcript

Convert Whisper JSON transcripts to markdown with sentence-level timestamps:

```bash
# Convert transcript.json to readable markdown
python3 scripts/generate_transcript_md.py transcript.json

# Specify output file
python3 scripts/generate_transcript_md.py transcript.json -o readable_transcript.md

# Adjust timestamp interval (default: 5 seconds)
python3 scripts/generate_transcript_md.py transcript.json --interval 10
```

**Output format:**
```markdown
# Transcript: Video Title
**Creator:** Channel Name
**Duration:** 28:18

[00:00] First sentence of the video.
[00:05] Another sentence after 5 seconds.
[00:12] Continuing the transcript...
```

**Use after:** Whisper transcription from video-ops skill

### 5. Keyframe Extraction (Interactive Integration)

After downloading, you'll be prompted to extract keyframes:

```
✅ Download complete!

📹 Video: Gemini 3 Pro is the best model ever made.mp4 (90MB)
📁 Location: ~/Movies/VIDEO_DOWNLOAD/Creator - Video Title (video_id)...

🖼️  Extract keyframes from this video?
   💡 Tip: Use --extract-keyframes or --no-keyframes to skip this prompt
   [Y/n/later]: _
```

**Options:**
- **Y/yes/Enter** → Extract keyframes now using video-ops skill
- **n/no** → Skip extraction
- **later** → Skip with reminder about video-ops

**Requirements:**
- Requires video-ops skill at `~/.claude/skills/video-ops/`
- Auto-detects and uses video-ops if available
- Provides fallback instructions if not found

**Automation flags:**
```bash
# Auto-extract (no prompt) - for scripts/agents
python3 scripts/download_single.py "URL" --extract-keyframes

# Never extract (no prompt) - for speed
python3 scripts/download_single.py "URL" --no-keyframes

# Custom video-ops location
python3 scripts/download_single.py "URL" --video-ops-path ~/custom/path/to/video-ops
```

### 6. Clean Up Fragments

After interrupted downloads, clean up orphaned files:

```bash
# Dry run (see what would be deleted)
python3 scripts/cleanup_fragments.py ~/Movies/VIDEO_DOWNLOAD --dry-run

# Actually delete fragments
python3 scripts/cleanup_fragments.py ~/Movies/VIDEO_DOWNLOAD
```

Removes `.part`, `.ytdl`, `.temp` files from failed downloads.

## Quality Selection Guide

| Quality | Resolution | Typical Size (1 hour) | Use Case |
|---------|------------|----------------------|----------|
| 4K | 3840×2160 | ~12GB | Archival, large displays |
| 1440p | 2560×1440 | ~6GB | High quality viewing |
| **1080p** | 1920×1080 | **~4GB** | **Default, best balance** |
| 720p | 1280×720 | ~2.5GB | Space-saving |
| 480p | 854×480 | ~1.2GB | Low bandwidth |
| Audio only | N/A | ~150MB | Podcasts, music |

**Audio bitrate:**
- **320k** (default): High quality, ~2.4MB/min
- 192k: Good quality, ~1.4MB/min
- 128k: Acceptable, ~0.96MB/min

## Caption/Transcript Extraction

**Captions are downloaded without downloading the full video** when platform-embedded captions exist (YouTube auto-generated, manual subs).

```bash
# Download with captions (default: en,pl,es)
python3 scripts/download_single.py "URL"

# Custom caption languages
python3 scripts/download_single.py "URL" --caption-langs en,fr,de,ja

# Skip captions entirely
python3 scripts/download_single.py "URL" --no-captions
```

**Caption file format:** Plain text (`.txt`), one line per segment, no timestamps. For timestamped transcripts, use video-ops skill's `transcribe_video.py` with Whisper.

## Platform Support

Supports 1000+ sites including:
- YouTube (videos, playlists, channels, unlisted videos)
- Vimeo (including private videos with cookies)
- Twitter/X
- Facebook
- Instagram
- TikTok
- Twitch
- Reddit
- And many more...

For full list, see [references/platform_support.md](references/platform_support.md).

## Private/Unlisted Videos

For private or unlisted videos, yt-dlp automatically extracts cookies from your browser:

```bash
# No special flags needed - yt-dlp handles authentication automatically
python3 scripts/download_single.py "UNLISTED_URL"
```

If authentication fails, yt-dlp will extract cookies from Chrome/Firefox/Safari automatically.

## Resume Support

All downloads support automatic resume:

```bash
# Start download
python3 scripts/download_single.py "URL"

# Interrupted by Ctrl+C or network failure
^C
⚠️  Download interrupted by user
   Run the same command again to resume from where you left off.

# Resume with exact same command
python3 scripts/download_single.py "URL"
# Continues from 47% where it left off
```

**No need to manage resume state** - yt-dlp handles this automatically via `--continue` flag.

## macOS Finder Tags

By default, downloaded videos are tagged with 'video' tag in macOS Finder for easy searching.

```bash
# Uses default 'video' tag
python3 scripts/download_single.py "URL"

# Custom tag name
python3 scripts/download_single.py "URL" --tag-name "work"

# Disable tagging
python3 scripts/download_single.py "URL" --no-tag
```

On non-Mac systems, tagging is silently skipped.

## Output Locations

**Auto-detection:**
- **Mac:** `~/Movies/VIDEO_DOWNLOAD/` (override with the `VIDEO_DOWNLOAD_DIR` environment variable)
- **Claude Desktop:** `/mnt/user-data/outputs/video-downloads/`

**Override:**
```bash
python3 scripts/download_single.py "URL" --output ~/custom/path
```

**Directory structure:**
- Single videos: `video_{id}/` subdirectories
- Playlists: `playlist_downloads/{playlist_title}/` organized by index

## Integration with video-ops

After downloading, use video-ops skill for analysis:

```bash
# 1. Download video
python3 scripts/download_single.py "URL"
# Output: ~/Movies/VIDEO_DOWNLOAD/video_abc123/video.mp4

# 2. Extract keyframes (video-ops)
python /mnt/skills/user/video-ops/scripts/extract_keyframes.py \
  ~/Movies/VIDEO_DOWNLOAD/video_abc123/video.mp4

# 3. Transcribe with Whisper (video-ops)
python /mnt/skills/user/video-ops/scripts/transcribe_video.py \
  ~/Movies/VIDEO_DOWNLOAD/video_abc123/video.mp4 \
  -o ~/Movies/VIDEO_DOWNLOAD/video_abc123/transcript.json
```

**Claude orchestration:** When user requests "download and analyze keyframes", call download_single.py first, then video-ops scripts on the downloaded file.

## Common Patterns

### Download + Keyframe Extraction

```bash
# Step 1: Query size
python3 scripts/query_video.py "URL"

# Step 2: Download
python3 scripts/download_single.py "URL" --quality 1080p

# Step 3: Extract keyframes (video-ops)
python /mnt/skills/user/video-ops/scripts/extract_keyframes.py \
  $(find ~/Movies/VIDEO_DOWNLOAD/video_*/  -name "*.mp4" | tail -1)
```

### Audio-Only for Transcription

```bash
# Download audio only (faster, smaller)
python3 scripts/download_single.py "URL" --audio-only

# Transcribe with Whisper (video-ops)
python /mnt/skills/user/video-ops/scripts/transcribe_video.py \
  ~/Movies/VIDEO_DOWNLOAD/video_abc123/*.mp3 -o transcript.json
```

### Playlist Subset for Analysis

```bash
# Download first 5 videos for analysis
python3 scripts/download_playlist.py "PLAYLIST_URL" --max-videos 5 --quality 720p

# Batch process keyframes
for video in ~/Movies/VIDEO_DOWNLOAD/playlist_downloads/*/*.mp4; do
  python /mnt/skills/user/video-ops/scripts/extract_keyframes.py "$video"
done
```

## Troubleshooting

### Download Fails with "ERROR: Unable to download"

**Cause:** Video unavailable, age-restricted, or requires authentication.

**Solutions:**
- For age-restricted: yt-dlp will try to authenticate automatically
- For geo-restricted: Content may not be available in your region
- For deleted: Video no longer exists

### Progress Bar Not Showing

**Cause:** Output is being buffered.

**Solution:** Progress is printed line-by-line. If running in a script, output may be buffered. Progress updates appear as:
```
[download]  45.2% of ~1.23GiB at 5.67MiB/s ETA 02:15
```

### Fragments Not Cleaning Up

**Cause:** Download was interrupted, leaving `.part` files.

**Solution:**
```bash
python3 scripts/cleanup_fragments.py ~/Movies/VIDEO_DOWNLOAD
```

### macOS Tag Not Applied

**Cause:** `tag` command not installed or not on macOS.

**Solution:** Install `tag` via Homebrew:
```bash
brew install tag
```

Or disable tagging: `--no-tag`

## Script Reference

| Script | Purpose | Key Flags |
|--------|---------|-----------|
| `query_video.py` | Pre-download metadata | `--json`, `--quality` |
| `download_single.py` | Single video download | `--quality`, `--audio-only`, `--no-captions` |
| `download_playlist.py` | Batch playlist download | `--max-videos`, `--range`, `--filter` |
| `cleanup_fragments.py` | Clean orphaned files | `--dry-run` |

All scripts support `--help` for detailed usage.

## Reference Documentation

For detailed information on specific topics:

- **references/platform_support.md** - Complete list of supported sites
- **references/quality_guide.md** - Codec details, size calculations
- **references/playlist_workflows.md** - Advanced batch processing patterns

## Dependencies

**Required:**
- Python 3.7+
- yt-dlp (auto-installed on first run)

**Optional:**
- `tag` command (macOS only, for Finder tagging)

**Installation:**
```bash
# yt-dlp is installed automatically
# For macOS tagging support:
brew install tag
```

## Tips for Claude

- Always call `query_video.py` first for playlists or videos >30 min to show size estimates
- Default to 1080p unless user requests otherwise or storage is a concern
- For audio extraction (podcasts, music), use `--audio-only`
- If user mentions "captions" or "subtitles", ensure `--captions` is enabled (it's default)
- After downloading, suggest video-ops operations: keyframes, transcription, trimming
- For interrupted downloads, reassure user they can resume with same command
- If download fails due to authentication, yt-dlp will automatically try browser cookies
- Use `--quality 720p` for faster downloads when user mentions speed/storage concerns
- Playlist downloads can take significant time - warn user and suggest `--max-videos 10` for testing
