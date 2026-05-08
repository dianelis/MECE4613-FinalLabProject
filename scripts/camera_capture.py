#!/usr/bin/env python3
"""Capture camera frames to the shared robot_stream.jpg file."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from robot.camera import main


if __name__ == '__main__':
    main()

