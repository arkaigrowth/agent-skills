# Platform Support Reference

## Supported Video Platforms

yt-dlp supports 1000+ sites. Here are the most commonly used:

### Video Streaming

- **YouTube**: Videos, playlists, channels, live streams, unlisted videos
- **Vimeo**: Public and private videos (with authentication)
- **Dailymotion**: Videos and playlists
- **Twitch**: VODs, clips, live streams
- **Facebook**: Public videos, Watch videos
- **Instagram**: Posts, IGTV, Reels, Stories
- **TikTok**: Videos, user profiles
- **Twitter/X**: Videos in tweets

### Social & Entertainment

- **Reddit**: Video posts
- **Pinterest**: Video pins
- **Tumblr**: Video posts
- **LinkedIn**: Video posts
- **9GAG**: Videos

### Educational & Professional

- **Coursera**: Course videos
- **Udemy**: Course videos (if you have access)
- **Khan Academy**: Educational videos
- **TED**: TED Talks
- **Vimeo**: Professional content

### Audio & Music

- **SoundCloud**: Tracks and playlists
- **Bandcamp**: Tracks and albums
- **Mixcloud**: Mixes and shows

### Live Streaming

- **Twitch**: Live and archived streams
- **YouTube Live**: Live streams
- **Facebook Live**: Live broadcasts

### Regional Platforms

- **Bilibili**: Chinese video platform
- **Niconico**: Japanese video platform
- **VK**: Russian social network videos
- **Youku**: Chinese video platform

## Authentication Requirements

Some platforms require authentication for private/restricted content:

### Automatic Cookie Extraction

yt-dlp can automatically extract cookies from your browser:

- Chrome: `--cookies-from-browser chrome`
- Firefox: `--cookies-from-browser firefox`
- Safari: `--cookies-from-browser safari`

**This is handled automatically by the download scripts when needed.**

### Manual Cookie Export

If automatic extraction fails:

1. Install browser extension (e.g., "Get cookies.txt")
2. Export cookies for the site
3. Use: `yt-dlp --cookies cookies.txt URL`

## Platform-Specific Notes

### YouTube

- **Unlisted videos**: Work without authentication
- **Private videos**: Require authentication (use cookies)
- **Age-restricted**: yt-dlp will attempt to authenticate
- **Live streams**: Can download ongoing streams
- **Premieres**: Can queue for download when live

### Vimeo

- **Private videos**: Require password or authentication
- **Staff Picks**: Fully supported
- **On Demand**: May require purchase/rental

### TikTok

- **Watermarks**: Videos include TikTok watermark
- **Music**: Audio is included in download

### Instagram

- **Private accounts**: Require authentication
- **Stories**: Temporary, must download within 24h

### Twitch

- **VODs**: Full archives supported
- **Clips**: Individual clips supported
- **Sub-only VODs**: Require subscription (use cookies)

## Geo-Restrictions

Some content may be geo-restricted:

- **Cannot bypass**: yt-dlp respects region locks
- **Solution**: Use VPN if needed (outside yt-dlp scope)

## Rate Limits

Platforms may rate-limit downloads:

- **YouTube**: Generally no issues
- **Others**: May throttle after multiple downloads
- **Solution**: Use `--sleep-interval` flag if needed

## Complete Platform List

For the full list of 1000+ supported sites:

```bash
yt-dlp --list-extractors
```

Or visit: https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md
