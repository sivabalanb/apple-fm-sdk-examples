"""
Pytest configuration and shared fixtures.
"""

import sys
from pathlib import Path

# Add repo root to path so imports work correctly
repo_root = Path(__file__).parent.parent
sys.path.insert(0, str(repo_root))

pytest_plugins = []
