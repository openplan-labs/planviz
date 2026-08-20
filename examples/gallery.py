#!/usr/bin/env python3
"""Render one example of every planviz figure, in light and dark.

The output is what the README and the docs gallery show, and it doubles as an
end-to-end check that every public function draws on synthetic data:

.. code-block:: sh

    python examples/gallery.py                       # -> docs/assets/gallery
    python examples/gallery.py --out /tmp/gallery    # somewhere else
    python examples/gallery.py --no-animations       # skip the GIFs

Each figure is written twice — ``<name>.png`` and ``<name>-dark.png`` — so
MkDocs Material can swap them with the ``#only-light`` / ``#only-dark``
fragments, and a README ``<picture>`` element can do the same.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Callable
from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt  # noqa: E402

import planviz  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
import data  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
DEFAULT_OUT = REPO / "docs" / "assets" / "gallery"


def _figures(dark: bool) -> dict[str, Callable[[], object]]:
    """Return ``{name: builder}`` for every static figure."""
    grid = data.warehouse()
    lattice = data.maze()
    search = data.astar(lattice, (1, 1), (19, 19))
    flood = data.astar(grid, (1, 1), (16, 26), weight=0.35)
    agents = data.routes(grid, count=5)
    crowd = data.routes(grid, count=12, seed=23)
    sweep = data.scaling()

    return {
        "grid": lambda: planviz.draw_grid(
            grid, dark=dark, title="Warehouse, 18 × 28, 4-connected"
        ),
        "search": lambda: planviz.draw_search(
            expanded=search["expanded"],
            frontier=search["frontiers"][-1],
            path=search["path"],
            grid=lattice,
            start=search["start"],
            goal=search["goal"],
            dark=dark,
            title="A* with a Manhattan heuristic",
        ),
        "paths": lambda: planviz.draw_paths(
            agents, grid, dark=dark, title="Five agents, prioritized planning"
        ),
        "congestion": lambda: planviz.draw_heatmap(
            data.congestion(grid, crowd),
            grid,
            dark=dark,
            label="agent-timesteps",
            title="Congestion — where twelve plans queue up",
        ),
        "paths-crowded": lambda: planviz.draw_paths(
            crowd, grid, dark=dark, title="Twelve agents — density, not hue"
        ),
        "paths-highlight": lambda: planviz.draw_paths(
            crowd,
            grid,
            highlight="C",
            dark=dark,
            title="One agent is the subject; the rest are context",
        ),
        "search-progress": lambda: planviz.search_panels(
            {
                "f, g and h per expansion": {
                    key: search["series"][key] for key in ("f", "g", "h")
                },
                "open list size": {"|open|": search["series"]["open"]},
            },
            dark=dark,
            fill=["open list size"],
            ylabels={"f, g and h per expansion": "cost"},
            suptitle=(
                f"A* on a 21 x 21 maze — {len(search['expanded'])} expansions"
            ),
        ),
        # A weighted A* over open floor, not the maze: a corridor search puts
        # one node on every depth ring and the polar view has nothing to say.
        "wavefront": lambda: planviz.radial_wavefront(
            flood["tree"],
            frontier=flood["frontier_ids"],
            goal=flood["goal_id"],
            dark=dark,
            title="Weighted A* — radius is depth, colour is the heuristic",
        ),
        "plan-timeline": lambda: planviz.plan_timeline(
            data.plan(), dark=dark, xlabel="step", title="Blocksworld plan, 8 steps"
        ),
        "agent-timeline": lambda: planviz.plan_timeline(
            planviz.timeline_from_paths(agents),
            dark=dark,
            xlabel="timestep",
            title="Who moves, who waits",
        ),
        "scaling": lambda: planviz.scaling_curve(
            sweep["series"],
            timeouts=sweep["timeouts"],
            cap=sweep["cap"],
            highlight="cuda",
            log_x=True,
            dark=dark,
            title="Median of 5 seeds, 64 × 64 grid, 5% obstacles",
        ),
        "success": lambda: planviz.success_heatmap(
            dark=dark, title="Coverage over 5 seeds (— = not measured)",
            **data.coverage(),
        ),
        "phases": lambda: planviz.phase_breakdown(
            data.phases(),
            accent="kernel",
            neutral=["host"],
            dark=dark,
            title="Where device wall time goes",
        ),
        "throughput": lambda: planviz.throughput_curve(
            data.throughput(),
            highlight="cuda",
            dark=dark,
            xlabel="distance maps per batch",
            ylabel="maps / s",
            title="Batched BFS throughput",
        ),
        "crossover": lambda: planviz.crossover_plot(
            data.crossover(),
            highlight="prioritized",
            dark=dark,
            ylabel="reference time ÷ candidate time",
            title="Above parity the candidate wins",
        ),
    }


def _animations(dark: bool) -> dict[str, Callable[[], object]]:
    grid = data.warehouse()
    lattice = data.maze()
    search = data.astar(lattice, (1, 1), (19, 19))
    agents = data.routes(grid, count=5)
    return {
        "search-animation": lambda: planviz.animate_search(
            search["expanded"],
            frontiers=search["frontiers"],
            path=search["path"],
            grid=lattice,
            start=search["start"],
            goal=search["goal"],
            frames=70,
            dark=dark,
            title="The frontier moves, the closed list accumulates",
        ),
        "paths-animation": lambda: planviz.animate_paths(
            agents, grid, dark=dark, title="Five agents executing the plan"
        ),
    }


def render(out: Path, animations: bool = True, progress=print) -> list[Path]:
    """Render the gallery into ``out``; return the paths written."""
    written: list[Path] = []
    for dark in (False, True):
        suffix = "-dark" if dark else ""
        for name, build in _figures(dark).items():
            drawn = build()
            path = planviz.save(drawn, out / f"{name}{suffix}.png")
            written.append(path)
            progress(f"{path}  ({path.stat().st_size // 1024} KB)")
            plt.close(getattr(drawn, "figure", drawn))
        if not animations:
            continue
        for name, build in _animations(dark).items():
            path = planviz.save_animation(build(), out / f"{name}{suffix}.gif")
            written.append(path)
            progress(f"{path}  ({path.stat().st_size // 1024} KB)")
    return written


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        prog="python examples/gallery.py", description=__doc__.splitlines()[0]
    )
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument(
        "--no-animations",
        dest="animations",
        action="store_false",
        help="skip the GIFs, which are the slow part",
    )
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)
    written = render(args.out, animations=args.animations)
    print(f"\n{len(written)} files in {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
