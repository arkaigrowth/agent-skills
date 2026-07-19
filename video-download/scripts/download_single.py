#!/usr/bin/env python3
"""
Download single video with full configurability.
Supports quality selection, audio extraction, caption download, and macOS tagging.
"""

import argparse
import json
import sys
import subprocess
from pathlib import Path
from _deps import (
    check_python_version, ensure_ytdlp, detect_environment, sanitize_filename,
    generate_video_id, apply_finder_tag, cleanup_fragments,
    get_video_metadata, create_video_folder_name,
    ProgressTracker, cleanup_log_on_success, setup_subprocess_cleanup
)

# Check Python version before proceeding
check_python_version()


def download_video(
    url,
    output_dir=None,
    quality='1080p',
    audio_bitrate='320k',
    audio_only=False,
    captions=True,
    caption_langs=None,
    keep_video=True,
    apply_tag=True,
    tag_name='video'
):
    """
    Download a single video with specified options.
    
    Args:
        url: Video URL
        output_dir: Download directory (None = auto-detect)
        quality: Video quality (4K, 1440p, 1080p, 720p, audio)
        audio_bitrate: Audio bitrate (320k, 192k, 128k)
        audio_only: Download audio only
        captions: Download captions/subtitles
        caption_langs: List of caption languages (None = en,pl,es)
        keep_video: Keep video after download
        apply_tag: Apply macOS Finder tag
        tag_name: Tag name to apply
        
    Returns:
        dict with download info
    """
    ensure_ytdlp()

    # Determine output directory
    if output_dir is None:
        output_dir = detect_environment()
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Fetch metadata and create human-readable folder name
    print("📡 Fetching video metadata...")
    folder_name = create_video_folder_name(url)
    video_dir = output_dir / folder_name
    video_dir.mkdir(parents=True, exist_ok=True)
    
    # Build yt-dlp command
    cmd = ['yt-dlp']
    
    # Output template
    output_template = str(video_dir / '%(title)s.%(ext)s')
    cmd.extend(['-o', output_template])
    
    # Quality selection
    if audio_only:
        cmd.extend([
            '-f', 'bestaudio',
            '--extract-audio',
            '--audio-format', 'mp3',
            '--audio-quality', audio_bitrate.replace('k', '')
        ])
    else:
        # Video + audio format selection
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
    
    # Captions
    if captions:
        if caption_langs is None:
            caption_langs = ['en', 'pl', 'es']
        cmd.extend([
            '--write-subs',
            '--write-auto-subs',
            '--sub-langs', ','.join(caption_langs)
            # Note: Native subtitle formats (vtt, srt) are used
            # Use generate_transcript_md.py to create human-readable transcripts
        ])
    
    # Progress bar
    cmd.append('--newline')  # Each progress update on new line
    
    # Metadata and JSON
    cmd.extend([
        '--write-info-json',  # Save metadata
        '--write-description',  # Save description
        '--write-thumbnail'  # Save thumbnail
    ])
    
    # Resume support
    cmd.append('--continue')  # Resume partial downloads
    cmd.append('--no-overwrites')  # Don't re-download if exists
    
    # Add URL
    cmd.append(url)
    
    print(f"\n🚀 Starting download...")
    print(f"📁 Output directory: {video_dir}")
    print(f"🎬 Quality: {quality if not audio_only else 'Audio only'}")
    print(f"🎵 Audio: {audio_bitrate}")
    print(f"📝 Captions: {'✅ ' + ', '.join(caption_langs) if captions else '❌ Disabled'}")
    print("\n" + "=" * 70)

    # Setup log file and progress tracker
    log_file = video_dir / "download.log"
    progress_tracker = ProgressTracker(log_file=log_file)

    # Setup subprocess cleanup handlers
    process_ref, cleanup = setup_subprocess_cleanup()

    # Run download with progress tracking
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

                # Parse progress
                if '[download]' in line:
                    if '%' in line:
                        # Check for milestone
                        percent = progress_tracker.parse_progress(line)
                        if percent:
                            milestone = progress_tracker.should_show_milestone(percent)
                            if milestone:
                                print(f"⬇️  Downloading... {milestone}% complete")
                    elif 'Destination:' in line or 'has already been downloaded' in line:
                        # Show file destination
                        print(f"\n{line}")
                elif '[info]' in line or 'Merging' in line or 'ERROR' in line:
                    print(f"\n{line}")

        process.wait()

        if process.returncode != 0:
            raise RuntimeError("Download failed - check download.log for details")

        print("\n" + "=" * 70)
        print("✅ Download complete!")

        # Clean up log file on success
        cleanup_log_on_success(log_file)

    except KeyboardInterrupt:
        print("\n\n⚠️  Download interrupted by user")
        print("   Run the same command again to resume from where you left off.")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Download failed: {e}", file=sys.stderr)
        print(f"📄 Full logs: {log_file}")
        sys.exit(1)
    finally:
        cleanup()
    
    # Find downloaded files
    video_files = list(video_dir.glob('*.mp4')) + list(video_dir.glob('*.mp3'))
    caption_files = list(video_dir.glob('*.vtt')) + list(video_dir.glob('*.srt'))
    metadata_files = list(video_dir.glob('*.info.json'))
    
    if not video_files:
        print("⚠️  Warning: No video/audio file found after download")
        return None
    
    video_file = video_files[0]
    
    # Apply macOS tag if requested
    if apply_tag and keep_video:
        if apply_finder_tag(video_file, tag_name):
            print(f"🏷️  Applied '{tag_name}' tag to video")
    
    # Generate summary
    summary = {
        'video_file': str(video_file),
        'video_dir': str(video_dir),
        'caption_files': [str(f) for f in caption_files],
        'metadata_files': [str(f) for f in metadata_files],
        'quality': quality,
        'audio_bitrate': audio_bitrate,
        'audio_only': audio_only,
        'size_bytes': video_file.stat().st_size if video_file.exists() else 0
    }
    
    # Save summary as markdown
    save_summary_md(summary, video_dir)
    
    # Clean up any fragments
    cleaned = cleanup_fragments(video_dir)
    if cleaned:
        print(f"🧹 Cleaned up {len(cleaned)} fragment files")
    
    return summary


def extract_keyframes_with_video_ops(video_file, video_ops_path=None, max_retries=1):
    """
    Extract keyframes using video-ops skill.

    Args:
        video_file: Path to video file
        video_ops_path: Custom path to video-ops skill (None = auto-detect)
        max_retries: Number of retries on failure (default: 1)

    Returns:
        True if successful, False otherwise
    """
    import os

    # Detect video-ops path
    if video_ops_path:
        video_ops_script = Path(video_ops_path) / 'scripts' / 'extract_keyframes.py'
    else:
        video_ops_script = Path.home() / '.claude' / 'skills' / 'video-ops' / 'scripts' / 'extract_keyframes.py'

    if not video_ops_script.exists():
        print("\n💡 video-ops skill not found. To extract keyframes:")
        print("   1. Install video-ops skill to ~/.claude/skills/video-ops/, or")
        print("   2. Use ffmpeg directly:")
        print(f"      ffmpeg -i \"{video_file}\" -vf 'select=eq(pict_type\\,I)' keyframes/frame_%04d.jpg")
        return False

    print("\n🖼️  Extracting keyframes with video-ops...")

    for attempt in range(max_retries + 1):
        try:
            result = subprocess.run(
                ['python3', str(video_ops_script), str(video_file)],
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            if result.returncode == 0:
                print("✅ Keyframes extracted successfully!")
                # Try to show keyframe location from output
                if 'keyframes' in result.stdout.lower():
                    for line in result.stdout.split('\n'):
                        if 'keyframes' in line.lower() or 'saved' in line.lower():
                            print(f"   {line.strip()}")
                return True
            else:
                if attempt < max_retries:
                    print(f"⚠️  Extraction failed (attempt {attempt + 1}/{max_retries + 1}), retrying...")
                else:
                    print(f"❌ Keyframe extraction failed after {max_retries + 1} attempts")
                    if result.stderr:
                        print(f"   Error: {result.stderr.strip()[:200]}")
                    return False

        except subprocess.TimeoutExpired:
            print("⚠️  Keyframe extraction timed out (5 min limit)")
            return False
        except Exception as e:
            print(f"❌ Error during keyframe extraction: {e}")
            return False

    return False


def save_summary_md(summary, video_dir):
    """Save download summary as markdown."""
    video_file = Path(summary['video_file'])
    size_mb = summary['size_bytes'] / (1024 * 1024)
    size_gb = size_mb / 1024
    
    md_content = f"""# Download Summary

## Video File
- **File:** {video_file.name}
- **Size:** {size_gb:.2f}GB ({size_mb:.0f}MB)
- **Quality:** {summary['quality']}
- **Audio:** {summary['audio_bitrate']}
- **Type:** {'Audio only' if summary['audio_only'] else 'Video + Audio'}

## Files
- Video/Audio: `{video_file.name}`
"""
    
    if summary['caption_files']:
        md_content += f"- Captions: {len(summary['caption_files'])} files\n"
        for cap in summary['caption_files']:
            md_content += f"  - `{Path(cap).name}`\n"
    
    if summary['metadata_files']:
        md_content += f"- Metadata: `{Path(summary['metadata_files'][0]).name}`\n"
    
    md_content += f"\n## Location\n`{video_dir}`\n"
    
    summary_path = video_dir / "SUMMARY.md"
    summary_path.write_text(md_content)


def main():
    parser = argparse.ArgumentParser(
        description='Download a single video with full configuration',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download with defaults (1080p, 320kbps audio, captions)
  %(prog)s "https://youtube.com/watch?v=abc123"
  
  # Download 4K quality
  %(prog)s URL --quality 4K
  
  # Download audio only
  %(prog)s URL --audio-only --audio-bitrate 192k
  
  # Custom output directory
  %(prog)s URL --output ~/Downloads/videos
  
  # No captions, don't tag
  %(prog)s URL --no-captions --no-tag
        """
    )
    
    parser.add_argument(
        'url',
        help='Video URL'
    )
    
    parser.add_argument(
        '--output', '-o',
        help='Output directory (default: auto-detect Mac or Claude Desktop)'
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
        '--audio-only',
        action='store_true',
        help='Download audio only (MP3 format)'
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
    
    parser.add_argument(
        '--no-tag',
        dest='apply_tag',
        action='store_false',
        help='Skip macOS Finder tag application'
    )
    
    parser.add_argument(
        '--tag-name',
        default='video',
        help='macOS tag name (default: video)'
    )

    parser.add_argument(
        '--extract-keyframes',
        action='store_true',
        help='Automatically extract keyframes after download (no prompt)'
    )

    parser.add_argument(
        '--no-keyframes',
        action='store_true',
        help='Skip keyframe extraction (no prompt)'
    )

    parser.add_argument(
        '--video-ops-path',
        help='Custom path to video-ops skill (default: ~/.claude/skills/video-ops)'
    )

    args = parser.parse_args()
    
    try:
        caption_langs = args.caption_langs.split(',') if args.captions else None
        
        summary = download_video(
            url=args.url,
            output_dir=args.output,
            quality=args.quality,
            audio_bitrate=args.audio_bitrate,
            audio_only=args.audio_only,
            captions=args.captions,
            caption_langs=caption_langs,
            apply_tag=args.apply_tag,
            tag_name=args.tag_name
        )
        
        if summary:
            print(f"\n📁 Files saved to: {summary['video_dir']}")
            print(f"📄 Summary: {Path(summary['video_dir']) / 'SUMMARY.md'}")

            # Handle keyframe extraction
            video_file = Path(summary['video_file'])
            size_mb = summary['size_bytes'] / (1024 * 1024)

            # Determine if we should extract keyframes
            should_extract = False

            if args.extract_keyframes:
                # Explicitly requested via flag
                should_extract = True
            elif args.no_keyframes:
                # Explicitly skipped via flag
                should_extract = False
            elif sys.stdin.isatty():
                # Interactive terminal - prompt user
                print(f"\n📹 Video: {video_file.name} ({size_mb:.0f}MB)")
                print(f"📁 Location: {summary['video_dir']}\n")
                print("🖼️  Extract keyframes from this video?")
                print("   💡 Tip: Use --extract-keyframes or --no-keyframes to skip this prompt")

                try:
                    response = input("   [Y/n/later]: ").strip().lower()
                    if response in ['y', 'yes', '']:
                        should_extract = True
                    elif response == 'later':
                        print("💡 You can extract keyframes later with video-ops skill")
                except (EOFError, KeyboardInterrupt):
                    print("\n⏭️  Skipping keyframe extraction")
            # else: Non-interactive (agent) - default to False (skip)

            # Extract keyframes if requested
            if should_extract:
                extract_keyframes_with_video_ops(
                    video_file=video_file,
                    video_ops_path=args.video_ops_path,
                    max_retries=1
                )

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
