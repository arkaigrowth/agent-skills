# Quality Guide Reference

## Video Quality Deep Dive

### Resolution & Bitrate Relationships

| Quality | Resolution | Bitrate (Video) | Bitrate (Audio) | Total | Use Case |
|---------|-----------|-----------------|-----------------|-------|----------|
| 4K/2160p | 3840×2160 | ~25 Mbps | 0.32 Mbps | ~25.3 Mbps | Archival, 4K displays |
| 1440p | 2560×1440 | ~12 Mbps | 0.32 Mbps | ~12.3 Mbps | High-quality editing |
| **1080p** | **1920×1080** | **~8 Mbps** | **0.32 Mbps** | **~8.3 Mbps** | **Best balance** |
| 720p | 1280×720 | ~5 Mbps | 0.32 Mbps | ~5.3 Mbps | Space-efficient |
| 480p | 854×480 | ~2.5 Mbps | 0.32 Mbps | ~2.8 Mbps | Low bandwidth |

### Size Calculations

**Formula:** `Size (MB) = (Bitrate in Mbps × Duration in seconds) / 8`

**Examples for 1-hour video:**

- **4K**: 25.3 Mbps × 3600s ÷ 8 = **11,385 MB (~11.1 GB)**
- **1080p**: 8.3 Mbps × 3600s ÷ 8 = **3,735 MB (~3.6 GB)**
- **720p**: 5.3 Mbps × 3600s ÷ 8 = **2,385 MB (~2.3 GB)**
- **Audio only**: 0.32 Mbps × 3600s ÷ 8 = **144 MB**

### Audio Bitrate Comparison

| Bitrate | Quality | Size (1 hour) | Use Case |
|---------|---------|---------------|----------|
| **320 kbps** | **Excellent** | **~144 MB** | **Music, high-quality podcasts** |
| 256 kbps | Very good | ~115 MB | Good balance |
| 192 kbps | Good | ~86 MB | Podcasts, voice |
| 128 kbps | Acceptable | ~58 MB | Space-constrained |

**Recommendation:** Use 320kbps for music, 192kbps for podcasts/voice.

## Codec Information

### Video Codecs

**H.264/AVC (default):**
- Universal compatibility
- Efficient compression
- Supported everywhere
- Default for yt-dlp downloads

**H.265/HEVC:**
- 50% better compression than H.264
- Less compatible (older devices struggle)
- Not typically used by yt-dlp by default

**VP9:**
- Used by YouTube for some videos
- Similar quality to H.264
- Good browser support

### Audio Codecs

**AAC (default):**
- Universal compatibility
- Good quality-to-size ratio
- Default for video downloads

**MP3 (for audio-only):**
- Universal compatibility
- Widely supported
- Default for `--audio-only` downloads

**Opus:**
- Better quality than AAC at same bitrate
- Less compatible

## Quality Selection Strategy

### For Different Use Cases

**Archival/Future-proofing:**
- Use 4K or highest available
- Store original quality
- Accept large file sizes

**Editing/Production:**
- Use 1080p or 1440p
- Balance quality and file size
- Consider workflow speed

**Personal Viewing:**
- Use 1080p (best balance)
- Good quality, reasonable size
- Works on all devices

**Mobile/Sharing:**
- Use 720p
- Faster downloads
- Less storage needed

**Podcasts/Music:**
- Use audio-only
- 320kbps for music
- 192kbps for speech

**Transcription Only:**
- Use audio-only
- Lower bitrate acceptable (128kbps)
- Much faster download

### Platform-Specific Considerations

**YouTube:**
- Often provides 4K, 1440p, 1080p, 720p
- 1080p60 (60fps) available for some videos
- VP9 codec for some high-quality streams

**Vimeo:**
- Provides multiple qualities
- Often has 1080p and 720p
- Professional codec settings

**TikTok/Instagram:**
- Usually max 1080p
- Often 720p mobile-optimized
- Use default settings

**Twitch:**
- Live streams: Source quality varies
- VODs: Usually 1080p60
- Consider 720p for faster downloads

## Trade-offs Summary

| Factor | 4K | 1080p | 720p | Audio Only |
|--------|----|----|------|------------|
| **Quality** | ★★★★★ | ★★★★☆ | ★★★☆☆ | N/A |
| **File Size** | ★☆☆☆☆ | ★★★☆☆ | ★★★★☆ | ★★★★★ |
| **Download Speed** | ★☆☆☆☆ | ★★★☆☆ | ★★★★☆ | ★★★★★ |
| **Compatibility** | ★★★☆☆ | ★★★★★ | ★★★★★ | ★★★★★ |
| **Storage Efficiency** | ★☆☆☆☆ | ★★★☆☆ | ★★★★☆ | ★★★★★ |

## Practical Examples

### Scenario 1: Interview Recording (1 hour)

**Options:**
- 1080p: ~3.6GB (recommended)
- 720p: ~2.3GB (if storage limited)
- Audio-only: ~144MB (if video not needed)

**Recommendation:** 1080p - Good quality for faces/gestures, reasonable size.

### Scenario 2: Tutorial/Screen Recording (30 min)

**Options:**
- 1080p: ~1.8GB (recommended)
- 720p: ~1.15GB (adequate for screen content)

**Recommendation:** 1080p - Text needs to be sharp, worth the size.

### Scenario 3: Podcast (2 hours)

**Options:**
- Audio-only 320kbps: ~288MB (recommended)
- Audio-only 192kbps: ~173MB (acceptable)

**Recommendation:** 320kbps - Music/high-quality audio matters.

### Scenario 4: Music Video (4 minutes)

**Options:**
- 1080p: ~240MB (recommended)
- 4K: ~680MB (if archival quality needed)

**Recommendation:** 1080p - Good balance, 4K rarely necessary.

### Scenario 5: Playlist of 50 Tutorials (avg 20 min each)

**Total Duration:** 1000 minutes (~16.7 hours)

**Options:**
- 1080p: ~60GB
- 720p: ~38GB (recommended)
- Audio-only: ~3.6GB

**Recommendation:** 720p - Acceptable quality, saves 22GB vs 1080p.

## Quick Decision Table

| Content Type | Recommended Quality | Rationale |
|--------------|---------------------|-----------|
| Tutorials/Courses | 1080p | Text readability |
| Interviews | 1080p | Face details matter |
| Music Videos | 1080p or 4K | Visual quality important |
| Podcasts | Audio 320k | No video needed |
| Webinars | 720p | Slides readable, saves space |
| Lectures | 720p | Acceptable for slides/board |
| Live Streams | 720p | Faster download, good enough |
| Archival | 4K | Future-proof |

## Advanced: Format Selection

yt-dlp uses format codes internally. The download scripts abstract this, but for reference:

**Format selection examples:**
- `bestvideo+bestaudio` - Best quality (may be 4K)
- `bestvideo[height<=1080]+bestaudio` - 1080p max
- `bestvideo[height<=720]+bestaudio` - 720p max
- `bestaudio` - Audio only, best quality

**The scripts handle this automatically based on `--quality` flag.**
