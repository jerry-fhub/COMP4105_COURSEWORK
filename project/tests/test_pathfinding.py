from __future__ import annotations

import unittest

from src.agents.pathfinding import a_star


class PathfindingTests(unittest.TestCase):
    def test_a_star_reaches_goal(self) -> None:
        obstacles = {(1, 1)}

        def neighbors(position: tuple[int, int]) -> list[tuple[int, int]]:
            x, y = position
            candidates = [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]
            return [
                (nx, ny)
                for nx, ny in candidates
                if 0 <= nx < 4 and 0 <= ny < 4 and (nx, ny) not in obstacles
            ]

        path = a_star((0, 0), (3, 3), neighbors)
        self.assertEqual(path[0], (0, 0))
        self.assertEqual(path[-1], (3, 3))
        self.assertGreater(len(path), 1)


if __name__ == "__main__":
    unittest.main()
