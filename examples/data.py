"""Synthetic instances for the gallery — no solver, no benchmark run required.

Everything here is seeded, so the committed gallery images are reproducible:
re-running ``examples/gallery.py`` on any machine produces the same figures.
The A\\* below is a plain textbook implementation whose only unusual feature is
that it records what a visualisation needs — expansion order, open-list
snapshots, and the parent/depth/heuristic of every expanded node.
"""

from __future__ import annotations

import heapq
import random
from collections.abc import Sequence

import numpy as np

Cell = tuple[int, int]


def warehouse(height: int = 18, width: int = 28, seed: int = 7) -> np.ndarray:
    """Return a warehouse occupancy grid: shelf blocks with aisles between."""
    rng = random.Random(seed)
    grid = np.zeros((height, width), dtype=bool)
    for row in range(2, height - 2, 4):
        for col in range(2, width - 2, 5):
            if rng.random() < 0.85:
                grid[row : row + 2, col : col + 3] = True
    return grid


def maze(height: int = 21, width: int = 21, seed: int = 3) -> np.ndarray:
    """Return a perfect maze on an odd-sized grid, carved by randomized DFS."""
    rng = random.Random(seed)
    grid = np.ones((height, width), dtype=bool)
    stack = [(1, 1)]
    grid[1, 1] = False
    while stack:
        row, col = stack[-1]
        steps = [(-2, 0), (2, 0), (0, -2), (0, 2)]
        rng.shuffle(steps)
        for drow, dcol in steps:
            nrow, ncol = row + drow, col + dcol
            if 0 < nrow < height - 1 and 0 < ncol < width - 1 and grid[nrow, ncol]:
                grid[row + drow // 2, col + dcol // 2] = False
                grid[nrow, ncol] = False
                stack.append((nrow, ncol))
                break
        else:
            stack.pop()
    return grid


def _neighbours(grid: np.ndarray, cell: Cell):
    height, width = grid.shape
    row, col = cell
    for drow, dcol in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        nrow, ncol = row + drow, col + dcol
        if 0 <= nrow < height and 0 <= ncol < width and not grid[nrow, ncol]:
            yield (nrow, ncol)


def astar(grid: np.ndarray, start: Cell, goal: Cell, weight: float = 1.0) -> dict:
    """Run A\\* and return everything a figure needs about the search.

    Returns a dict with ``path``, ``expanded`` (in expansion order),
    ``frontiers`` (the open list after each expansion), ``tree`` (records of
    ``(node, parent, depth, h)``), and the ``f``/``g``/``h``/``open`` series.
    """

    def h(cell: Cell) -> int:
        return abs(cell[0] - goal[0]) + abs(cell[1] - goal[1])

    open_heap: list[tuple[float, int, Cell]] = [(weight * h(start), 0, start)]
    came: dict[Cell, Cell] = {}
    cost: dict[Cell, int] = {start: 0}
    closed: set = set()
    ids: dict[Cell, int] = {start: 0}

    expanded: list[Cell] = []
    frontiers: list[list[Cell]] = []
    tree: list[tuple[int, int, int, float]] = []
    series: dict[str, list[float]] = {"f": [], "g": [], "h": [], "open": []}

    while open_heap:
        f, g, cell = heapq.heappop(open_heap)
        if cell in closed:
            continue
        closed.add(cell)
        expanded.append(cell)
        parent = came.get(cell)
        ids.setdefault(cell, len(ids))
        tree.append(
            (ids[cell], ids[parent] if parent is not None else -1, g, float(h(cell)))
        )
        series["f"].append(f)
        series["g"].append(g)
        series["h"].append(h(cell))
        series["open"].append(len({entry[2] for entry in open_heap} - closed))
        frontiers.append(sorted({entry[2] for entry in open_heap} - closed))
        if cell == goal:
            break
        for nxt in _neighbours(grid, cell):
            step = g + 1
            if step < cost.get(nxt, 1 << 30):
                cost[nxt] = step
                came[nxt] = cell
                ids.setdefault(nxt, len(ids))
                heapq.heappush(open_heap, (step + weight * h(nxt), step, nxt))

    path: list[Cell] = []
    if goal in closed:
        cell = goal
        while cell != start:
            path.append(cell)
            cell = came[cell]
        path.append(start)
        path.reverse()
    open_cells = {entry[2] for entry in open_heap} - closed
    return {
        "path": path,
        "expanded": expanded,
        "frontiers": frontiers,
        "tree": tree,
        "series": series,
        "start": start,
        "goal": goal,
        # Node ids, for the radial view, which works in tree space not grid space.
        "frontier_ids": [ids[cell] for cell in open_cells if cell in ids],
        "goal_id": ids.get(goal),
    }


def free_cells(grid: np.ndarray) -> list[Cell]:
    rows, cols = np.nonzero(~grid)
    return list(zip(rows.tolist(), cols.tolist(), strict=True))


def routes(
    grid: np.ndarray, count: int = 5, seed: int = 11, waits: int = 2
) -> dict[str, list[Cell]]:
    """Return ``count`` named agent routes across ``grid``.

    They are planned one at a time and ignore each other, then ``waits``
    stand-still steps are spliced into each — which is what a prioritized
    planner produces and what makes a timeline figure worth drawing. The
    gallery is about how a figure looks, not about whether the plan is valid.
    """
    rng = random.Random(seed)
    cells = free_cells(grid)
    _, width = grid.shape
    left = [cell for cell in cells if cell[1] < width // 3]
    right = [cell for cell in cells if cell[1] > 2 * width // 3]
    out: dict[str, list[Cell]] = {}
    names = [chr(ord("A") + i) for i in range(count)]
    for index, name in enumerate(names):
        source, target = (left, right) if index % 2 == 0 else (right, left)
        for _ in range(20):
            start, goal = rng.choice(source), rng.choice(target)
            result = astar(grid, start, goal)
            if result["path"]:
                path = list(result["path"])
                for _ in range(rng.randint(0, waits)):
                    at = rng.randrange(1, max(2, len(path) - 1))
                    path[at:at] = [path[at]] * rng.randint(1, 3)
                out[name] = path
                break
    return out


def congestion(grid: np.ndarray, paths: dict[str, list[Cell]]) -> np.ndarray:
    """Return agent-timesteps per cell — where the plan queues up."""
    counts = np.zeros(grid.shape, dtype=float)
    for path in paths.values():
        for row, col in path:
            counts[int(row), int(col)] += 1
    return counts


def scaling(seed: int = 5) -> dict:
    """Return a synthetic three-backend sweep: ``{name: {agents: [seeds]}}``."""
    rng = random.Random(seed)
    sizes = [4, 8, 16, 32, 64, 128]
    laws = {
        "reference": (2.6e-3, 1.85),
        "optimized": (7.0e-4, 1.70),
        "cuda": (9.0e-3, 1.05),
    }
    out = {}
    for name, (scale, exponent) in laws.items():
        out[name] = {
            n: [scale * n**exponent * rng.uniform(0.82, 1.3) for _ in range(5)]
            for n in sizes
        }
    # The reference backend stops finishing inside the limit past 32 agents.
    out["reference"] = {n: v for n, v in out["reference"].items() if n <= 32}
    return {"series": out, "timeouts": {"reference": [64, 128]}, "cap": 30.0}


def coverage(seed: int = 13) -> dict:
    """Return a synthetic success matrix over (density x agents)."""
    rng = random.Random(seed)
    agents = [4, 8, 16, 32, 64, 128]
    densities = [0.05, 0.15, 0.25]
    matrix = []
    for density in densities:
        row = []
        for n in agents:
            pressure = density * 4 + n / 160
            rate = max(0.0, min(1.0, 1.15 - pressure + rng.uniform(-0.08, 0.08)))
            row.append(None if (density == 0.25 and n == 128) else round(rate, 2))
        matrix.append(row)
    return {
        "matrix": matrix,
        "x_labels": [str(n) for n in agents],
        "y_labels": [f"{d:.0%}" for d in densities],
    }


def phases() -> dict:
    """Return a synthetic device-time split: ``{batch: {phase: seconds}}``."""
    out = {}
    for batch in (32, 64, 128, 256, 512):
        kernel = 0.0009 * batch
        out[str(batch)] = {
            "kernel": kernel,
            "h2d": 0.006 + 0.00004 * batch,
            "d2h": 0.004 + 0.00003 * batch,
            "host": 0.012,
        }
    return out


def throughput(seed: int = 17) -> dict:
    """Return a synthetic saturation sweep: throughput against batch size."""
    rng = random.Random(seed)
    sizes = [16, 32, 64, 128, 256, 512, 1024]
    out = {
        "reference": {
            n: [4.2e4 * rng.uniform(0.95, 1.05) for _ in range(3)] for n in sizes
        },
        "cuda": {
            n: [
                2.6e6 * (1 - np.exp(-n / 260.0)) * rng.uniform(0.95, 1.05)
                for _ in range(3)
            ]
            for n in sizes
        },
    }
    return out


def crossover(seed: int = 19) -> dict:
    """Return synthetic speedup ratios per algorithm family."""
    rng = random.Random(seed)
    sizes = [4, 8, 16, 32, 64, 128]
    families = {"prioritized": 0.62, "PIBT": 0.30, "batched BFS": 1.4}
    return {
        name: {
            n: [base * (n / 8) ** 0.78 * rng.uniform(0.9, 1.12) for _ in range(3)]
            for n in sizes
        }
        for name, base in families.items()
    }


def plan() -> Sequence[str]:
    """Return a short synthetic PDDL-style plan."""
    return [
        "unstack(d, c)",
        "put-down(d)",
        "unstack(c, b)",
        "stack(c, d)",
        "pick-up(b)",
        "stack(b, c)",
        "pick-up(a)",
        "stack(a, b)",
    ]
