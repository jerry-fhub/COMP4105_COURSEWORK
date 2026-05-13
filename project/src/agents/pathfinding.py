from __future__ import annotations

import heapq
from typing import Callable

from src.env.models import Position


def manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct_path(came_from: dict[Position, Position], current: Position) -> list[Position]:
    path = [current]
    while current in came_from:
        current = came_from[current]
        path.append(current)
    path.reverse()
    return path


def a_star(
    start: Position,
    goal: Position,
    neighbor_fn: Callable[[Position], list[Position]],
) -> list[Position]:
    if start == goal:
        return [start]

    open_heap: list[tuple[int, int, Position]] = []
    heapq.heappush(open_heap, (0, 0, start))
    came_from: dict[Position, Position] = {}
    g_score = {start: 0}
    tie = 0

    while open_heap:
        _, _, current = heapq.heappop(open_heap)
        if current == goal:
            return reconstruct_path(came_from, current)

        for neighbor in neighbor_fn(current):
            tentative_g = g_score[current] + 1
            if tentative_g >= g_score.get(neighbor, 1_000_000_000):
                continue
            came_from[neighbor] = current
            g_score[neighbor] = tentative_g
            tie += 1
            f_score = tentative_g + manhattan(neighbor, goal)
            heapq.heappush(open_heap, (f_score, tie, neighbor))

    return [start]
