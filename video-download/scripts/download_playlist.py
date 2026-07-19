#!/usr/bin/env python3
"""
Download playlists with filtering and range selection.
Supports downloading all videos, subsets, or filtered by keywords.
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from _deps import (
    check_python_version, ensure_ytdlp, detect_environment, cleanup_fragments,
    ProgressTracker, cleanup_log_on_success, setup_subprocess_cleanup
)

# Check Python version before proceeding
check_python_version()


def download_playlist(
    url,
    output_dir=None,
    quality='1080p',
    audio_bitrate='320k',
    range_spec=None,
    max_videos=None,
    filter_keyword=None,
    captions=True,
    caption_langs=None
):
    """
    Download playlist with options.
    
    Args:
        url: Playlist URL
        output_dir: Download directory
        quality: Video quality
        audio_bitrate: Audio bitrate
        range_spec: Range spec like "1-10" or "5-20"
        max_videos: Maximum number of videos to download
        filter_keyword: Filter videos by keyword in title
        captions: Download captions
        caption_langs: Caption languages
        
    Returns:
        dict with download summary
    """
    ensure_ytdlp()
    
    # Determine output directory
    if output_dir is None:
        output_dir = detect_environment()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create playlist subdirectory
    playlist_dir = output_dir / "playlist_downloads"
    playlist_dir.mkdir(parents=True, exist_ok=True)
    
    # Build command
    cmd = ['yt-dlp']
    
    # Output template (organize by playlist)
    output_template = str(playlist_dir / '%(playlist_title)s/%(playlist_index)03d - %(title)s.%(ext)s')
    cmd.extend(['-o', output_template])
    
    # Quality selection
    format_map = {
        '4K': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
        '2160p': 'bestvideo[height<=2160]+bestaudio/best[height<=2160]',
        '1440p': 'bestvideo[height<=1440]+bestaudio/best[height<=1440]',
        '1080p': 'bestvideo[height<=1080]+bestaudio/best[height<=1080]',
        '720p': 'bestvideo[height<=720]+bestaudio/best[height<=720]',
        '480p': 'bestvideo[height<=480]+bestaudio/best[height<=480]',
    }
    cmd.extend(['-f', format_map.get(quality, format_map['1080p'])])
    cmd.extend(['--merge-output-format', 'mp4'])
    cmd.extend(['--audio-quality', audio_bitrate.replace('k', '')])
    
    # Playlist handling
    cmd.append('--yes-playlist')
    
    # Range selection
    if range_spec:
        start, end = map(int, range_spec.split('-'))
        cmd.extend(['--playlist-start', str(start)])
        cmd.extend(['--playlist-end', str(end)])
    elif max_videos:
        cmd.extend(['--playlist-end', str(max_videos)])
    
    # Keyword filtering (done via match-filter)
    if filter_keyword:
        cmd.extend(['--match-filter', f'title ~= "(?i){filter_keyword}"'])
    
    # Captions
    if captions:
        if caption_langs is None:
            caption_langs = ['en', 'pl', 'es']
        cmd.extend([
            '--write-subs',
            '--write-auto-subs',
            '--sub-langs', ','.join(caption_langs)
            # Native subtitle formats (vtt, srt) are used
        ])
    
    # Metadata
    cmd.extend([
        '--write-info-json',
        '--write-thumbnail'
    ])
    
    # Progress and resume
    cmd.append('--newline')
    cmd.append('--continue')
    cmd.append('--no-overwrites')
    
    # Error handling - skip unavailable videos
    cmd.append('--ignore-errors')
    
    # Add URL
    cmd.append(url)
    
    print(f"\n🚀 Starting playlist download...")
    print(f"📁 Output directory: {playlist_dir}")
    print(f"🎬 Quality: {quality}")
    print(f"🎵 Audio: {audio_bitrate}")
    if range_spec:
        print(f"📊 Range: Videos {range_spec}")
    elif max_videos:
        print(f"📊 Limit: First {max_videos} videos")
    if filter_keyword:
        print(f"🔍 Filter: '{filter_keyword}'")
    print("\n" + "=" * 70)

    # Setup log file and progress tracker
    log_file = playlist_dir / "playlist_download.log"
    progress_tracker = ProgressTracker(log_file=log_file)

    # Setup subprocess cleanup handlers
    process_ref, cleanup = setup_subprocess_cleanup()

    # Track statistics
    downloaded = 0
    skipped = 0
    failed = 0

    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        process_ref['proc'] = process

        for line in process.stdout:
            line = line.strip()
            if line:
                # Log all output to file
                progress_tracker.log_line(line)

                if '[download]' in line:
                    if 'Destination:' in line:
                        downloaded += 1
                        print(f"\n📥 Video {downloaded}: {line.split('Destination:')[1].strip()}")
                    elif '%' in line:
                        # Check for milestone
                        percent = progress_tracker.parse_progress(line)
                        if percent:
                            milestone = progress_tracker.should_show_milestone(percent)
                            if milestone:
                                print(f"⬇️  Video {downloaded}: {milestone}% complete")
                    elif 'has already been downloaded' in line:
                        print(f"\n{line}")
                elif 'ERROR' in line:
                    failed += 1
                    print(f"\n❌ {line}")
                elif 'Skipping' in line:
                    skipped += 1
                    print(f"\n⏭️  {line}")
                elif '[info]' in line or 'Merging' in line:
                    print(f"\n{line}")

        process.wait()

        print("\n" + "=" * 70)
        print(f"✅ Playlist download complete!")
        print(f"   Downloaded: {downloaded}")
        print(f"   Skipped: {skipped}")
        print(f"   Failed: {failed}")

        # Clean up log file on success (if no failures)
        if failed == 0:
            cleanup_log_on_success(log_file)

    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
        print("   Run the same command again to resume.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Download failed: {e}", file=sys.stderr)
        print(f"📄 Full logs: {log_file}")
        sys.exit(1)
    finally:
        cleanup()
    
    # Clean up fragments
    cleaned = cleanup_fragments(playlist_dir)
    if cleaned:
        print(f"🧹 Cleaned up {len(cleaned)} fragment files")
    
    return {
        'playlist_dir': str(playlist_dir),
        'downloaded': downloaded,
        'skipped': skipped,
        'failed': failed
    }


def main():
    parser = argparse.ArgumentParser(
        description='Download playlists with filtering and range selection',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download entire playlist
  %(prog)s "https://youtube.com/playlist?list=xyz"
  
  # Download first 10 videos
  %(prog)s URL --max-videos 10
  
  # Download videos 5-15
  %(prog)s URL --range 5-15
  
  # Filter by keyword (case-insensitive)
  %(prog)s URL --filter "tutorial"
  
  # Lower quality to save space
  %(prog)s URL --quality 720p --max-videos 20
        """
    )
    
    parser.add_argument(
        'url',
        help='Playlist URL'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output directory (default: auto-detect)'
    )
    
    parser.add_argument(
        '--quality', '-q',
        default='1080p',
        choices=['4K', '2160p', '1440p', '1080p', '720p', '480p'],
        help='Video quality (default: 1080p)'
    )
    
    parser.add_argument(
        '--audio-bitrate',
        default='320k',
        choices=['320k', '256k', '192k', '128k'],
        help='Audio bitrate (default: 320k)'
    )
    
    parser.add_argument(
        '--range',
        help='Video range to download (e.g., "1-10", "5-20")'
    )
    
    parser.add_argument(
        '--max-videos',
        type=int,
        help='Maximum number of videos to download'
    )
    
    parser.add_argument(
        '--filter',
        dest='filter_keyword',
        help='Filter videos by keyword in title'
    )
    
    parser.add_argument(
        '--no-captions',
        dest='captions',
        action='store_false',
        help='Skip caption download'
    )
    
    parser.add_argument(
        '--caption-langs',
        default='en,pl,es',
        help='Comma-separated caption languages (default: en,pl,es)'
    )
    
    args = parser.parse_args()
    
    try:
        caption_langs = args.caption_langs.split(',') if args.captions else None
        
        summary = download_playlist(
            url=args.url,
            output_dir=args.output,
            quality=args.quality,
            audio_bitrate=args.audio_bitrate,
            range_spec=args.range,
            max_videos=args.max_videos,
            filter_keyword=args.filter_keyword,
            captions=args.captions,
            caption_langs=caption_langs
        )
        
        print(f"\n📁 Files saved to: {summary['playlist_dir']}")
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
