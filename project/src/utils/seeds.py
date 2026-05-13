from __future__ import annotations

import random

import numpy as np


def seed_everything(seed: int) -> random.Random:
    """Seed Python and NumPy and return a Random instance for local use."""
    random.seed(seed)
    np.random.seed(seed)
    return random.Random(seed)
