#!/usr/bin/env python3
"""Utils to parse data"""

import random
import time


def random_wait(how_long=5, max_diff=2):
    """Wait random seconds."""

    max_diff = min(how_long, max_diff)
    offset = random.random() * max_diff * 2 - max_diff
    time.sleep(max(0, how_long + offset))
