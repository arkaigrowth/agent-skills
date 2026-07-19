#!/usr/bin/env python3
"""
Clean up orphaned download fragments from failed or interrupted downloads.
Finds and removes .part, .ytdl, .temp files.
"""

import argparse
import sys
from pathlib import Path
from _deps import check_python_version, find_fragments, cleanup_fragments, format_size

# Check Python version before proceeding
check_python_version()


def main():
    parser = argparse.ArgumentParser(
        description='Clean up orphaned download fragments',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Dry run - see what would be deleted
  %(prog)s ~/Movies/VIDEO_DOWNLOAD --dry-run
  
  # Actually delete fragments
  %(prog)s ~/Movies/VIDEO_DOWNLOAD
  
  # Clean specific subdirectory
  %(prog)s ~/Movies/VIDEO_DOWNLOAD/video_abc123
        """
    )
    
    parser.add_argument(
        'directory',
        help='Directory to clean'
    )
    
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Show what would be deleted without actually deleting'
    )
    
    args = parser.parse_args()
    
    try:
        directory = Path(args.directory)
        if not directory.exists():
            print(f"❌ Directory not found: {directory}", file=sys.stderr)
            sys.exit(1)
        
        fragments = find_fragments(directory)
        
        if not fragments:
            print(f"✅ No fragments found in {directory}")
            return
        
        total_size = sum(Path(f).stat().st_size for f in fragments if Path(f).exists())
        
        print(f"\n🔍 Found {len(fragments)} fragment files ({format_size(total_size)}):")
        print("=" * 70)
        
        for fragment in fragments:
            path = Path(fragment)
            if path.exists():
                size = format_size(path.stat().st_size)
                print(f"  {path.name} ({size})")
        
        if args.dry_run:
            print("\n⚠️  DRY RUN - No files were deleted")
            print("   Run without --dry-run to actually delete these files")
        else:
            print("\n🧹 Cleaning up...")
            cleaned = cleanup_fragments(directory)
            print(f"✅ Deleted {len(cleaned)} fragment files ({format_size(total_size)} freed)")
        
        print("=" * 70)
        
    except Exception as e:
        print(f"❌ Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
