"""planviz — the Frontier-styled figure library for OpenPlan Labs.

One installable package for the pictures every planning repository draws: grid
maps, search figures, plan timelines, MAPF animations, and benchmark charts.
The brand's palette, marks and chart rules ship *inside* the wheel, so a figure
drawn here is on-brand without anyone locating the branding repository.

Planners not included. This library draws results; it does not produce them.

Four things hold across the whole API:

* **Nothing happens on import.** Importing ``planviz`` changes no matplotlib
  state. Style is applied by :func:`use_style`, or per-figure inside a
  :func:`style_context` that restores rcParams on exit.
* **Every figure function takes ``dark: bool = False``** and an optional
  ``ax=``, so light and dark variants come from the same call and figures
  compose into panels.
* **Nothing is saved or shown for you.** Functions return the
  :class:`~matplotlib.axes.Axes` they drew on, or the
  :class:`~matplotlib.figure.Figure` for multi-panel figures.
  :func:`save` is the explicit write.
* **No planner types are imported.** A grid is a 2-D array-like, a path is a
  sequence of ``(row, col)`` pairs, a benchmark series is a mapping.

    >>> import matplotlib; matplotlib.use("Agg")
    >>> import planviz
    >>> ax = planviz.draw_search(
    ...     expanded=[(1, 1), (1, 2), (2, 1)],
    ...     frontier=[(0, 1), (2, 2)],
    ...     path=[(1, 1), (1, 2), (2, 2)],
    ...     grid=[[0, 0, 0], [0, 0, 0], [1, 0, 0]],
    ...     dark=True,
    ... )
    >>> _ = planviz.save(ax, "/tmp/search.png")
"""

from __future__ import annotations

from . import tokens
from ._common import save
from .animate import animate_paths, animate_search, save_animation, to_jshtml
from .benchmarks import (
    crossover_plot,
    phase_breakdown,
    scaling_curve,
    success_heatmap,
    throughput_curve,
)
from .grids import MARKS, draw_grid, draw_paths, draw_search
from .search import (
    Step,
    plan_timeline,
    radial_wavefront,
    search_panels,
    search_progress,
    timeline_from_paths,
)
from .style import STYLE_PATH, style_context, use_style
from .tokens import AGENT_RAMP, DARK, LIGHT, Tokens

__version__ = "0.1.0"

__all__ = [
    "__version__",
    # style and tokens
    "use_style",
    "style_context",
    "STYLE_PATH",
    "tokens",
    "Tokens",
    "LIGHT",
    "DARK",
    "AGENT_RAMP",
    "MARKS",
    # grids and agents
    "draw_grid",
    "draw_paths",
    "draw_search",
    "animate_paths",
    "animate_search",
    "save_animation",
    "to_jshtml",
    # search progress
    "search_progress",
    "search_panels",
    "radial_wavefront",
    "plan_timeline",
    "timeline_from_paths",
    "Step",
    # benchmarks
    "scaling_curve",
    "success_heatmap",
    "phase_breakdown",
    "throughput_curve",
    "crossover_plot",
    # output
    "save",
]
