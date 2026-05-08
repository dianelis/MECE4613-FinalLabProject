#!/usr/bin/env python3
"""Start the combined HMI, camera stream, QR scanner, and Part B server."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from robot.web_app import main


if __name__ == '__main__':
    main()

