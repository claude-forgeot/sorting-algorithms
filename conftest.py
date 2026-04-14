"""Root conftest: configures pytest for the project.

- Adds the project root to sys.path so tests can import top-level packages
  (sorting, visualization, benchmarks) directly.
- Forces pygame to run headless during tests via SDL_VIDEODRIVER=dummy.
  Without this, pygame tries to open an X display and tests hang in CI.
"""

import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")

_ROOT = Path(__file__).parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
