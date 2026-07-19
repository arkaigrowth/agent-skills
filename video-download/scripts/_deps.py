"""
Shared dependency management and utilities for video-download skill.
Handles yt-dlp installation, validation, and size estimation.
"""

import os
import sys
import subprocess
import json
import re
import atexit
import signal
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from datetime import datetime


class DependencyError(Exception):
    """Raised when a required dependency is missing."""
    pass


def check_python_version():
    """
    Check if Python version meets requirements (3.7+).
    Exits with error message if version is too old.
    """
    if sys.version_info < (3, 7):
        print("❌ Error: Python 3.7+ required", file=sys.stderr)
        print(f"   Found: Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}", file=sys.stderr)
        print("   Please upgrade Python or use python3 command", file=sys.stderr)
        sys.exit(1)


def check_ytdlp():
    """Check if yt-dlp is available."""
    try:
        subprocess.run(['yt-dlp', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def ensure_ytdlp():
    """Ensure yt-dlp is installed, install if missing."""
    if check_ytdlp():
        return True
    
    print("📦 Installing yt-dlp...")
    try:
        subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '--break-system-packages', 'yt-dlp'],
            check=True,
            capture_output=True
        )
        print("✅ yt-dlp installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        raise DependencyError(
            f"Failed to install yt-dlp.\n"
            f"Error: {e.stderr.decode()}\n"
            f"Try manually: pip install yt-dlp"
        )


def detect_environment():
    """
    Detect the default download directory.

    Resolution order:
    1. VIDEO_DOWNLOAD_DIR environment variable, if set.
    2. ~/Movies/VIDEO_DOWNLOAD when a home Movies folder exists (macOS).
    3. /mnt/user-data/outputs/video-downloads (Claude Desktop fallback).
    """
    # Explicit override via environment variable
    env_dir = os.environ.get('VIDEO_DOWNLOAD_DIR')
    if env_dir:
        env_path = Path(env_dir).expanduser()
        env_path.mkdir(parents=True, exist_ok=True)
        return str(env_path)

    # macOS default under the current user's home directory
    mac_path = Path.home() / 'Movies' / 'VIDEO_DOWNLOAD'
    if mac_path.parent.exists():  # Check if Movies folder exists
        mac_path.mkdir(parents=True, exist_ok=True)
        return str(mac_path)

    # Default to Claude Desktop outputs
    claude_path = Path('/mnt/user-data/outputs/video-downloads')
    claude_path.mkdir(parents=True, exist_ok=True)
    return str(claude_path)


def estimate_size(duration_seconds, quality='1080p', audio_only=False):
    """
    Estimate download size based on duration and quality.
    
    Args:
        duration_seconds: Video duration in seconds
        quality: Video quality (4K, 1440p, 1080p, 720p, 480p)
        audio_only: If True, estimate audio size only
        
    Returns:
        dict with size_mb, size_gb, and bitrate_mbps
    """
    # Bitrate estimates (Mbps) based on quality
    bitrates = {
        '4K': 25.0,
        '2160p': 25.0,
        '1440p': 12.0,
        '1080p': 8.0,
        '720p': 5.0,
        '480p': 2.5,
        '360p': 1.0,
    }
    
    # Audio bitrate (320kbps default)
    audio_bitrate = 0.32  # Mbps
    
    if audio_only:
        bitrate = audio_bitrate
    else:
        bitrate = bitrates.get(quality, 8.0) + audio_bitrate
    
    # bitrate is in megabits per second, duration in seconds.
    # megabits = bitrate * duration_seconds; divide by 8 for megabytes.
    size_mb = (bitrate * duration_seconds) / 8
    size_gb = size_mb / 1024
    
    return {
        'size_mb': round(size_mb, 1),
        'size_gb': round(size_gb, 2),
        'bitrate_mbps': round(bitrate, 2)
    }


def format_duration(seconds):
    """
    Convert seconds to human-readable duration.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Formatted string (e.g., "45:23" or "1h 23m 45s")
    """
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours}h {minutes}m {secs}s"
    elif minutes > 0:
        return f"{minutes}:{secs:02d}"
    else:
        return f"{secs}s"


def format_size(bytes_size):
    """
    Convert bytes to human-readable size.
    
    Args:
        bytes_size: Size in bytes
        
    Returns:
        Formatted string (e.g., "1.2GB" or "850MB")
    """
    gb = bytes_size / (1024 ** 3)
    if gb >= 1:
        return f"{gb:.1f}GB"
    
    mb = bytes_size / (1024 ** 2)
    if mb >= 1:
        return f"{mb:.0f}MB"
    
    kb = bytes_size / 1024
    return f"{kb:.0f}KB"


def parse_url_type(url):
    """
    Determine if URL is a video, playlist, or channel.
    
    Args:
        url: Video/playlist URL
        
    Returns:
        'video', 'playlist', or 'channel'
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    
    # YouTube patterns
    if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
        if 'list' in query:
            return 'playlist'
        if '/channel/' in parsed.path or '/c/' in parsed.path or '/@' in parsed.path:
            return 'channel'
        return 'video'
    
    # Default to video for other platforms
    return 'video'


def sanitize_filename(filename, max_length=80):
    """
    Sanitize filename for filesystem safety.

    Args:
        filename: Original filename
        max_length: Maximum length for filename

    Returns:
        Safe filename
    """
    # Remove or replace problematic characters
    # Handle special colons (： Japanese, etc.)
    filename = filename.replace('：', '-').replace(':', '-')
    filename = re.sub(r'[<>"/\\|?*]', '_', filename)
    # Limit length
    if len(filename) > max_length:
        filename = filename[:max_length].rstrip()
    return filename.strip()


def get_video_metadata(url):
    """
    Fetch video metadata (title, creator, id) without downloading.

    Args:
        url: Video URL

    Returns:
        dict with 'title', 'creator', 'video_id'
    """
    ensure_ytdlp()

    cmd = [
        'yt-dlp',
        '--dump-json',
        '--no-playlist',
        '--skip-download',
        url
    ]

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True, timeout=30)
        metadata = json.loads(result.stdout)

        return {
            'title': metadata.get('title', 'Unknown'),
            'creator': metadata.get('uploader', metadata.get('channel', 'Unknown')),
            'video_id': metadata.get('id', generate_video_id(url))
        }
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, json.JSONDecodeError):
        # Fallback: use URL-based ID
        return {
            'title': 'Unknown',
            'creator': 'Unknown',
            'video_id': generate_video_id(url)
        }


def create_video_folder_name(url, metadata=None):
    """
    Create human-readable folder name from video metadata.
    Format: "{creator} - {title} ({video_id})"

    Args:
        url: Video URL
        metadata: Optional metadata dict (if None, will fetch)

    Returns:
        Sanitized folder name string
    """
    if metadata is None:
        metadata = get_video_metadata(url)

    title = sanitize_filename(metadata['title'], max_length=60)
    creator = sanitize_filename(metadata['creator'], max_length=30)
    video_id = metadata['video_id']

    folder_name = f"{creator} - {title} ({video_id})"

    # Final sanitization and length check
    folder_name = sanitize_filename(folder_name, max_length=120)

    return folder_name


def generate_video_id(url):
    """
    Extract or generate a unique ID for the video.
    
    Args:
        url: Video URL
        
    Returns:
        Unique identifier string
    """
    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    
    # YouTube video ID
    if 'youtube.com' in parsed.netloc:
        if 'v' in query:
            return query['v'][0]
    elif 'youtu.be' in parsed.netloc:
        return parsed.path.strip('/')
    
    # For other platforms, use hash of URL
    import hashlib
    return hashlib.md5(url.encode()).hexdigest()[:12]


def check_mac_tag_support():
    """Check if macOS tag command is available."""
    try:
        subprocess.run(['tag', '--version'], capture_output=True, check=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def apply_finder_tag(filepath, tag_name='video'):
    """
    Apply macOS Finder tag to a file.
    
    Args:
        filepath: Path to file
        tag_name: Tag name to apply (default: 'video')
        
    Returns:
        True if successful, False otherwise
    """
    if not check_mac_tag_support():
        # Silently skip on non-Mac systems
        return False
    
    try:
        subprocess.run(
            ['tag', '-a', tag_name, str(filepath)],
            check=True,
            capture_output=True
        )
        return True
    except subprocess.CalledProcessError:
        # Fallback: Try xattr method
        try:
            plist_data = f'("video",0)'.encode()
            subprocess.run(
                ['xattr', '-w', 'com.apple.metadata:_kMDItemUserTags', plist_data, str(filepath)],
                check=True,
                capture_output=True
            )
            return True
        except:
            return False


def find_fragments(directory):
    """
    Find orphaned download fragments (.part, .ytdl, .temp files).
    
    Args:
        directory: Directory to search
        
    Returns:
        List of fragment file paths
    """
    directory = Path(directory)
    if not directory.exists():
        return []
    
    fragments = []
    patterns = ['*.part', '*.ytdl', '*.temp', '*.f*']
    
    for pattern in patterns:
        fragments.extend(directory.rglob(pattern))
    
    return [str(f) for f in fragments]


def cleanup_fragments(directory, dry_run=False):
    """
    Clean up orphaned download fragments.

    Args:
        directory: Directory to clean
        dry_run: If True, only list files without deleting

    Returns:
        List of cleaned files
    """
    fragments = find_fragments(directory)

    if not fragments:
        return []

    if dry_run:
        return fragments

    cleaned = []
    for fragment in fragments:
        try:
            Path(fragment).unlink()
            cleaned.append(fragment)
        except Exception:
            pass

    return cleaned


class ProgressTracker:
    """Track download progress and show milestones."""

    def __init__(self, log_file=None):
        self.log_file = log_file
        self.last_percent = 0
        self.milestones = {10, 25, 50, 75, 90, 100}
        self.shown_milestones = set()

    def parse_progress(self, line):
        """
        Parse yt-dlp progress line and extract percentage.

        Args:
            line: Progress line from yt-dlp

        Returns:
            float percentage (0-100) or None
        """
        # Match patterns like: [download]  45.2% of ~1.23GiB
        match = re.search(r'\[download\]\s+(\d+\.?\d*)%', line)
        if match:
            return float(match.group(1))
        return None

    def should_show_milestone(self, percent):
        """Check if this percentage crosses a milestone."""
        for milestone in self.milestones:
            if percent >= milestone and milestone not in self.shown_milestones:
                self.shown_milestones.add(milestone)
                return milestone
        return None

    def log_line(self, line):
        """Write line to log file if configured."""
        if self.log_file:
            try:
                with open(self.log_file, 'a') as f:
                    f.write(line + '\n')
            except:
                pass


def cleanup_log_on_success(log_file):
    """
    Replace log file with success message on successful download.

    Args:
        log_file: Path to log file
    """
    if not log_file or not Path(log_file).exists():
        return

    try:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        success_msg = (
            f"✅ Download completed successfully on {timestamp}.\n"
            f"Logs cleared for space management - no issues observed.\n"
        )
        Path(log_file).write_text(success_msg)
    except:
        pass


def setup_subprocess_cleanup(process_var_name='process'):
    """
    Setup cleanup handlers for subprocess to prevent zombies.

    Args:
        process_var_name: Name of the process variable (for error messages)

    Returns:
        cleanup function
    """
    process_ref = {'proc': None}

    def cleanup():
        """Terminate and wait for process to exit."""
        proc = process_ref['proc']
        if proc and proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
            except:
                pass

    # Register cleanup handlers
    atexit.register(cleanup)

    def sigterm_handler(signum, frame):
        cleanup()
        sys.exit(128 + signum)

    signal.signal(signal.SIGTERM, sigterm_handler)
    signal.signal(signal.SIGINT, sigterm_handler)

    return process_ref, cleanup
