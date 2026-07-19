# Playlist Workflows Reference

## Advanced Batch Processing Patterns

### Workflow 1: Progressive Download Strategy

For large playlists, download incrementally to verify quality before committing:

```bash
# Step 1: Query metadata
python scripts/query_video.py "PLAYLIST_URL" --json > playlist_info.json

# Step 2: Download first 3 videos to test
python scripts/download_playlist.py "PLAYLIST_URL" --max-videos 3 --quality 1080p

# Step 3: Review downloads
ls ~/Movies/VIDEO_DOWNLOAD/playlist_downloads/

# Step 4: If satisfied, download next batch
python scripts/download_playlist.py "PLAYLIST_URL" --range 4-20 --quality 1080p

# Step 5: Continue in batches
python scripts/download_playlist.py "PLAYLIST_URL" --range 21-50 --quality 1080p
```

**Benefits:**
- Test quality/size before full download
- Pause between batches
- Resume if interrupted

### Workflow 2: Multi-Quality Downloads

Download playlist at multiple qualities for different use cases:

```bash
# High quality for archival (first 10 only)
python scripts/download_playlist.py "URL" --max-videos 10 --quality 1080p \
  --output ~/Movies/VIDEO_DOWNLOAD/archive_quality

# Lower quality for mobile/quick review
python scripts/download_playlist.py "URL" --quality 720p \
  --output ~/Movies/VIDEO_DOWNLOAD/mobile_quality

# Audio-only for transcription
python scripts/download_playlist.py "URL" --audio-only \
  --output ~/Movies/VIDEO_DOWNLOAD/audio_transcripts
```

### Workflow 3: Filtered Download by Keywords

Download only relevant videos from a large playlist:

```bash
# Example: Course playlist, only want "Python" lectures
python scripts/query_video.py "COURSE_PLAYLIST_URL" --json > course.json

# Download Python-related only
python scripts/download_playlist.py "COURSE_PLAYLIST_URL" \
  --filter "python" --quality 720p

# Download "advanced" topics only
python scripts/download_playlist.py "COURSE_PLAYLIST_URL" \
  --filter "advanced" --quality 720p
```

**Filter is case-insensitive** - matches title text.

### Workflow 4: Overnight Batch Download

For very large playlists, set up overnight download:

```bash
# Use nohup to continue after disconnection
nohup python scripts/download_playlist.py "LARGE_PLAYLIST" \
  --quality 720p \
  > download.log 2>&1 &

# Check progress next morning
tail -f download.log

# Or check downloaded count
ls ~/Movies/VIDEO_DOWNLOAD/playlist_downloads/*/ | wc -l
```

### Workflow 5: Parallel Processing After Download

After downloading playlist, process all videos:

```bash
# Download playlist
python scripts/download_playlist.py "URL" --max-videos 20 --quality 1080p

# Batch extract keyframes
for video in ~/Movies/VIDEO_DOWNLOAD/playlist_downloads/*/*.mp4; do
  echo "Processing: $video"
  # hand off to your transcription/keyframe tooling here
    --threshold 0.3 --max-frames 50
done

# Batch transcribe
for video in ~/Movies/VIDEO_DOWNLOAD/playlist_downloads/*/*.mp4; do
  echo "Transcribing: $video"
  output="${video%.mp4}_transcript.json"
  # hand off to your transcription/keyframe tooling here
done
```

### Workflow 6: Resume After Interruption

Playlists resume automatically:

```bash
# Start large playlist
python scripts/download_playlist.py "URL" --quality 1080p

# Gets interrupted at video 23/50
^C

# Resume with exact same command - skips already downloaded
python scripts/download_playlist.py "URL" --quality 1080p
# Continues from video 24
```

**yt-dlp's `--no-overwrites` flag handles this automatically.**

### Workflow 7: Channel Archive

Download all videos from a channel:

```bash
# Option 1: Use channel URL directly
python scripts/download_playlist.py "https://youtube.com/@channelname/videos" \
  --quality 1080p

# Option 2: Get uploads playlist ID and download
# (Uploads playlist ID is usually UC... instead of UC...)
python scripts/download_playlist.py "UPLOADS_PLAYLIST_URL" --quality 720p
```

**Warning:** Popular channels may have 1000+ videos. Use `--max-videos` to limit.

### Workflow 8: Differential Updates

Download only new videos from a playlist you've downloaded before:

```bash
# Initial download
python scripts/download_playlist.py "URL" --quality 1080p

# Later, re-run same command
python scripts/download_playlist.py "URL" --quality 1080p
# Automatically skips already-downloaded videos, gets new ones
```

**yt-dlp checks existing files and skips them.**

### Workflow 9: Custom Output Organization

Organize downloads by category:

```bash
# Tutorials
python scripts/download_playlist.py "TUTORIAL_PLAYLIST" \
  --output ~/Movies/VIDEO_DOWNLOAD/tutorials

# Webinars
python scripts/download_playlist.py "WEBINAR_PLAYLIST" \
  --output ~/Movies/VIDEO_DOWNLOAD/webinars

# Interviews
python scripts/download_playlist.py "INTERVIEW_PLAYLIST" \
  --output ~/Movies/VIDEO_DOWNLOAD/interviews
```

## Playlist Size Estimation

Use query script to estimate before downloading:

```bash
python scripts/query_video.py "PLAYLIST_URL"
```

**Output includes:**
- Total video count
- Total duration
- Size estimates for each quality
- Preview of first 5 videos

**Example output:**
```
🎬 Playlist: "PIM Tutorial Series"
Videos: 47
Total Duration: 18h 23m

⚠️  WARNING: This is a playlist download

💾 Estimated Total Sizes:
  4K     ~180.5GB
  1440p  ~92.3GB
  1080p  ~61.5GB ⭐
  720p   ~38.7GB

📋 Top 5 Videos:
  1. Introduction to PIM (45:23, 1,200MB)
  2. Data Modeling (32:15, 890MB)
  ...
```

## Handling Large Playlists

### Strategy 1: Subset by Range

Download in manageable chunks:

```bash
# Videos 1-20
python scripts/download_playlist.py "URL" --range 1-20

# Videos 21-40
python scripts/download_playlist.py "URL" --range 21-40

# Videos 41-60
python scripts/download_playlist.py "URL" --range 41-60
```

### Strategy 2: Reduce Quality

Use lower quality for large playlists:

```bash
# 50 videos at 1080p = ~180GB
# 50 videos at 720p = ~115GB (saves 65GB)
python scripts/download_playlist.py "URL" --quality 720p
```

### Strategy 3: Audio-Only First

Download audio to assess content, then decide which to download in video:

```bash
# Step 1: Download all as audio (fast, small)
python scripts/download_playlist.py "URL" --audio-only \
  --output ~/Movies/VIDEO_DOWNLOAD/audio_preview

# Step 2: Listen/review

# Step 3: Download specific videos in full quality
python scripts/download_single.py "SPECIFIC_VIDEO_URL" --quality 1080p
```

## Error Handling

### Unavailable Videos

Playlists may contain unavailable videos (deleted, private, geo-blocked):

```bash
# Use --ignore-errors (default in download_playlist.py)
python scripts/download_playlist.py "URL"
```

**Behavior:**
- Unavailable videos are skipped automatically
- Download continues with next video
- Summary shows: Downloaded, Skipped, Failed counts

### Network Interruptions

Downloads resume automatically:

```bash
# If network drops during video 15
# Just re-run same command
python scripts/download_playlist.py "URL"
# Skips videos 1-14 (already downloaded)
# Resumes video 15 from partial file
# Continues with video 16, 17...
```

## Cleanup After Batch Downloads

Large playlist downloads may leave fragments:

```bash
# After playlist download, clean up
python scripts/cleanup_fragments.py ~/Movies/VIDEO_DOWNLOAD --dry-run

# If fragments found, actually delete
python scripts/cleanup_fragments.py ~/Movies/VIDEO_DOWNLOAD
```

## Performance Tips

### Faster Downloads

1. **Use lower quality**: 720p downloads 2x faster than 1080p
2. **Audio-only**: 10x faster than video
3. **Wired connection**: Faster than Wi-Fi
4. **Off-peak hours**: Less network congestion

### Storage Management

1. **Clean up old downloads**: Remove videos after processing
2. **Use external drive**: Move large playlists to external storage
3. **Audio-only when possible**: 20x smaller than video
4. **720p for non-critical**: Saves ~40% vs 1080p

### Monitoring Progress

```bash
# Check downloaded count
ls ~/Movies/VIDEO_DOWNLOAD/playlist_downloads/*/ | wc -l

# Check total size
du -sh ~/Movies/VIDEO_DOWNLOAD/playlist_downloads/

# Watch live progress
tail -f download.log  # If using nohup
```

## Best Practices

### Before Starting Large Playlist

1. **Query first**: Get size estimate
2. **Test with --max-videos 3**: Verify quality/size
3. **Choose appropriate quality**: 720p often sufficient
4. **Estimate time**: ~1 video per minute at 1080p
5. **Check storage**: Ensure enough free space

### During Download

1. **Don't interrupt unnecessarily**: Let batches complete
2. **Monitor storage**: Watch free space
3. **Check for errors**: Review failed downloads

### After Download

1. **Verify downloads**: Spot-check videos play correctly
2. **Clean fragments**: Remove `.part` files
3. **Organize**: Move to appropriate folders
4. **Backup if archival**: Copy to external drive
5. **Delete originals after processing**: If using for transcription only


## Troubleshooting Large Playlists

### "Out of storage space" During Download

**Solution:**
```bash
# Stop download
^C

# Clean up fragments
python scripts/cleanup_fragments.py ~/Movies/VIDEO_DOWNLOAD

# Resume with lower quality
python scripts/download_playlist.py "URL" --quality 720p
```

### "Too many videos to download"

**Solution:**
```bash
# Download in smaller batches
python scripts/download_playlist.py "URL" --range 1-25
python scripts/download_playlist.py "URL" --range 26-50
```

### "Download too slow"

**Solutions:**
1. Use 720p instead of 1080p
2. Download during off-peak hours
3. Use wired connection
4. Check bandwidth limits
