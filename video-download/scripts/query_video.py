#!/usr/bin/env python3
"""
Query video metadata without downloading.
Provides pre-flight information: title, duration, estimated size, available formats.
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from _deps import (
    check_python_version, ensure_ytdlp, parse_url_type, estimate_size,
    format_duration, format_size
)

# Check Python version before proceeding
check_python_version()


def query_video(url, quality='1080p'):
    """
    Query video metadata using yt-dlp without downloading.
    
    Args:
        url: Video or playlist URL
        quality: Target quality for size estimation
        
    Returns:
        dict with video metadata and size estimates
    """
    ensure_ytdlp()
    
    url_type = parse_url_type(url)
    
    # Query metadata without downloading
    cmd = [
        'yt-dlp',
        '--dump-json',
        '--no-playlist' if url_type == 'video' else '--yes-playlist',
        url
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to query video: {e.stderr}")
    
    # Parse JSON output (one line per video)
    videos = []
    for line in result.stdout.strip().split('\n'):
        if line:
            videos.append(json.loads(line))
    
    # Process results
    if url_type == 'video':
        return process_single_video(videos[0], quality)
    else:
        return process_playlist(videos, quality, url)


def process_single_video(video_info, quality):
    """Process metadata for a single video."""
    duration = video_info.get('duration', 0)
    title = video_info.get('title', 'Unknown')
    uploader = video_info.get('uploader', 'Unknown')
    upload_date = video_info.get('upload_date', 'Unknown')
    view_count = video_info.get('view_count', 0)
    
    # Check available formats
    formats = video_info.get('formats', [])
    available_qualities = set()
    has_captions = bool(video_info.get('subtitles') or video_info.get('automatic_captions'))
    
    for fmt in formats:
        height = fmt.get('height')
        if height:
            if height >= 2160:
                available_qualities.add('4K')
            elif height >= 1440:
                available_qualities.add('1440p')
            elif height >= 1080:
                available_qualities.add('1080p')
            elif height >= 720:
                available_qualities.add('720p')
    
    # Estimate sizes for different qualities
    size_estimates = {}
    for q in ['4K', '1440p', '1080p', '720p', 'audio']:
        if q == 'audio':
            est = estimate_size(duration, audio_only=True)
        else:
            est = estimate_size(duration, quality=q)
        size_estimates[q] = est
    
    return {
        'type': 'video',
        'title': title,
        'uploader': uploader,
        'upload_date': upload_date,
        'duration_seconds': duration,
        'duration_formatted': format_duration(duration),
        'view_count': view_count,
        'available_qualities': sorted(available_qualities, reverse=True),
        'has_captions': has_captions,
        'size_estimates': size_estimates,
        'url': video_info.get('webpage_url', video_info.get('url')),
        'video_id': video_info.get('id', 'unknown')
    }


def process_playlist(videos, quality, playlist_url):
    """Process metadata for a playlist."""
    total_duration = sum(v.get('duration', 0) for v in videos)
    
    # Get playlist title (from first video's playlist info)
    playlist_title = videos[0].get('playlist_title', 'Unknown Playlist')
    
    # Estimate total sizes
    size_estimates = {}
    for q in ['4K', '1440p', '1080p', '720p']:
        est = estimate_size(total_duration, quality=q)
        size_estimates[q] = est
    
    # Top 5 videos for preview
    top_videos = []
    for v in videos[:5]:
        duration = v.get('duration', 0)
        est = estimate_size(duration, quality=quality)
        top_videos.append({
            'title': v.get('title', 'Unknown'),
            'duration': format_duration(duration),
            'size_estimate': f"{est['size_mb']}MB"
        })
    
    return {
        'type': 'playlist',
        'playlist_title': playlist_title,
        'video_count': len(videos),
        'total_duration_seconds': total_duration,
        'total_duration_formatted': format_duration(total_duration),
        'size_estimates': size_estimates,
        'top_videos': top_videos,
        'url': playlist_url
    }


def print_video_info(info):
    """Print video information in human-readable format."""
    print(f"\n📹 Video: {info['title']}")
    print("=" * 70)
    print(f"Uploader:     {info['uploader']}")
    print(f"Duration:     {info['duration_formatted']}")
    print(f"Upload Date:  {info['upload_date']}")
    print(f"Views:        {info['view_count']:,}")
    print(f"Captions:     {'✅ Available' if info['has_captions'] else '❌ Not available'}")
    
    print(f"\n📊 Available Qualities: {', '.join(info['available_qualities'])}")
    
    print("\n💾 Estimated Download Sizes:")
    print("-" * 70)
    for quality, est in info['size_estimates'].items():
        if quality == 'audio':
            print(f"  Audio only (320kbps):  ~{est['size_mb']}MB")
        else:
            stars = " ⭐" if quality == '1080p' else ""
            print(f"  {quality:<6} ~{est['size_gb']:.1f}GB ({est['size_mb']}MB){stars}")
    print("=" * 70)


def print_playlist_info(info):
    """Print playlist information in human-readable format."""
    print(f"\n🎬 Playlist: {info['playlist_title']}")
    print("=" * 70)
    print(f"Videos:        {info['video_count']}")
    print(f"Total Duration: {info['total_duration_formatted']}")
    
    print("\n⚠️  WARNING: This is a playlist download")
    print(f"   Downloading {info['video_count']} videos will take significant time and storage.")
    
    print("\n💾 Estimated Total Sizes:")
    print("-" * 70)
    for quality, est in info['size_estimates'].items():
        stars = " ⭐" if quality == '1080p' else ""
        print(f"  {quality:<6} ~{est['size_gb']:.1f}GB{stars}")
    
    print(f"\n📋 Top 5 Videos:")
    print("-" * 70)
    for i, video in enumerate(info['top_videos'], 1):
        print(f"  {i}. {video['title']}")
        print(f"     Duration: {video['duration']}, Est. size: {video['size_estimate']}")
    
    print("\n💡 Options:")
    print("  [1] Download all videos")
    print("  [2] Download first 10 videos")
    print("  [3] Specify range (e.g., videos 1-20)")
    print("  [4] Cancel")
    print("=" * 70)


def main():
    parser = argparse.ArgumentParser(
        description='Query video metadata without downloading',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://youtube.com/watch?v=abc123"
  %(prog)s "https://youtube.com/playlist?list=xyz" --quality 720p
  %(prog)s URL --json > metadata.json
        """
    )
    
    parser.add_argument(
        'url',
        help='Video or playlist URL'
    )
    
    parser.add_argument(
        '--quality',
        default='1080p',
        choices=['4K', '1440p', '1080p', '720p', '480p'],
        help='Target quality for size estimation (default: 1080p)'
    )
    
    parser.add_argument(
        '--json',
        action='store_true',
        help='Output as JSON instead of human-readable format'
    )
    
    args = parser.parse_args()
    
    try:
        info = query_video(args.url, quality=args.quality)
        
        if args.json:
            print(json.dumps(info, indent=2))
        else:
            if info['type'] == 'video':
                print_video_info(info)
            else:
                print_playlist_info(info)
                
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
