#!/usr/bin/env python3
"""
Convert Whisper JSON transcript to human-readable markdown format.
Creates sentence-level timestamps for easy navigation.
"""

import argparse
import json
import sys
import re
from pathlib import Path
from datetime import timedelta
from _deps import check_python_version

# Check Python version before proceeding
check_python_version()


def format_timestamp(seconds):
    """
    Convert seconds to timestamp format [HH:MM:SS] or [MM:SS].

    Args:
        seconds: Time in seconds (float)

    Returns:
        Formatted timestamp string
    """
    td = timedelta(seconds=int(seconds))
    total_seconds = int(td.total_seconds())
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    secs = total_seconds % 60

    if hours > 0:
        return f"[{hours:02d}:{minutes:02d}:{secs:02d}]"
    else:
        return f"[{minutes:02d}:{secs:02d}]"


def split_into_sentences(text):
    """
    Split text into sentences using basic punctuation rules.

    Args:
        text: Input text

    Returns:
        List of sentences
    """
    # Split on sentence-ending punctuation followed by space or newline
    sentences = re.split(r'([.!?]+[\s\n]+)', text)

    # Recombine sentences with their punctuation
    result = []
    for i in range(0, len(sentences) - 1, 2):
        sentence = sentences[i] + (sentences[i + 1] if i + 1 < len(sentences) else '')
        sentence = sentence.strip()
        if sentence:
            result.append(sentence)

    # Handle last sentence if it doesn't end with punctuation
    if len(sentences) % 2 == 1 and sentences[-1].strip():
        result.append(sentences[-1].strip())

    return result if result else [text]


def generate_markdown_transcript(json_path, output_path=None, interval=5):
    """
    Generate markdown transcript from Whisper JSON output.

    Args:
        json_path: Path to JSON transcript file
        output_path: Path to output markdown file (None = auto-generate)
        interval: Minimum seconds between timestamps (default: 5)

    Returns:
        Path to generated markdown file
    """
    json_path = Path(json_path)

    if not json_path.exists():
        raise FileNotFoundError(f"Transcript file not found: {json_path}")

    # Read JSON transcript
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Handle nested transcript structure from video-ops
    if 'transcript' in data:
        transcript_data = data['transcript']
        text = transcript_data.get('text', '')
        segments = transcript_data.get('segments', [])
        language = transcript_data.get('language', data.get('language', 'unknown'))
    else:
        # Handle flat structure
        text = data.get('text', '')
        segments = data.get('segments', [])
        language = data.get('language', 'unknown')

    # Get video info from parent directory if available OR from JSON
    video_dir = json_path.parent
    info_files = list(video_dir.glob('*.info.json'))

    title = "Unknown"
    creator = "Unknown"
    duration = "Unknown"
    date = "Unknown"

    # Try to get duration from video-ops JSON structure first
    if 'video' in data and 'duration' in data['video']:
        duration = format_timestamp(data['video']['duration']).strip('[]')

    if info_files:
        with open(info_files[0], 'r', encoding='utf-8') as f:
            info = json.load(f)
            title = info.get('title', 'Unknown')
            creator = info.get('uploader', info.get('channel', 'Unknown'))
            if 'duration' in info and duration == "Unknown":
                duration = format_timestamp(info['duration']).strip('[]')
            date = info.get('upload_date', 'Unknown')
            if date != 'Unknown' and len(date) == 8:  # Format: YYYYMMDD
                date = f"{date[:4]}-{date[4:6]}-{date[6:]}"

    # Build markdown content
    md_lines = [
        f"# Transcript: {title}",
        "",
        f"**Creator:** {creator}  ",
        f"**Duration:** {duration}  ",
        f"**Date:** {date}  ",
        f"**Language:** {language}",
        "",
        "---",
        ""
    ]

    # Process segments with sentence-level timestamps
    last_timestamp = -interval - 1

    for segment in segments:
        segment_start = segment.get('start', 0)
        segment_text = segment.get('text', '').strip()

        if not segment_text:
            continue

        # Split segment into sentences
        sentences = split_into_sentences(segment_text)

        for sentence in sentences:
            # Add timestamp if enough time has passed or it's a new segment
            if segment_start - last_timestamp >= interval:
                md_lines.append(f"{format_timestamp(segment_start)} {sentence}")
                last_timestamp = segment_start
            else:
                # Continue on same line or new line depending on length
                if md_lines and not md_lines[-1].endswith(('.', '!', '?')):
                    md_lines[-1] += ' ' + sentence
                else:
                    md_lines.append(sentence)

    # Add footer
    word_count = len(text.split())
    md_lines.extend([
        "",
        "---",
        "",
        f"**Total words:** {word_count:,}  ",
        f"**Transcript source:** {json_path.name}  ",
        f"**Generated with:** Whisper ASR"
    ])

    # Determine output path
    if output_path is None:
        output_path = json_path.with_suffix('.md')
    else:
        output_path = Path(output_path)

    # Write markdown file
    md_content = '\n'.join(md_lines)
    output_path.write_text(md_content, encoding='utf-8')

    return output_path


def main():
    parser = argparse.ArgumentParser(
        description='Convert Whisper JSON transcript to human-readable markdown',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert transcript.json to transcript.md
  %(prog)s transcript.json

  # Specify output file
  %(prog)s transcript.json -o readable_transcript.md

  # Change timestamp interval (default: 5 seconds)
  %(prog)s transcript.json --interval 10
        """
    )

    parser.add_argument(
        'json_file',
        help='Path to Whisper JSON transcript file'
    )

    parser.add_argument(
        '-o', '--output',
        help='Output markdown file path (default: same name with .md extension)'
    )

    parser.add_argument(
        '--interval',
        type=int,
        default=5,
        help='Minimum seconds between timestamps (default: 5)'
    )

    args = parser.parse_args()

    try:
        output_path = generate_markdown_transcript(
            json_path=args.json_file,
            output_path=args.output,
            interval=args.interval
        )

        print(f"✅ Markdown transcript generated: {output_path}")
        print(f"📄 File size: {output_path.stat().st_size // 1024}KB")

    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
