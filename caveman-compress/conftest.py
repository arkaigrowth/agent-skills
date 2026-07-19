"""Pytest bootstrap: put the skill root on sys.path so `scripts` imports resolve.

Keeps the test suite runnable from the skill directory without installing the
package.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
